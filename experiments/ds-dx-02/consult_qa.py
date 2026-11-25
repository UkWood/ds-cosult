"""Source-free CONSULT-01 preflight, historical budget pins and owner launch."""
import argparse
import getpass
import json
import os
import sys
from collections import Counter
from pathlib import Path

from bundle import FORBIDDEN, archive, read_bundle, sums, verify_zip
from consult_d import CONTEXT_BYTES, LIMIT, SAFETY_TERMS, conduct, questions, report, select, words
from progress import Progress, reporting
from protocol import (Ledger, Stop, encode, kernel_release, live_gate, locked, money, offline,
                      reserve, runtime_digest, save, sha, transport)
from qa_pins import PINS, QUESTION_SHA256
from reconcile import summarize

QUESTIONS = Path(__file__).with_name("configs") / "DS-DX-02-R4-B-QA-CONSULT-QUESTIONS.json"
HISTORIES = ("private-state", "private-r3", "private-r4-a", "private-r4-c", "private-r4-b")


def consultation_finances(workspace):
    rows = {}
    for directory in HISTORIES:
        path = workspace / directory / "ledger.json"
        history = summarize(path)
        if any(op["status"] == "SETTLED" and op["checkpoint"] != "verified" for op in history["operations"]):
            raise Stop("A historical settled checkpoint failed financial verification")
        rows[directory] = {key: history[key] for key in ("ledger_sha256", "spent_nd", "retained_nd")}
    b = rows["private-r4-b"]
    if b["ledger_sha256"] != PINS["ledger"] or b["retained_nd"]:
        raise Stop("R4-B financial ledger differs from the pinned release")
    previous = sum(max(row["spent_nd"] + row["retained_nd"], floor) for row, floor in zip(
        rows.values(), (5_267_700, 461_289_132, 0, 0, 0), strict=True))
    ledger = workspace / "private-r4-b/ledger.json"
    raw = ledger.read_bytes()
    if sha(raw) != PINS["ledger"]:
        raise Stop("R4-B financial ledger changed during verification")
    previous_go_remaining = json.loads(raw)["total"] - b["spent_nd"]
    return dict(histories=rows, prior_accounted_nd=previous, original_total_ceiling_nd=5 * 10**9,
                previous_go_remaining_nd=previous_go_remaining,
                max_new_total_nd=min(5 * 10**9 - previous, previous_go_remaining))


def inputs(workspace):
    kb = workspace / "knowledge-r4-b-v1"
    archive_path = workspace / "compile-r4-b-v1/knowledge.zip"
    if sha(archive_path.read_bytes()) != PINS["knowledge"]:
        raise Stop("Original KnowledgeBase archive SHA differs")
    zip_meta = verify_zip(archive_path)
    entries, meta = read_bundle(kb)
    if (zip_meta != meta or meta["identity"] != PINS["identity"] or meta["snapshot"] != PINS["snapshot"]
            or meta["execution"] != "live" or meta["status"] != "PARTIAL"):
        raise Stop("KnowledgeBase directory does not match the pinned PARTIAL release")
    if sha(QUESTIONS.read_bytes()) != QUESTION_SHA256:
        raise Stop("Frozen question file changed")
    rows = questions(QUESTIONS)
    if (len(rows) != 12 or [i for i, row in enumerate(rows, 1) if "dialog" in row] != [10, 11]
            or any(row.get("dialog") != "serial" for row in rows[9:11])
            or any(row.get("images") for row in rows)):
        raise Stop("Frozen CONSULT series shape changed")
    return entries, meta, rows


def inspect_selector(entries, rows):
    index = {row["fact_id"]: row for row in json.loads(entries["index.json"])}
    critical = set()
    for key, row in index.items():
        lines = entries[row["path"]].decode().splitlines()
        lo, hi = row["lines"]
        if row.get("critical") or row["kind"] == "unresolved" or words("\n".join(lines[lo-1:hi])) & SAFETY_TERMS:
            critical.add(key)
    checks = {}
    for n, row in enumerate(rows, 1):
        history = [] if n != 11 else [{"question": rows[9]["question"],
                                       "answer": "Синтетический ответ Q10 для проверки передачи контекста диалога."}]
        body, selection = select(entries, row["question"], history)
        wire = json.loads(body)
        context = wire["messages"][1]["content"]
        prepared = context[0]["text"]
        selected = set(selection["fact_ids"])
        if (not selected or not critical <= selected or "Метаданные" not in prepared
                or not json.loads(entries["sources.json"]) or "База PARTIAL" not in wire["messages"][0]["content"]
                or FORBIDDEN.search(body) or any(block["type"] != "text" for block in context)
                or "tools" in wire or "response_format" in wire or wire["thinking"] != {"type": "disabled"}
                or wire.get("stream") is not True or wire.get("stream_options") != {"include_usage": True}):
            raise Stop(f"Selector safety, critical fact or source check failed for Q{n:02}")
        checks[f"Q{n:02}"] = dict(selection=selection["mode"], context_block_bytes=len(prepared.encode()),
                                 request_bytes=len(body), records=len(selected), critical=len(critical),
                                 kinds=Counter(index[key]["kind"] for key in selected),
                                 source_locators=sum(not loc.startswith("I:") for key in selected
                                                     for loc in index[key]["locators"]),
                                 synthetic_history=bool(history))
    return dict(status="SELECTOR_ONLY", paid_calls=0, limit_completion=LIMIT,
                configured_context_bytes=CONTEXT_BYTES, observed_provider_usage=None, questions=checks)


def plan(workspace, preflight):
    entries, meta, rows = inputs(workspace)
    raw = preflight.read_bytes()
    evidence = json.loads(raw)
    if any(evidence.get(key) != value for key, value in dict(
            snapshot=meta["snapshot"], runtime=runtime_digest(), kernel=kernel_release(),
            offline="seccomp: socket EPERM", paid_calls=0, package_count=3, r4_b_qa=True).items()):
        raise Stop("Run the full QA offline preflight on this WSL host")
    pins = dict(schema=1, knowledge_identity=meta["identity"], archive_sha256=PINS["knowledge"],
                questions_sha256=QUESTION_SHA256, runtime=runtime_digest(), kernel=kernel_release(),
                preflight_sha256=sha(raw), accepted_knowledge_status="PARTIAL",
                chat={"thinking": {"type": "disabled"}, "stream": True,
                      "stream_options": {"include_usage": True}, "max_tokens": LIMIT},
                finance=consultation_finances(workspace), next_reserve_nd=reserve(LIMIT),
                graph_reserve_nd=len(rows) * reserve(LIMIT))
    return pins, entries, meta, rows


def prepare(workspace, preflight):
    pins, entries, _, rows = plan(workspace, preflight)
    review = inspect_selector(entries, rows)
    output = workspace / "qa-r4-b"
    if output.is_symlink():
        raise Stop("QA output directory must not be a symlink")
    path = output / "consult-plan.json"
    if path.exists() or path.is_symlink():
        raise Stop("Choose fresh CONSULT plan output")
    bundle = {"selector.json": encode(review), "consult-plan.json": encode(pins)}
    bundle["SHA256SUMS"] = sums(bundle)
    archive(output / "consult-dryrun.zip", bundle)
    save(path, pins)
    print(encode(dict(plan_sha256=sha(path.read_bytes()), finance=pins["finance"],
                      next_reserve_nd=pins["next_reserve_nd"], graph_reserve_nd=pins["graph_reserve_nd"])).decode())


def live(args):
    live_gate()
    if not args.allow_partial or not args.owner_go.strip() or not args.confirm_provider_contract:
        raise Stop("Confirm PARTIAL, provider contract and separate CONSULT Owner GO")
    workspace = args.workspace.resolve(strict=True)
    state, reports = workspace / "private-consult-01", workspace / "reports-consult-01"
    if state.is_symlink() or reports.is_symlink() or reports.exists():
        raise Stop("Use fresh CONSULT-01 state and reports")
    with locked(workspace / ".r4-budget"), locked(state):
        if set(p.name for p in state.iterdir()) != {".lock"} or reports.exists():
            raise Stop("CONSULT-01 is single-use; inspect existing reports")
        pins, entries, meta, rows = plan(workspace, args.preflight)
        raw = (workspace / "qa-r4-b/consult-plan.json").read_bytes()
        if sha(raw) != args.plan_sha256 or json.loads(raw) != pins:
            raise Stop("Approved CONSULT plan or historical evidence changed")
        cap, total = money(args.owner_go_usd), money(args.total_go_usd)
        if not pins["next_reserve_nd"] <= cap <= total <= pins["finance"]["max_new_total_nd"]:
            raise Stop("CONSULT caps exceed verified remaining total or cannot fund the first reserve")
        identity = sha(encode([args.plan_sha256, args.owner_go, cap, total]))
        journal = Ledger(state / "ledger.json", "consult", cap, total, identity)
        journal.check(pins["next_reserve_nd"])
        key = getpass.getpass("Ключ DeepSeek: ")
        if not key:
            raise Stop("Empty key")
        save(state / "owner-go.json", dict(owner_go=args.owner_go, plan_sha256=args.plan_sha256,
                                         identity=identity, cap_nd=cap, total_nd=total))
        answers = []
        progress = Progress("CONSULT", reports)
        with reporting(progress):
            try:
                conduct(entries, meta, rows, journal, transport(key), answers, progress=progress)
            except Stop as error:
                report(reports, answers, str(error), journal)
                raise
            report(reports, answers, None, journal)
        progress.terminal("COMPLETE_UNREVIEWED")


def main():
    cli = argparse.ArgumentParser()
    commands = cli.add_subparsers(dest="command", required=True)
    for command in ("prepare", "live"):
        sub = commands.add_parser(command)
        sub.add_argument("--workspace", type=Path, required=True)
        sub.add_argument("--preflight", type=Path, required=True)
        if command == "live":
            for flag in ("plan-sha256", "owner-go", "owner-go-usd", "total-go-usd"):
                sub.add_argument("--" + flag, required=True)
            sub.add_argument("--allow-partial", action="store_true")
            sub.add_argument("--confirm-provider-contract", action="store_true")
    args = cli.parse_args()
    os.umask(0o077)
    if args.command == "live":
        live(args)
    else:
        offline(stream=sys.stderr)
        prepare(args.workspace.resolve(strict=True), args.preflight)


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
