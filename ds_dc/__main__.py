"""Local operator CLI. Explicit --fetch is solely for approved publisher PDFs."""
import argparse
from collections import Counter
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from .corpus import BKD, COMMIT, dossiers, inventory
from .runtime import MockD1, Pilot, Journal
from .reference_review import reference_review
from .finance import Ledger, Stopped
from .native import CONTROLLED_CAL, NativeD1, mock_transport
from .prep import freeze, freeze_digest, load, restore

CASE_FILE = Path(__file__).resolve().parents[1] / "docs/reports/DS-DC-01-RESOLVER-CASES.json"
PEER = "192.0.2.10"
WHEN = 1_795_000_000


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def prepare(pilot):
    for dossier in pilot.dossiers.values():
        if dossier["state"] == "ready":
            for doc in dossier["included_docs"]:
                pilot.provider.prepare(doc, WHEN)


def run_cases(entries, registry, cache, output):
    output.mkdir(parents=True, exist_ok=True)
    write(output / "catalogue.json", [{k: v for k, v in row.items() if k not in ("body", "raw")}
                                     for row in entries.values()])
    write(output / "dossiers.json", registry)
    cases = json.loads(CASE_FILE.read_text())
    cases.extend([
        dict(id="holdout-rs485", question="Какие изделия поддерживают RS-485?", expected=[]),
        dict(id="holdout-software", question="Для чего нужен БУСЛоРа?", expected=["saturn:software:buslora"]),
        dict(id="holdout-variant", question="Опишите СЛДКС-99", expected=[]),
    ])
    records = []
    with TemporaryDirectory(dir=cache) as directory, patch("socket.socket",
            side_effect=AssertionError("network disabled during offline scenarios")):
        for case in cases:
            provider = MockD1(1_000_000)
            pilot = Pilot(entries, registry, cache, Journal(directory), provider, case.get("cap", 64_000),
                          review=reference_review(cache))
            prepare(pilot)
            token = pilot.open(PEER, WHEN)
            if case.get("active"):
                pilot.ask(PEER, token, "seed", "Что такое БКД-ПК-RF.2?", now=WHEN)
            result = pilot.ask(PEER, token, "case", case["question"], hint=case.get("hint"), now=WHEN + 1)
            decision = result.get("decision", {})
            selected = decision.get("selected", [])
            acceptable = selected == case["expected"] or (case.get("allow_clarification")
                         and not selected and any(c["id"] in case["expected"] for c in decision["candidates"]))
            status = result["status"]
            if case["id"] == 12:
                acceptable = acceptable and status == "over_cap" and result["mock_posts"] == 0
            if case["id"] in (1, 4, 6):
                acceptable = acceptable and status == "draft" and result["mock_posts"] == 1
            verdict = "FAIL" if not acceptable else "BLOCKED" if status in {"not_ready", "over_cap"} and case["id"] in (3, 7, 8) else "PASS"
            records.append(dict(case=case, result=result, verdict=verdict,
                                composition={k: registry.get(k, {"state": "not_ready"})["state"] for k in selected},
                                seed_posts=provider.chat_posts - result.get("mock_posts", 0),
                                mock_uploads=provider.uploads, real_api_calls=0))
            if case["id"] == 1 and provider.last_wire:
                body = provider.last_wire
                content = body["messages"][-1]["content"]
                material = json.loads(content[-2]["text"])
                write(output / "mock-wire-redacted.json", dict(
                    model=body["model"], thinking=body["thinking"], max_tokens=body["max_tokens"],
                    stream=body["stream"], file_parts=[dict(type="file", file_id="[mock handle]")
                    for part in content if part["type"] == "file"],
                    pages=[dict(path=page["path"], sha256=page["sha256"],
                                utf8_bytes=len(page["raw"].encode())) for page in material["pages"]],
                    documents=material["documents"], real_api_calls=0,
                    cold_chat_reserved_micro_usd=provider.reserved,
                    file_reserved_micro_usd=provider.file_reserved))
    write(output / "resolver.json", records)
    print(json.dumps(dict(site_commit=COMMIT, entries=len(entries),
                          verdicts=Counter(row["verdict"] for row in records)), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--fetch", action="store_true")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--evaluate", type=Path)
    action.add_argument("--question", action="append")
    action.add_argument("--chat", action="store_true")
    action.add_argument("--freeze", type=Path)
    action.add_argument("--evaluate-dc02", type=Path)
    action.add_argument("--cleanup-sha")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--live-go", type=Path, help="Private operator approval, never needed in PREP.")
    parser.add_argument("--manifest", type=Path, help="Frozen corpus manifest required by live GO.")
    parser.add_argument("--contract", type=Path, help="Reviewed provider contract required by live GO.")
    parser.add_argument("--ledger", type=Path, help="Private durable ledger required by live GO.")
    parser.add_argument("--legacy-dc01", action="store_true", help="Use historical DC-01 question path.")
    parser.add_argument("--p0", action="store_true")
    parser.add_argument("--reference-only", action="store_true",
                        help="Explicitly scope material to the root card and pinned origin manual.")
    args = parser.parse_args()
    args.cache.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not args.evaluate and not args.legacy_dc01:
        return dc02(args, parser)
    if args.live_go:
        parser.error("live GO is incompatible with DC-01")
    if args.legacy_dc01 and not (args.question or args.evaluate):
        parser.error("DC-01 supports --question and --evaluate")
    entries, excluded = inventory(args.site)
    audit_path = args.cache / "audit.json"
    audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
    registry = dossiers(entries, args.cache, args.fetch, audit=audit, reference_only=args.reference_only)
    if args.evaluate:
        run_cases(entries, registry, args.cache, args.evaluate)
        write(args.evaluate / "inventory.json", dict(commit=COMMIT, excluded=excluded,
              kinds=Counter(row["kind"] for row in entries.values()),
              states=Counter(row["state"] for row in entries.values())))
        return
    provider = MockD1(1_000_000)
    pilot = Pilot(entries, registry, args.cache, Journal(args.cache / "journal"), provider,
                  review=reference_review(args.cache))
    prepare(pilot)
    token = pilot.open(PEER, WHEN)
    for i, question in enumerate(args.question):
        print(json.dumps(pilot.ask(PEER, token, f"turn-{i}", question,
                         mode="P0" if args.p0 else "D1", now=WHEN + i), ensure_ascii=False))


def dc02(args, parser):
    import time
    from uuid import uuid4

    if args.live_go and (args.fetch or args.freeze or args.evaluate_dc02
                         or not args.manifest or not args.ledger or not args.contract):
        parser.error("live GO requires a frozen manifest, reviewed contract and durable ledger")
    if args.fetch:
        restore(args.cache)
    entries, registry, _ = load(args.site, args.cache, reference_only=args.reference_only)
    manifest = freeze(entries, registry)
    if args.freeze:
        write(args.freeze, manifest)
        print(freeze_digest(manifest))
        return
    if args.evaluate_dc02:
        from .evaluate import evaluate
        evaluate(entries, registry, manifest, args.cache, args.evaluate_dc02)
        return
    if args.live_go:
        if args.live_go.stat().st_mode & 0o077 or args.live_go.is_symlink():
            parser.error("GO file must be private")
        if json.loads(args.manifest.read_text()) != manifest:
            parser.error("corpus drift")
        repo = Path(__file__).resolve().parents[1]
        git = lambda *command: subprocess.check_output(["git", "-C", str(repo), *command], text=True).strip()
        if git("status", "--porcelain"):
            parser.error("live GO requires an exact, clean published revision")
        approval = json.loads(args.live_go.read_text())
        if bool(args.cleanup_sha) != (approval.get("kind") == "cleanup"):
            parser.error("cleanup requires a dedicated GO and --cleanup-sha")
        if approval.get("kind") == CONTROLLED_CAL and (
                args.chat or args.p0 or args.reference_only or len(args.question or []) != 1):
            parser.error("controlled calibration requires one pinned CLI question")
        live = (approval, git("rev-parse", "HEAD"), os.getenv("DEEPSEEK_API_KEY", ""),
                json.loads(args.contract.read_text()))
        provider = NativeD1(args.cache, Ledger(args.ledger), manifest=manifest, live=live)
        if args.cleanup_sha:
            try:
                provider.cleanup(args.cleanup_sha, time.time())
            except Stopped as exc:
                parser.exit(1, f"{exc}\n")
            print("delete_acknowledged")
            return
        return run_dc02(args, entries, registry, provider, time, uuid4)
    if args.cleanup_sha:
        parser.error("cleanup requires operator GO")
    # Explicit fixture transport is the default, regardless of environment credentials.
    with TemporaryDirectory(prefix="ds-dc02-fixture-") as temporary:
        provider = NativeD1(args.cache, Ledger(temporary), manifest=manifest, fixture=mock_transport())
        return run_dc02(args, entries, registry, provider, time, uuid4)


def run_dc02(args, entries, registry, provider, time, uuid4):
    pilot = Pilot(entries, registry, args.cache, Journal(args.cache / "journal-dc02"), provider,
                  cap=None, owner_dc02=True, review=reference_review(args.cache))
    if args.chat:
        from .owner_web import serve
        return serve(pilot, args.port)
    token = pilot.open(PEER)
    for question in args.question:
        result = pilot.ask(PEER, token, str(uuid4()), question,
                           mode="P0" if args.p0 else "D1", now=time.time())
        print(json.dumps(result, ensure_ascii=False))
        if provider.controlled and result["status"] != "calibration_observed":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
