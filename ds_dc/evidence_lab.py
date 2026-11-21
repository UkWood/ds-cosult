"""Offline V1 replay and V2 lab with independently reviewed synthetic facts."""
import argparse
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unicodedata

from .candidate_fixture import load_candidate
from .corpus import MAX_SIZE, digest
from .pdf_policy import pdf_tool
from .runtime import CandidateAnswer, Claim, Locator, source_locator, verify


def nfc_text(text):
    return " ".join(unicodedata.normalize("NFC", text).split())


@dataclass(frozen=True)
class Source:
    sha256: str
    revision: str
    pages: int
    applicability: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class Fragment:
    source: str
    page: int
    anchor: str
    text: str


@dataclass(frozen=True)
class Fact:
    entity: str
    generation: str
    kind: str
    subject: str
    value: str
    unit: str
    qualifier: str
    condition: str
    relation: str
    part: str
    fragments: tuple[str, ...]


def assess_v2(candidate, *, registry, labels, fragments, facts, parts):
    """Match reviewed propositions only. Mechanical matches alone give no semantic credit."""
    if (not isinstance(candidate, dict)
            or set(candidate) != {"version", "claims", "answer_claim_ids", "unresolved"}
            or candidate["version"] != "2-lab"
            or not all(isinstance(candidate[k], list) and len(candidate[k]) <= 32
                       for k in ("claims", "answer_claim_ids", "unresolved"))
            or not all(isinstance(item, str) for key in ("answer_claim_ids", "unresolved")
                       for item in candidate[key])):
        return {"verdict": "invalid_contract", "claims": {}, "uncovered": sorted(parts)}
    results = {}
    coverage = {}
    fields = set(Fact.__dataclass_fields__) - {"fragments"}
    for item in candidate["claims"]:
        if (not isinstance(item, dict) or set(item) != fields | {"id", "evidence"}
                or not all(isinstance(item[k], str) for k in fields | {"id"})
                or not item["id"] or item["id"] in results
                or not isinstance(item["evidence"], list) or not 1 <= len(item["evidence"]) <= 4):
            return {"verdict": "invalid_contract", "claims": results, "uncovered": sorted(parts)}
        identity = labels.get(nfc_text(item["entity"]), ())
        facet = {k: item[k] for k in fields}
        failure = None
        evidence = []
        if len(identity) != 1:
            failure = "scope_unresolved"
        else:
            facet["entity"] = identity[0]
        for loc in item["evidence"]:
            if (not isinstance(loc, dict) or set(loc) != {"source", "page", "anchor", "quote"}
                    or not all(isinstance(loc[k], str) for k in ("source", "anchor", "quote"))
                    or type(loc["page"]) is not int):
                failure = failure or "invalid_locator"
                continue
            source = registry.get(loc["source"])
            fragment = fragments.get(loc["anchor"])
            if (source is None or fragment is None or not 1 <= loc["page"] <= source.pages
                    or (fragment.source, fragment.page) != (loc["source"], loc["page"])):
                failure = failure or "invalid_locator"
            elif len(identity) == 1 and (identity[0], item["generation"]) not in source.applicability:
                failure = failure or "inapplicable_source"
            elif nfc_text(fragment.text) != nfc_text(loc["quote"]):
                failure = failure or "quote_mismatch"
            evidence.append(loc["anchor"])
        if not failure:
            proof = Fact(**facet, fragments=tuple(sorted(evidence)))
            if proof in facts:
                coverage[item["id"]] = item["part"]
            else:
                failure = "semantic_pending"
        results[item["id"]] = failure or "supported_fixture"
    answer_ids = candidate["answer_claim_ids"]
    resolved_parts = {coverage[key] for key in answer_ids if key in coverage}
    unresolved = set(candidate["unresolved"])
    uncovered = parts - resolved_parts - unresolved
    if any(results.get(key) != "supported_fixture" for key in answer_ids):
        verdict = "answer_not_supported"
    elif uncovered or not unresolved <= parts or resolved_parts & unresolved:
        verdict = "question_coverage_gap"
    elif any(value != "supported_fixture" for value in results.values()):
        verdict = "semantic_pending"
    elif unresolved:
        verdict = "partial_fixture"
    else:
        verdict = "supported_fixture"
    return {"verdict": verdict, "claims": results, "uncovered": sorted(uncovered)}


def audit_v1(candidate, question, docs, site, cache):
    legacy, legacy_diagnostics = verify(candidate, question, docs, cache, pages=site, dc02=True)
    scopes = {d["scope"] for d in docs} | {scope for page in site for scope in page["scope"]}
    extracted = {}
    rows = []
    for index, claim in enumerate(candidate.get("claims", [])):
        flags = []
        if set(claim) != Claim.__required_keys__:
            flags.append("claim_fields_mismatch")
        if claim.get("scope") not in scopes:
            flags.append("scope_not_canonical")
        if not claim.get("locators"):
            flags.append("no_locator")
        for loc in claim.get("locators", []):
            if set(loc) == {"doc_id", "sha256", "field_path", "quote"}:
                page = next((p for p in site if p["id"] == loc["doc_id"] and p["sha256"] == loc["sha256"]), None)
                if page is None:
                    flags.append("site_identity_mismatch")
                else:
                    if claim.get("scope") not in page["scope"]:
                        flags.append("site_scope_mismatch")
                    result = source_locator(loc, {key: "" for key in ("value", "unit", "qualifier", "condition")}
                                            | {"scope": page["scope"][0]}, site)
                    flags.append("site_" + result)
                    if "quote" in loc:
                        for facet in ("literal", "value", "unit", "condition", "qualifier"):
                            value = claim.get(facet)
                            if value and nfc_text(value) not in nfc_text(loc["quote"]):
                                flags.append(facet + "_not_literal_in_quote")
                continue
            if set(loc) != Locator.__required_keys__ or type(loc.get("page")) is not int:
                flags.append("locator_fields_mismatch")
                continue
            matching = [doc for doc in docs if doc["id"] == loc["doc_id"] and doc["sha256"] == loc["sha256"]]
            if not matching:
                flags.append("pdf_identity_mismatch")
                continue
            if all(doc["scope"] != claim.get("scope") for doc in matching):
                flags.append("pdf_scope_mismatch")
            if all(doc["revision"] != loc["revision"] for doc in matching):
                flags.append("revision_mismatch")
            doc = matching[0]
            page = loc["page"]
            if not 1 <= page <= doc["pages"]:
                flags.append("page_out_of_range")
                continue
            key = (doc["sha256"], page)
            if key not in extracted:
                try:
                    path = cache / (doc["sha256"] + ".pdf")
                    if path.stat().st_size > MAX_SIZE or digest(path.read_bytes()) != doc["sha256"]:
                        raise ValueError("pdf_integrity")
                    plain = pdf_tool("pdftotext", "-f", str(page), "-l", str(page), path, "-")
                    layout = pdf_tool("pdftotext", "-layout", "-f", str(page), "-l", str(page), path, "-")
                    extracted[key] = (plain, layout)
                except (OSError, ValueError, subprocess.SubprocessError):
                    extracted[key] = None
            extraction = extracted[key]
            if extraction is None:
                flags.append("page_text_unavailable")
                continue
            text, layout = extraction
            quote = nfc_text(loc["quote"])
            legacy_text = " ".join(text.split())
            legacy_quote = " ".join(loc["quote"].split())
            if not quote:
                flags.append("empty_quote")
            elif legacy_quote in legacy_text:
                flags.append("quote_present")
            elif quote in nfc_text(text):
                flags.append("quote_unicode_only")
            elif quote.casefold() in nfc_text(text).casefold():
                flags.append("quote_ignore_case_only")
            elif quote in nfc_text(layout):
                flags.append("quote_layout_only")
            else:
                flags.append("quote_missing")
            for facet in ("literal", "value", "unit", "condition", "qualifier"):
                value = claim.get(facet)
                if value and nfc_text(value) not in quote:
                    flags.append(facet + "_not_literal_in_quote")
        rows.append({"claim_index": index, "checks": flags,
                     "semantic_review": ["value_and_applicability", "qualifier_and_condition",
                                         "table_row_column_relation", "question_coverage"]})
    answer = nfc_text(candidate.get("answer_candidate", ""))
    return {"legacy": legacy, "legacy_diagnostics": legacy_diagnostics,
            "candidate_fields_exact": set(candidate) == CandidateAnswer.__required_keys__,
            "claims": rows, "unresolved_spans_lexically_present": all(
                bool(part) and part in question for part in candidate.get("unresolved", [])),
            "claim_literals_absent_from_answer": [
                i for i, claim in enumerate(candidate.get("claims", []))
                if claim.get("literal") and nfc_text(claim["literal"]) not in answer],
            "open_semantic_review": ["unclaimed_statements_in_answer", "coverage_of_all_question_parts"]}


def replay(path, sha256, site, cache):
    from .finance import Ledger
    from .native import NativeD1, wire_identity
    from .prep import freeze, freeze_digest, load
    from .recovery import MANIFEST, Q01_WIRE
    from .runtime import Journal, Pilot

    candidate = load_candidate(path, sha256)
    questions_file = Path(__file__).resolve().parents[1] / "docs/runbooks/ds-dc-02/live-questions.json"
    question = next(q["question"] for q in json.loads(questions_file.read_text())["questions"] if q["id"] == "Q01")
    entries, registry, _ = load(site, cache)
    manifest = freeze(entries, registry)
    if freeze_digest(manifest) != MANIFEST:
        raise ValueError("fixture_corpus_mismatch")
    with TemporaryDirectory() as root:
        root = Path(root)
        provider = NativeD1(cache, Ledger(root / "ledger"), manifest=manifest)
        report = {}

        def inspect(_request, text, pages, docs, history, _now, _cap):
            if wire_identity(text, pages, docs, history) != Q01_WIRE:
                raise ValueError("fixture_wire_mismatch")
            report.update(audit_v1(candidate, text, docs, pages, cache))
            return "offline_replay", None, {}

        provider.dispatch = inspect
        pilot = Pilot(entries, registry, cache, Journal(root / "journal"), provider, owner_dc02=True)
        peer = "127.0.0.1"
        result = pilot.ask(peer, pilot.open(peer), "offline-replay", question)
        if result["status"] != "offline_replay" or provider.chat_posts != 0:
            raise ValueError("fixture_replay_not_executed")
        return {"fixture_sha256": sha256, "wire_sha256": Q01_WIRE, "manifest_sha256": MANIFEST, **report}


def demo_matrix():
    """Controlled facts for an invented device, unrelated to the Q01 live answer."""
    scopes = {"lab:device:A", "lab:device:B"}
    labels = {"Fixture A": ("lab:device:A",), "lab:device:A": ("lab:device:A",),
              "Fixture B": ("lab:device:B",)}
    # A row-label, cell, and condition may occur independently in the page.
    row = "Mass 10 kg max dry; Power 15 W"
    raw = "---\ntitle: Fixture manual\n---\n" + row
    page = {"id": "lab-sheet", "scope": sorted(scopes), "sha256": digest(raw.encode()), "raw": raw}
    fragments = {"r1-label": Fragment("S1", 1, "r1-label", "Mass"),
                 "r1-cell": Fragment("S1", 1, "r1-cell", "10 kg max dry"),
                 "r2-label": Fragment("S1", 1, "r2-label", "Power"),
                 "r2-cell": Fragment("S1", 1, "r2-cell", "15 W")}
    proof = Fact("lab:device:A", "G1", "quantity_limit", "mass", "10", "kg", "max",
                 "dry", "same_row", "P1", ("r1-cell", "r1-label"))
    base_claim = {k: getattr(proof, k) for k in Fact.__dataclass_fields__ if k != "fragments"}
    base_claim.update(id="C1", evidence=[
        {"source": "S1", "page": 1, "anchor": key, "quote": fragments[key].text}
        for key in proof.fragments
    ])
    cases = [
        ("human_scope", {"entity": "Fixture A"}, "supported_fixture"),
        ("wrong_revision", {}, "answer_not_supported"),
        ("wrong_quote", {}, "answer_not_supported"),
        ("crossed_table_rows", {}, "answer_not_supported"),
        ("wrong_generation", {"generation": "G2"}, "answer_not_supported"),
        ("wrong_value", {"value": "15"}, "answer_not_supported"),
        ("wrong_unit", {"unit": "W"}, "answer_not_supported"),
        ("dropped_limit", {"qualifier": ""}, "answer_not_supported"),
        ("dropped_condition", {"condition": ""}, "answer_not_supported"),
        ("unsupported_claim", {"subject": "pressure"}, "answer_not_supported"),
        ("extra_answer_text", {}, "invalid_contract"),
        ("mandatory_sequence", {"relation": "must_precede"}, "answer_not_supported"),
    ]
    matrix = []
    with TemporaryDirectory() as root:
        for name, changes, expected in cases:
            claim = deepcopy(base_claim) | changes
            response = {"version": "2-lab", "claims": [claim], "answer_claim_ids": ["C1"], "unresolved": []}
            quote = row
            locator = {"doc_id": page["id"], "sha256": page["sha256"], "field_path": "line:4", "quote": quote}
            docs = []
            if name == "wrong_revision":
                claim["evidence"][0]["source"] = "S1-R0"
                docs = [{"id": "lab-pdf", "sha256": page["sha256"], "scope": proof.entity,
                         "revision": "R1", "pages": 1}]
                locator = {"doc_id": "lab-pdf", "sha256": page["sha256"], "revision": "R0",
                           "page": 1, "section": "", "table": "T1", "quote": row}
            elif name == "wrong_quote":
                claim["evidence"][0]["quote"] = "20 kg"
                locator["quote"] = "20 kg"
            elif name == "crossed_table_rows":
                claim["evidence"][1] = {"source": "S1", "page": 1, "anchor": "r2-label", "quote": "Power"}
            elif name == "extra_answer_text":
                response["answer_candidate"] = "Pressure is 30 Pa."
            old_claim = {k: claim[k] for k in ("value", "unit", "qualifier", "condition")}
            old_claim.update(claim_id="C1", scope=claim["entity"], component=claim["subject"],
                             literal=claim["subject"], locators=[locator])
            old = dict(answer_candidate=response.get("answer_candidate", "Mass statement"),
                       claims=[old_claim], unresolved=[], status_hint="candidate")
            legacy, _ = verify(old, "What is the mass?", docs, Path(root), pages=[page], dc02=True)
            result = assess_v2(response, registry={
                                   "S1": Source(page["sha256"], "R1", 1, frozenset({(proof.entity, proof.generation)})),
                                   "S1-R0": Source(digest(b"older revision"), "R0", 1,
                                                   frozenset({(proof.entity, proof.generation)})),
                               },
                               labels=labels, fragments=fragments, facts={proof}, parts={"P1"})
            matrix.append(dict(case=name, legacy=legacy, expected=expected, actual=result["verdict"],
                               claim_status=result["claims"].get("C1")))
    return matrix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    commands.add_parser("matrix")
    actual = commands.add_parser("replay")
    for flag in ("fixture", "site", "cache"):
        actual.add_argument("--" + flag, type=Path, required=True)
    actual.add_argument("--sha256", required=True)
    args = parser.parse_args()
    try:
        report = demo_matrix() if args.mode == "matrix" else replay(args.fixture, args.sha256, args.site, args.cache)
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        parser.exit(1, "Offline lab refused input. Check the fixture pin and frozen corpus.\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
