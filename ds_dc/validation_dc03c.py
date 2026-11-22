"""Offline child checks for the independent DC-03C runner."""
import argparse
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from ds_pilot.discovery import front

from . import context
from .corpus import BKD, SLD
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
    "Q01": ("7498d9920faf9cf25dfbf461c0bc64a75701089423a1c142c1b45cb85e9b9afd", 4, 80, 53289, 15532),
    "Q02": ("d6c1ac408cf46c62c1f653a222c4e5af54d07fbc9981f65c21bb622b55303513", 10, 403, 315380, 122929),
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
    for question_id, (expected_sha, files, pages, size, max_bytes) in OLD_WIRES.items():
        with TemporaryDirectory() as directory:
            work = Path(directory)
            provider = NativeD1(cache, Ledger(work / "ledger"), manifest=manifest)
            seen = []

            def record(_request, question, site, docs, history, _now, _cap):
                require(history == [], "historical_history_changed")
                approval = wire_approval(question, site, docs, history)
                sizing = context.size(question, site, docs, history, cache)
                seen.append((approval["wire_sha256_without_handles"], sizing["unique_files"],
                             sizing["physical_pages"], sizing["estimate"], approval["max_wire_bytes"]))
                return "offline_wire_checked", None, {}

            provider.dispatch = record
            provider.send = OfflineConsultant._reject_send
            pilot = Pilot(entries, dossiers, cache, Journal(work / "journal"), provider, owner_dc02=True)
            peer = "127.0.0.1"
            result = pilot.ask(peer, pilot.open(peer), "wire", questions[question_id])
            require(result["status"] == "offline_wire_checked" and provider.chat_posts == 0
                    and seen == [(expected_sha, files, pages, size, max_bytes)]
                    and CAL_WIRES[question_id] == (expected_sha, files, pages),
                    "historical_wire_or_sizing_mismatch")
    return {"historical_requests_checked": 2, "q01_wire": OLD_WIRES["Q01"][0], "q02_wire": OLD_WIRES["Q02"][0]}


def authentic(site, cache):
    packet = replay(Path(os.environ["DS_DC_Q01_CANDIDATE"]), site, cache)
    require(packet["v1"]["legacy"] == "invalid_locator" and packet["coverage"] == "semantic_pending"
            and packet["historical_wire"] == OLD_WIRES["Q01"][0]
            and packet["confirmed_claim_ids"] == ["1", "2", "3", "4", "5"]
            and all(row["technical_status"] == "supported" for row in packet["v2_claims"]),
            "authentic_q01_verdict_changed")
    return {"supported": 5, "v1": "invalid_locator", "coverage": "semantic_pending",
            "fixture_sha256": packet["fixture_sha256"], "actual_new_model_candidate": False,
            "locators": sum(len(row["locators"]) for row in packet["v2_claims"])}


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


if __name__ == "__main__":
    main()
