"""Local operator CLI. Explicit --fetch is solely for approved publisher PDFs."""
import argparse
from collections import Counter
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from .corpus import BKD, COMMIT, dossiers, inventory
from .runtime import MockD1, Pilot, Journal
from .reference_review import reference_review

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
    parser.add_argument("--p0", action="store_true")
    parser.add_argument("--reference-only", action="store_true",
                        help="Explicitly scope material to the root card and pinned origin manual.")
    args = parser.parse_args()
    args.cache.mkdir(mode=0o700, parents=True, exist_ok=True)
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


if __name__ == "__main__":
    main()
