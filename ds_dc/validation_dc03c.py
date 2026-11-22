"""Offline child checks for the independent DC-03C runner."""
import argparse
import json
import math
import os
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from ds_pilot.discovery import front

from . import context
from .corpus import BKD, SLD, encoded
from .evidence_integration import MockReply, OfflineConsultant
from .finance import Ledger
from .native import CAL_WIRES, NativeD1, wire_approval
from .prep import freeze, freeze_digest, load
from .recovery import MANIFEST
from .runtime import Journal, Pilot
from .structural_shadow import replay

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs/reports/ds-dc-02"
QUESTIONS = ROOT / "docs/runbooks/ds-dc-02/live-questions.json"
OLD_WIRES = {
    "Q01": ("7498d9920faf9cf25dfbf461c0bc64a75701089423a1c142c1b45cb85e9b9afd", 4, 80),
    "Q02": ("d6c1ac408cf46c62c1f653a222c4e5af54d07fbc9981f65c21bb622b55303513", 10, 403),
}
WSL_ESTIMATES = {"Q01": 53287, "Q02": 315382}
SIZING_FIELDS = ("system", "pages_and_metadata", "question_tokens", "wire_without_history", "history",
                 "sparse_pages", "input_mode", "unique_files", "physical_pages", "margin",
                 "verified_upper_bound", "observed_usage")
WIRE_FIELDS = ("wire_sha256_without_handles", "scope_wire_sha256_without_handles", "max_wire_bytes")
VERDICTS = {"supported", "semantic_pending", "contradicted", "invalid"}
Q01_FLAGS = ("schema_valid", "source_identity_verified", "applicability_verified",
             "evidence_verified", "relation_verified")
Q01_REASONS = {
    "invalid_claim_schema", "foreign_entity_or_source_or_page", "cross_source_or_non_pdf_relation_unproved",
    "evidence_unavailable", "quote_or_structure_unproved", "crossed_rows_or_tables",
    "ambiguous_structural_relation", "merged_value_or_action_unproved", "applicability_unproved",
    "unproved_row_context_or_variant", "unproved_troubleshooting_relation",
    "unproved_modality_subject_or_condition", "verified_table_relation", "unproved_quantity_context",
    "numeric_format_unproved", "verified_quantity", "different_numeric_value", "unproved_quantity_modality",
    "unhandled_v1_shape", "v1_identity_unresolved", "unhandled_v1_technical_fields",
    "v1_literal_quote_conflict", "v1_symptom_fields_unproved", "v1_value_literal_conflict",
    "v1_component_unproved", "v1_action_condition_unproved", "v1_condition_or_coordinate_unproved",
}

# Safe geometry from the independent R1 acceptance report. This is an
# acceptance assertion only. The verifier receives no fixed page or row.
Q01_LOCATOR_ROWS = (
    ((2, 0),), ((2, 1), (2, 0)), ((2, 2), (2, 1)), ((3, 1), (2, 0)), ((3, 2), (3, 1)),
)
Q01_CELL_BOXES = {
    (2, 0): (79.704, 539.110, 233.930, 613.390),
    (2, 1): (233.930, 539.110, 389.950, 583.630),
    (2, 2): (389.950, 539.110, 558.740, 583.630),
    (3, 1): (233.930, 583.630, 389.950, 613.390),
    (3, 2): (389.950, 583.630, 558.740, 613.390),
}



def require(test, reason):
    if not test:
        raise ValueError(reason)


def local_corpus(site, cache):
    entries, dossiers, _ = load(site, cache)
    manifest = freeze(entries, dossiers)
    require(manifest == json.loads((REPORTS / "corpus-manifest.json").read_text())
            and freeze_digest(manifest) == MANIFEST, "canonical_freeze_mismatch")
    return entries, dossiers, manifest


def historical(entries, dossiers, manifest, cache):
    questions = {row["id"]: row["question"] for row in json.loads(QUESTIONS.read_text())["questions"]}
    pinned = json.loads((REPORTS / "r1-calibration-sizing.json").read_text())["requests"]
    count, _ = context.get_counter(cache / context.TOKENIZER_NAME)
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, text=True, timeout=10, check=True)
    match = re.search(r"pdftotext version (\d{1,3}\.\d{1,3}(?:\.\d{1,3})?)", version.stderr + version.stdout)
    observations = {}
    for question_id, cal_wire in OLD_WIRES.items():
        expected = {key: pinned[question_id][key] for key in SIZING_FIELDS + WIRE_FIELDS}
        expected["estimate"] = WSL_ESTIMATES[question_id]
        site_fields = ("site_raw_local_tokens", "site_raw_utf8_bytes", "metadata_without_site_raw_local_tokens")
        expected.update({key: pinned[question_id][key] for key in site_fields})
        with TemporaryDirectory() as directory:
            work = Path(directory)
            provider = NativeD1(cache, Ledger(work / "ledger"), manifest=manifest)
            seen = []

            def record(_request, question, site, docs, history, _now, _cap):
                approval = wire_approval(question, site, docs, history)
                sizing = context.size(question, site, docs, history, cache)
                raw = [page["raw"] for page in site]
                no_raw = [{key: value for key, value in page.items() if key != "raw"} for page in site]
                metadata = encoded({"pages": no_raw, "documents": docs})
                seen.append(({key: sizing[key] for key in SIZING_FIELDS} | approval |
                             {"estimate": sizing["estimate"]}, sizing["pdf"],
                             {"site_raw_local_tokens": sum(map(count, raw)),
                              "site_raw_utf8_bytes": sum(len(text.encode()) for text in raw),
                              "metadata_without_site_raw_local_tokens": count(metadata)},
                             not any(item.get("unavailable") for item in sizing["per_pdf"].values()),
                             sizing["method"] == pinned[question_id]["method"], not history))
                return "offline_wire_checked", None, {}

            provider.dispatch = record
            provider.send = OfflineConsultant._reject_send
            pilot = Pilot(entries, dossiers, cache, Journal(work / "journal"), provider, owner_dc02=True)
            peer = "127.0.0.1"
            result = pilot.ask(peer, pilot.open(peer), "wire", questions[question_id])
            checks = {"dispatch": result["status"] == "offline_wire_checked" and len(seen) == 1,
                      "zero_posts": provider.chat_posts == 0,
                      "cal_wire": CAL_WIRES[question_id] == cal_wire,
                      "material_scope": result.get("material_scope") == pinned[question_id]["scope"]}
            actual, pdf, site_stats = {}, None, {}
            if seen:
                actual, pdf, site_stats, available, method_ok, empty_history = seen[0]
                checks.update(pdf_available=available, tokenizer_method=method_ok, empty_history=empty_history)
                actual.update(site_stats)
                checks.update({key: actual.get(key) == value for key, value in expected.items()})
            observations[question_id.lower()] = {"expected": expected, "actual": actual, "pdf_local_tokens": pdf,
                                                 "checks": checks,
                                                 "passed": all(checks.values())}
    return {"baseline": "independent_wsl_dc03b", "poppler_version": match[1] if match else None,
            "requests": observations, "passed": all(row["passed"] for row in observations.values())}


def q01_evidence(packet):
    context_reasons = {
        "formatting": {"running_document_id", "physical_page_number"},
        "navigation": {"table_caption", "table_reference"},
        "safety": {"general_work_safety"},
        "applicability": {"applicability_text"},
        "unresolved": {"unresolved_linked_text"},
        "unlinked": {"detached_text"},
    }
    context_issues = {"missing_row_cell", "unresolved_column", "unresolved_table_context",
                      "unproved_row_applicability"}

    def safe_box(bbox):
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4 or any(
                type(n) not in (float, int) or not math.isfinite(n) or abs(n) > 10**6 for n in bbox):
            return None
        return list(bbox)

    def locator(value):
        keys = ("page", "table", "row", "column")
        if any(type(value.get(key)) is not int or not 0 <= value[key] <= 10000 for key in keys):
            return None
        bbox = safe_box(value.get("bbox"))
        return {key: value[key] for key in keys} | {"bbox": bbox} if bbox else None

    def context(entry):
        category, reason = entry.get("category"), entry.get("reason")
        if reason not in context_reasons.get(category, ()):
            return None
        boxes = [safe_box(bbox) for bbox in entry["boxes"][:12]]
        return {"category": category, "reason": reason, "boxes": [box for box in boxes if box is not None]}

    rows = []
    for index, row in enumerate(packet["v2_claims"][:5], 1):
        status = row.get("technical_status")
        locators = [locator(item) for item in row.get("locators", [])[:8]]
        evidence = [context(item) for item in row.get("context_evidence", [])[:16]]
        rows.append({"claim": index, "id_matches": row.get("id") == str(index),
                     "verdict": status if status in VERDICTS else "unknown",
                     "flags": {flag: row.get(flag) if type(row.get(flag)) is bool else None for flag in Q01_FLAGS},
                     "reasons": [reason for reason in row.get("reason_codes", []) if reason in Q01_REASONS],
                     "locators": [item for item in locators if item is not None],
                     "context_issues": [issue for issue in row.get("context_issues", []) if issue in context_issues],
                     "context_evidence": [item for item in evidence if item is not None]})
    legacy = packet["v1"]["legacy"]
    coverage = packet["coverage"]
    count = len(packet["v2_claims"])
    return {"claim_count": count, "claims": rows, "v1": legacy if legacy == "invalid_locator" else "unexpected",
            "coverage": coverage if coverage == "semantic_pending" else "unexpected",
            "confirmed": sum(row["verdict"] == "supported" for row in rows),
            "historical_wire_matches": packet.get("historical_wire") == OLD_WIRES["Q01"][0],
            "confirmed_ids_match": packet["confirmed_claim_ids"] == ["1", "2", "3", "4", "5"],
            "actual_new_model_candidate": False}


def q01_locators_preserved(claims):
    observed = [tuple((loc["page"], loc["table"], loc["row"], loc["column"],
                       tuple(round(value, 3) for value in loc["bbox"]))
                      for loc in claim["locators"]) for claim in claims]
    expected = [tuple((60, 1, row, column, Q01_CELL_BOXES[row, column]) for row, column in locations)
                for locations in Q01_LOCATOR_ROWS]
    return observed == expected


def authentic(site, cache):
    try:
        packet = replay(Path(os.environ["DS_DC_Q01_CANDIDATE"]), site, cache)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        reason = str(error)
        return {"passed": False, "reason": reason if reason in
                {"fixture_corpus_mismatch", "fixture_wire_mismatch", "shadow_not_executed"} else "replay_failed"}
    result = q01_evidence(packet)
    result["locators_preserved"] = q01_locators_preserved(result["claims"])
    result["passed"] = (
        result["v1"] == "invalid_locator" and result["coverage"] == "semantic_pending"
        and result["historical_wire_matches"] and result["confirmed_ids_match"]
        and result["claim_count"] == result["confirmed"] == 5 and result["locators_preserved"]
        and all(row["id_matches"] for row in result["claims"]))
    return result


def new_wire(entries, dossiers, cache):
    # Synthetic response JSON selecting an actual pinned site field. This probe
    # is separate from Q01-N and its model packet carries no ground truth.
    observed = {}

    def transport(payload):
        material = json.loads(payload["messages"][-1]["content"][-2]["text"])
        key, source = next((key, src) for key, src in material["sources"].items() if src["kind"] == "site")
        _, _, data = front(source["markdown"].encode())
        payload = {field: material[field] for field in ("version", "request_id", "wire_identity")}
        payload.update(claims=[], answer_claim_ids=[], unresolved=[], evidence_extracts=[
            dict(id="X1", entity=source["entity"], source=key, field="features[1]",
                 quote=data["features"][1], conditions=[], parts=["P1"])])
        observed["calls"] = observed.get("calls", 0) + 1
        return MockReply(json.dumps(payload).encode())

    with OfflineConsultant(entries, dossiers, cache, transport) as advisor:
        first = advisor.ask("Какие данные БКД-ПК-RF.2 считывает из памяти приборов?", request_id="probe-site-v1")
        require(first["status"] == "reference" and len(first["extracts"]) == 1
                and first["extracts"][0]["citations"][0]["commit"] == "084d759487bfab6e111549c9b5469711ac5fc13e"
                and observed.get("calls") == 1, "pinned_site_extract_failed")
    sizing = first["diagnostics"]["sizing"]
    require(sizing["unique_files"] == 4 and sizing["physical_pages"] == 80, "new_bkd_dossier_changed")
    with OfflineConsultant(entries, dossiers, cache, None) as advisor:
        sld = advisor.ask("Для чего предназначена СЛДКС-1?", request_id="probe-sld-sizing-v1")
    sld_size = sld["diagnostics"]["sizing"]
    require(sld["status"] in {"over_cap", "mock_not_run"} and sld_size["unique_files"] == 10
            and sld_size["physical_pages"] == 403, "new_sld_dossier_changed")
    return {"probe": "synthetic_mock_from_pinned_site", "bkd_wire": first["diagnostics"]["wire_identity"],
            "bkd_tokens": sizing["estimate"], "bkd_micro_usd": sizing["estimated_cold_micro_usd"],
            "sld_wire": sld["diagnostics"]["wire_identity"], "sld_tokens": sld_size["estimate"],
            "sld_micro_usd": sld_size["estimated_cold_micro_usd"], "sld_status": sld["status"],
            "verified_provider_bound": False, "provider_operations": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("freeze", "historical", "authentic", "new-wire"))
    args = parser.parse_args()
    site, cache = (Path(os.environ[key]) for key in ("SATURN_SOURCE", "DS_DC_CACHE"))
    if args.check == "authentic":
        result = authentic(site, cache)
    else:
        entries, dossiers, manifest = local_corpus(site, cache)
        if args.check == "historical":
            result = historical(entries, dossiers, manifest, cache)
        elif args.check == "new-wire":
            result = new_wire(entries, dossiers, cache)
        else:
            require(set(dossiers) == {BKD, SLD}, "pilot_scope_changed")
            result = {"manifest_sha256": MANIFEST}
    print(json.dumps(result))
    return 0 if result.get("passed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
