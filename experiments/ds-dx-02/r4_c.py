"""Owner-only streaming continuation of the frozen R4-A P/V pairs."""
import argparse
import getpass
import json
import os
import time
from pathlib import Path
from zipfile import ZipFile

from bundle import sums
from compile_d import multipart, payload
from protocol import (Ledger, Stop, encode, kernel_release, live_gate, load, locked, money,
                      offline, runtime_digest, save, sha, transport)
from r4_a import finances, plan, run_matrix, score, validate_card

CASES = ("P-D", "P-L", "V-D", "V-L")
BUDGET_LOCK = ".r4-budget"


def original(workspace, card_path, frozen_sha):
    path = workspace / "r4-a-plan/manifest-frozen.json"
    raw = path.read_bytes()
    if sha(raw) != frozen_sha:
        raise Stop("Original frozen manifest differs from the approved digest")
    frozen = json.loads(raw)
    experiment = frozen["experiment"]
    expected = plan(workspace / "source-pilot")
    if {k: v for k, v in experiment.items() if k not in {"runtime", "kernel"}} != {
            k: v for k, v in expected.items() if k not in {"runtime", "kernel"}}:
        raise Stop("R4-A inputs and fixed request settings differ from the pinned continuation")
    card = card_path.read_bytes()
    if sha(card) != frozen["card_sha256"]:
        raise Stop("Engineering card differs from the original R4-A pin")
    validate_card(json.loads(card), experiment)
    return experiment, frozen["card_sha256"]


def verified_checkpoint(state, op):
    raw = (state / "r4-a" / (op["id"] + ".json")).read_bytes()
    data = json.loads(raw)
    if (op["status"] != "SETTLED" or sha(raw) != op["result_sha256"]
            or data["cost_nd"] != op["cost_nd"]):
        raise Stop("Original R4-A checkpoint failed ledger verification")
    return data


def pdf_checkpoint(workspace, experiment, frozen_sha, history):
    """A verified lease can be reused until expiry; remote availability is unknown offline."""
    state = workspace / "private-r4-a"
    go = load(state / "owner-go.json")
    stage = history["stages"]["r4-a"]
    if go["manifest_sha256"] != frozen_sha or go["identity"] != stage["identity"]:
        raise Stop("Original R4-A Owner GO does not bind this frozen manifest")
    ops = history["ops"]
    if [(op["id"], op["status"]) for op in ops] != [
            ("A-D", "SETTLED"), ("A-L", "SETTLED"), ("pdf-upload", "SETTLED"), ("P-D", "UNKNOWN")]:
        raise Stop("Continuation requires exactly the recorded R4-A outcome; inspect any different history")
    if any(op["stage"] != "r4-a" for op in ops):
        raise Stop("Unexpected stage in the original R4-A ledger")
    for op in ops[:2]:
        verified_checkpoint(state, op)
    upload = experiment["upload"]
    pdf = (workspace / "source-pilot/pdf" / (upload["source"] + ".pdf")).read_bytes()
    upload_op = ops[2]
    if (sha(pdf) != upload["sha256"] or len(pdf) != upload["size"]
            or upload_op["request_sha256"] != sha(multipart(pdf)[0])
            or upload_op["cost_nd"] != upload["reserve_nd"]):
        raise Stop("Original PDF upload differs from the frozen request")
    result = verified_checkpoint(state, upload_op)
    if (not isinstance(result["handle"], str) or not result["handle"].startswith("file-api-")
            or type(result["expires_at"]) is not int):
        raise Stop("Invalid stored PDF lease")
    first = next(case for case in experiment["cases"] if case["id"] == "P-D")
    task, source = first["task"], upload["source"]
    root = workspace / "source-pilot"
    context = load(root / "plan/context.json")[source]
    group = (source, {n: context[n - 1] for n in task["scope"][source]})
    original_body, original_prefix = payload(
        root, load(root / "source-manifest.json"), task,
        {source: dict(result, first=1, last=upload["pages"])}, {}, group, mode=first["mode"])
    if (ops[3]["request_sha256"] != sha(original_body) or ops[3]["prefix_sha256"] != original_prefix
            or ops[3]["reserve_nd"] != first["reserve_nd"]):
        raise Stop("Original UNKNOWN P-D request differs from the frozen input and handle")
    return result


def continuation(workspace, card, frozen_sha, file_mode, *, now=None):
    original_plan, card_sha = original(workspace, card, frozen_sha)
    if (workspace / "private-r4-b/ledger.json").exists() or (workspace / "private-r4-b/.inflight").exists():
        raise Stop("R4-B history exists; a continuation would require a new joint financial decision")
    baseline = finances(workspace, include_r4_a=True)
    a_ledger = workspace / "private-r4-a/ledger.json"
    ledger_bytes = a_ledger.read_bytes()
    if sha(ledger_bytes) != baseline["r4_a_sha256"]:
        raise Stop("Original R4-A ledger changed during financial verification")
    pdf = pdf_checkpoint(workspace, original_plan, frozen_sha, json.loads(ledger_bytes))
    now = time.time() if now is None else now
    reuse_possible = pdf["expires_at"] > now
    if file_mode == "reuse" and not reuse_possible:
        raise Stop("Original PDF lease expired; prepare upload plan only for separate upload Owner GO")
    if file_mode not in {"reuse", "upload"}:
        raise Stop("Choose reuse or separately approved upload")
    cases = [case for case in original_plan["cases"] if case["id"] in CASES]
    if tuple(case["id"] for case in cases) != CASES:
        raise Stop("Unexpected continuation matrix")
    original_score = workspace / "private-r4-a/engineering/score.json"
    upload_reserve = original_plan["upload"]["reserve_nd"] if file_mode == "upload" else 0
    experiment = dict(cases=cases, upload=original_plan["upload"], snapshot=original_plan["snapshot"],
                      graph_bound_nd=sum(case["reserve_nd"] for case in cases) + upload_reserve)
    result = dict(schema=1, experiment=experiment, runtime=runtime_digest(), kernel=kernel_release(),
                  frozen_sha256=frozen_sha, card_sha256=card_sha, streaming=True,
                  old_score_sha256=sha(original_score.read_bytes()) if original_score.exists() else None,
                  file_mode=file_mode, old_pdf_expires_at=pdf["expires_at"], upload_reserve_nd=upload_reserve,
                  first_reserve_nd=upload_reserve if upload_reserve else cases[0]["reserve_nd"],
                  prior_financial_exposure=baseline)
    return result, pdf if file_mode == "reuse" else None


def engineering_score(workspace, card, review):
    state = workspace / "private-r4-c"
    go = load(state / "owner-go.json")
    if sha(card.read_bytes()) != go["card_sha256"]:
        raise Stop("Review requires the original frozen engineering card")
    report = workspace / "reports-r4-c/r4-c-summary.zip"
    if sha(report.read_bytes()) != report.with_suffix(".zip.sha256").read_text().split()[0]:
        raise Stop("Summary ZIP checksum mismatch")
    output = state / "engineering/score.json"
    if output.exists():
        raise Stop("Continuation score already exists")
    with ZipFile(report) as source:
        entries = {"summary.json": source.read("summary.json")}
        if source.read("SHA256SUMS") != sums(entries):
            raise Stop("Continuation summary checksum mismatch")
    save(output, score(load(card), load(review), json.loads(entries["summary.json"])))


def validate_go(args, pins):
    cap, total = money(args.owner_go_usd), money(args.total_go_usd)
    baseline = pins["prior_financial_exposure"]
    first_chat = pins["experiment"]["cases"][0]["reserve_nd"]
    if (not args.acknowledge_prior_p_d_unknown or not args.confirm_provider_contract or not args.owner_go.strip()
            or not pins["upload_reserve_nd"] + first_chat <= cap <= min(total, baseline["max_compile_nd"])
            or total > baseline["max_total_nd"]):
        raise Stop("Owner GO must cover prior UNKNOWN, provider contract and remaining financial ceilings")
    upload_go = args.upload_owner_go
    if pins["file_mode"] == "upload":
        if not upload_go or not upload_go.strip() or upload_go.strip() == args.owner_go.strip():
            raise Stop("A new PDF upload requires a separate Owner GO")
    elif upload_go is not None:
        raise Stop("The reuse plan authorizes no PDF upload")
    return cap, total


def verify_preflight(workspace, pins):
    preflight = load(workspace / "preflight-r4-c/preflight.json")
    if any(preflight.get(k) != v for k, v in dict(
            snapshot=pins["experiment"]["snapshot"], runtime=pins["runtime"], kernel=pins["kernel"],
            r4_c_sse=True, offline="seccomp: socket EPERM", paid_calls=0, package_count=3).items()):
        raise Stop("Run the full R4-C offline preflight on this WSL host")


def run_live(workspace, args):
    state, reports = workspace / "private-r4-c", workspace / "reports-r4-c"
    if state.is_symlink() or reports.is_symlink() or reports.exists():
        raise Stop("Require fresh nonsymlink continuation paths")
    with locked(workspace / BUDGET_LOCK), locked(state):
        if set(p.name for p in state.iterdir()) != {".lock"} or reports.exists():
            raise Stop("R4-C is single-use; inspect the existing continuation offline")
        pins, reused_file = continuation(workspace, args.card, args.frozen_sha256, args.file)
        plan_bytes = (workspace / f"r4-c-plan-{args.file}.json").read_bytes()
        if sha(plan_bytes) != args.plan_sha256 or json.loads(plan_bytes) != pins:
            raise Stop("Continuation plan or prior evidence changed since approval")
        verify_preflight(workspace, pins)
        cap, total = validate_go(args, pins)
        original_go = load(workspace / "private-r4-a/owner-go.json")["owner_go"]
        if args.owner_go.strip() == original_go.strip():
            raise Stop("The continuation requires a new Owner GO")
        identity = sha(encode([args.plan_sha256, args.owner_go, args.upload_owner_go, cap, total]))
        journal = Ledger(state / "ledger.json", "r4-c", cap, total, identity)
        key = getpass.getpass("Ключ DeepSeek: ")
        if not key:
            raise Stop("Empty key")
        save(state / "ledger.json", journal.data)
        save(state / "owner-go.json", dict(owner_go=args.owner_go, upload_owner_go=args.upload_owner_go,
             identity=identity, plan_sha256=args.plan_sha256, frozen_sha256=args.frozen_sha256,
             card_sha256=pins["card_sha256"], prior_financial_exposure=pins["prior_financial_exposure"],
             acknowledged_prior_p_d_unknown=True))
        result = run_matrix(workspace / "source-pilot", pins["experiment"], journal, transport(key), reports,
                            execution="live", streaming=True, reused_file=reused_file)
        if result["status"] == "PARTIAL":
            raise Stop("R4-C PARTIAL; inspect the new summary and reserve before any future decision")


def main():
    cli = argparse.ArgumentParser()
    subs = cli.add_subparsers(dest="command", required=True)
    for name in ("prepare", "live", "score"):
        sub = subs.add_parser(name)
        sub.add_argument("--workspace", required=True, type=Path)
        sub.add_argument("--card", required=True, type=Path)
        if name == "score":
            sub.add_argument("--review", required=True, type=Path)
        else:
            sub.add_argument("--frozen-sha256", required=True)
            sub.add_argument("--file", choices=("reuse", "upload"), required=True)
        if name == "live":
            for flag in ("plan-sha256", "owner-go", "owner-go-usd", "total-go-usd"):
                sub.add_argument("--" + flag, required=True)
            sub.add_argument("--upload-owner-go")
            sub.add_argument("--acknowledge-prior-p-d-unknown", action="store_true")
            sub.add_argument("--confirm-provider-contract", action="store_true")
    args = cli.parse_args()
    os.umask(0o077)
    workspace = args.workspace.resolve(strict=True)
    if args.command == "live":
        live_gate()
        run_live(workspace, args)
        return
    offline()
    if args.command == "score":
        engineering_score(workspace, args.card, args.review)
        return
    pins, _ = continuation(workspace, args.card, args.frozen_sha256, args.file)
    verify_preflight(workspace, pins)
    output = workspace / f"r4-c-plan-{args.file}.json"
    if output.exists() or output.is_symlink():
        raise Stop("Continuation plan already exists")
    save(output, pins)
    print(encode(pins).decode())
    print("Continuation plan SHA256 " + sha(output.read_bytes()))


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
