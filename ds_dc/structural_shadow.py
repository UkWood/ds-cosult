"""Replay the unchanged historical Q01 and inspect a derived V2 diagnostic view."""
import argparse
from dataclasses import replace
from functools import lru_cache
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from .candidate_fixture import load_candidate
from .corpus import BKD
from .evidence_lab import audit_v1, nfc_text
from .finance import Ledger
from .native import NativeD1, wire_identity
from .prep import freeze, freeze_digest, load
from .recovery import MANIFEST, Q01_WIRE
from .runtime import Claim, Journal, Locator, Pilot
from .structural_pdf import extract
from .technical_registry import Entity, Source, SourceRegistry, VERSION
from .technical_verifier import inspect_claim, table_rows, word

Q01_SHA = "ae646fb4ae9d3b83c22edc9717b4d8ddb0ef228ac54b9f5a1aec222bcb24cb26"
V1_ROLES = {
    "симптом неисправности": ("symptom", "symptom", "observed"),
    "возможная причина": ("possible_cause", "cause", "possible"),
    "по таблице неисправностей": ("conditional_action", "action", "conditional"),
}


def bound_manual(source, entity, cover):
    """Use an exact printed model and edition. Dossier membership grants no applicability."""
    blocks = {nfc_text(item["text"]) for item in cover["blocks"]}
    if not source.revision or ", " not in source.revision:
        return source
    doc, edition = source.revision.rsplit(", ", 1)
    if ({entity.label, "Контроллер " + entity.label} & blocks
            and {doc, "Редакция " + edition, "Руководство по эксплуатации"} <= blocks):
        return replace(source, applicability="explicit_model_and_edition_on_cover")
    return source


def project_v1(claim, registry, extract_page):
    if (not isinstance(claim, dict) or set(claim) != Claim.__required_keys__
            or not all(isinstance(claim[k], str) for k in Claim.__required_keys__ - {"locators"})
            or not isinstance(claim["locators"], list) or len(claim["locators"]) != 1
            or not isinstance(claim["locators"][0], dict)
            or set(claim["locators"][0]) != Locator.__required_keys__):
        return None, "unhandled_v1_shape"
    loc = claim["locators"][0]
    binding = registry.v1_source(loc, claim["scope"])
    if not binding or type(loc["page"]) is not int:
        return None, "v1_identity_unresolved"
    source_id, entity_id = binding
    source = registry.sources[source_id]
    if not source.applicability:
        return None, "applicability_unproved"
    rule = V1_ROLES.get(word(claim["qualifier"]))
    if rule is None or claim["unit"] or not isinstance(loc["quote"], str):
        return None, "unhandled_v1_technical_fields"
    kind, target, qualifier = rule
    literal = claim["literal"]
    if nfc_text(literal) != nfc_text(loc["quote"]):
        return None, "v1_literal_quote_conflict"
    condition = claim["condition"]
    if kind == "symptom":
        if (word(claim["value"] + " " + claim["component"]) != word(literal)
                or word(condition) != word(claim["value"])):
            return None, "v1_symptom_fields_unproved"
        condition = ""
    elif word(claim["value"]) != word(literal):
        return None, "v1_value_literal_conflict"
    elif kind == "possible_cause" and word(claim["component"]) != "причина неисправности":
        return None, "v1_component_unproved"
    elif kind == "conditional_action":
        if word(claim["component"]) != "действие по устранению неисправности":
            return None, "v1_component_unproved"
        before = word(condition)
        condition = before.removeprefix("если ").removeprefix("возможная причина — ")
        if condition == before:
            return None, "v1_action_condition_unproved"
    evidence = [{"role": target, "source": source_id, "page": loc["page"], "quote": loc["quote"]}]
    prerequisite = {"possible_cause": "symptom", "conditional_action": "cause"}.get(kind)
    try:
        page = extract_page(source, loc["page"])
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, "evidence_unavailable"
    matches = {}
    for table, row, cells in table_rows(page):
        if not cells.get(target) or nfc_text(cells[target]["text"]) != nfc_text(loc["quote"]):
            continue
        top = page["tables"][table]["bbox"][1]
        preceding = [block for block in page["blocks"] if block["bottom"] <= top]
        if loc["table"] and (not preceding or word(max(preceding, key=lambda b: b["bottom"])["text"])
                             != word(loc["table"])):
            continue
        if loc["section"] and not any(word(block["text"]) == word(loc["section"]) for block in preceding):
            continue
        if prerequisite and (not cells.get(prerequisite) or word(cells[prerequisite]["text"]) != word(condition)):
            continue
        cell = cells[target]
        key = (table, row if prerequisite else cell["row"], cell["column"])
        matches[key] = cells
    if len(matches) != 1:
        return None, "v1_condition_or_coordinate_unproved"
    (table, _, _), cells = next(iter(matches.items()))
    evidence[0]["hint"] = {"table": table, "row": cells[target]["row"], "column": cells[target]["column"]}
    if prerequisite:
        cell = cells[prerequisite]
        evidence.append({"role": prerequisite, "source": source_id, "page": loc["page"],
                         "quote": cell["text"],
                         "hint": {"table": table, "row": cell["row"], "column": cell["column"]}})
    return dict(id=claim["claim_id"], entity=entity_id, kind=kind, subject=literal,
                value="", unit="", comparator="", qualifier=qualifier, condition=condition,
                parts=[], evidence=evidence), None


def replay(path, site, cache):
    candidate = load_candidate(path, Q01_SHA)
    questions = Path(__file__).resolve().parents[1] / "docs/runbooks/ds-dc-02/live-questions.json"
    question = next(q["question"] for q in json.loads(questions.read_text())["questions"] if q["id"] == "Q01")
    entries, dossiers, _ = load(site, cache)
    manifest = freeze(entries, dossiers)
    if freeze_digest(manifest) != MANIFEST:
        raise ValueError("fixture_corpus_mismatch")

    @lru_cache(maxsize=32)
    def extract_page(source, page):
        if not 1 <= page <= source.pages:
            raise ValueError("page_outside_registry")
        return extract(cache, source.sha256, page)

    with TemporaryDirectory() as root:
        root = Path(root)
        provider = NativeD1(cache, Ledger(root / "ledger"), manifest=manifest)
        result = {}

        def inspect(_request, text, pages, docs, history, _now, _cap):
            if wire_identity(text, pages, docs, history) != Q01_WIRE:
                raise ValueError("fixture_wire_mismatch")
            entity = Entity(BKD, entries[BKD]["title"], "RF.2")
            sources = []
            cited = {(loc.get("doc_id"), loc.get("sha256"), loc.get("revision"))
                     for claim in candidate["claims"] for loc in claim["locators"]}
            for doc in docs:
                source = Source(doc["scope"], entity.generation, "pdf", doc["sha256"], doc["id"],
                                doc["revision"], doc["pages"], doc["url"])
                if (source.doc_id, source.sha256, source.revision) in cited:
                    try:
                        source = bound_manual(source, entity, extract_page(source, 1))
                    except (OSError, ValueError, subprocess.SubprocessError):
                        pass
                sources.append(source)
            sources.extend(Source(entity.canonical_id, entity.generation, "site", page["sha256"],
                                  page["id"], None, 0, page["canonical"], commit=page["commit"], blob=page["blob"])
                           for page in pages)
            registry = SourceRegistry("shadow-Q01", MANIFEST, [entity], sources, {"P1": question})
            result.update(fixture_sha256=Q01_SHA, historical_wire=Q01_WIRE,
                          version=VERSION, shadow_wire_identity=registry.wire_identity,
                          v1=audit_v1(candidate, text, docs, pages, cache),
                          gt={"source": "Final Audit R1 F08", "supported_claims": 5},
                          v2_claims=[], coverage="semantic_pending",
                          unpublished_text=["sequence_unproved", "exhaustiveness_unproved"])
            for original in candidate["claims"]:
                derived, reason = project_v1(original, registry, extract_page)
                if derived:
                    result["v2_claims"].append(inspect_claim(derived, registry, extract_page))
                else:
                    result["v2_claims"].append(dict(id=original["claim_id"], technical_status="semantic_pending",
                        schema_valid=None, source_identity_verified=None, applicability_verified=None,
                        evidence_verified=None, relation_verified=None, reason_codes=[reason],
                        covered_parts=[], locators=[]))
            result["confirmed_claim_ids"] = [row["id"] for row in result["v2_claims"]
                                             if row["technical_status"] == "supported"]
            result["extractions"] = [
                extract_page(source, page)["identity"]
                for source in sources if source.applicability
                for page in sorted({loc["page"] for row in result["v2_claims"] for loc in row.get("locators", [])
                                    if loc["sha256"] == source.sha256})
            ]
            return "offline_shadow", None, {}

        provider.dispatch = inspect
        pilot = Pilot(entries, dossiers, cache, Journal(root / "journal"), provider, owner_dc02=True)
        peer = "127.0.0.1"
        status = pilot.ask(peer, pilot.open(peer), "offline-shadow", question)
        if status["status"] != "offline_shadow" or provider.chat_posts:
            raise ValueError("shadow_not_executed")
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixture", "site", "cache"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = replay(args.fixture, args.site, args.cache)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        parser.exit(1, "Shadow replay refused input. Verify the fixture and frozen corpus.\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
