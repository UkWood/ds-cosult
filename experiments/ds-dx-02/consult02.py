"""Pinned owner-only runner for CONSULT-02; the benchmark card is test-only."""
import argparse
import getpass
import json
import os
import re
from pathlib import Path
from zipfile import ZipFile

from bundle import archive, sums
from consult_qa import consultation_finances, inputs
from progress import Progress, reporting
from protocol import Ledger, Stop, encode, kernel_release, live_gate, locked, money, reply, reserve, runtime_digest, save, sha, transport
from qa_pins import PINS, QUESTION_SHA256
from reconcile import summarize
from selector_v2 import BOUND, CONTEXT_PROFILES, OUTPUT_LIMIT, PROMPT_LIMIT, REVISION, WIRE_LIMIT, Selector

BASELINE_SHA = "2fe080665f154133a4a278729b6cdc5262ef6093cabd9f949ef59f7bf8124f1a"
OFFLINE_DIR = "consult02-r2-offline"
PRIVATE_DIR = "private-consult-02-r2"
REPORT_DIR = "reports-consult-02-r2"
R1_SWEEP_SHA = "672aa6112c73c933867f482b6de871aad3f385dbf397b1f5e652b5adc239ec20"
CARD_SHA = "7f75793404709bb2bb1c6ca5fb6904eba1bd90cdc039acff8f3850036ce33814"


def baseline_path(workspace):
    return workspace / "reports-consult-01/DS-DX-02B-results.zip"


def r1_sweep_path(workspace):
    return workspace / "consult02-r1-offline/consult02-context-sweep.zip"


def finance(workspace):
    prior = consultation_finances(workspace)
    raw = (workspace / "private-consult-01/ledger.json").read_bytes()
    history = summarize(workspace / "private-consult-01/ledger.json")
    operations = history["operations"]
    if (history["ledger_sha256"] != sha(raw) or history["blocked"] or history["spent_nd"] != 243_085_440
            or [op["id"] for op in operations] != [f"Q{i:02}" for i in range(1, 13)]
            or any(op["stage"] != "consult" or op["checkpoint"] != "verified" for op in operations)):
        raise Stop("CONSULT-01 history does not verify")
    exposure = prior["prior_accounted_nd"] + history["spent_nd"]
    previous = json.loads(raw)["total"] - history["spent_nd"]
    return dict(histories=dict(prior["histories"], **{"private-consult-01": {
                    "ledger_sha256": sha(raw), "spent_nd": history["spent_nd"], "retained_nd": 0}}),
                prior_accounted_nd=exposure, remaining_original_nd=5 * 10**9 - exposure,
                previous_consult_owner_remaining_nd=previous,
                max_new_total_nd=min(5 * 10**9 - exposure, previous,
                                     prior["max_new_total_nd"] - history["spent_nd"]))


def pins(workspace, preflight):
    for directory in ("private-consult-02", "private-consult-02-r1"):
        prior02 = workspace / directory
        if (prior02 / "ledger.json").exists() or (prior02 / ".inflight").exists():
            raise Stop("Earlier CONSULT-02 exposure requires separate financial reconciliation")
    entries, manifest, rows = inputs(workspace)
    check = preflight.read_bytes()
    evidence = json.loads(check)
    if any(evidence.get(key) != value for key, value in dict(
            snapshot=PINS["snapshot"], runtime=runtime_digest(), kernel=kernel_release(),
            offline="seccomp: socket EPERM", paid_calls=0, package_count=3, consult02_r2=True).items()):
        raise Stop("Run full CONSULT-02 preflight on this WSL host")
    if sha(baseline_path(workspace).read_bytes()) != BASELINE_SHA:
        raise Stop("Historical CONSULT-01 archive changed")
    if sha(r1_sweep_path(workspace).read_bytes()) != R1_SWEEP_SHA:
        raise Stop("Historical R1 Context Sweep archive changed")
    budget = finance(workspace)
    next_cost = reserve(OUTPUT_LIMIT)
    plan = dict(schema=1, knowledge_identity=manifest["identity"], knowledge_sha256=PINS["knowledge"],
                snapshot=manifest["snapshot"], questions_sha256=QUESTION_SHA256, test_card_sha256=CARD_SHA,
                baseline_sha256=BASELINE_SHA, r1_sweep_sha256=R1_SWEEP_SHA, runtime=runtime_digest(), kernel=kernel_release(),
                preflight_sha256=sha(check), revision=REVISION, bound=BOUND, context_profiles=CONTEXT_PROFILES,
                accepted_status="PARTIAL", thinking="disabled", transport="SSE with usage", max_output=OUTPUT_LIMIT,
                maximum_prompt_tokens=PROMPT_LIMIT, finance=budget, next_reserve_nd=next_cost,
                graph_reserve_nd=len(rows) * next_cost,
                worst_case_affordable_at_remaining_ceiling=max(0, min(len(rows), budget["max_new_total_nd"] // next_cost)))
    return plan, entries, manifest, rows


def read_zip(path, expected):
    raw = path.read_bytes()
    from io import BytesIO
    if sha(raw) != expected or path.with_suffix(".zip.sha256").read_text().split() != [expected, path.name]:
        raise Stop("ZIP or sidecar checksum mismatch")
    with ZipFile(BytesIO(raw)) as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise Stop("Repeated ZIP names")
        contents = {name: source.read(name) for name in names}
    if contents.pop("SHA256SUMS", None) != sums(contents):
        raise Stop("ZIP internal checksums mismatch")
    return contents


def approved(workspace, preflight, digest):
    fresh, entries, manifest, rows = pins(workspace, preflight)
    raw = (workspace / OFFLINE_DIR / "plan.json").read_bytes()
    saved = json.loads(raw)
    if sha(raw) != digest or saved["pins"] != fresh:
        raise Stop("Approved plan or immutable evidence changed")
    checked = read_zip(workspace / OFFLINE_DIR / "consult02-context-sweep.zip", saved["report_zip_sha256"])
    summary = json.loads(checked["summary.json"])
    if (summary["status"] != "PASS" or summary["card_sha256"] != CARD_SHA or summary["matched"] != 54
            or json.loads(checked["plan-pins.json"]) != fresh
            or sha(checked["summary.json"]) != saved["summary_sha256"]):
        raise Stop("Independent selector acceptance did not pass")
    profile = saved["selected_profile"]
    if (profile not in CONTEXT_PROFILES or summary["minimum_series_profile"] != profile
            or summary["profiles"][profile]["status"] != "PASS"
            or saved["local_wire_bytes"] != CONTEXT_PROFILES[profile]):
        raise Stop("Approved profile differs from the minimum passing Context Sweep profile")
    return dict(fresh, local_wire_bytes=CONTEXT_PROFILES[profile]), entries, manifest, rows


def render_references(answer, sources):
    return re.sub(r"\[(S[1-9][0-9]*)\]", lambda match: (
        "[" + sources[match[1]] + "]" if match[1] in sources else "[источник не подтверждён]"), answer)


def conduct(entries, rows, journal, post, results, progress, *, wire_limit=WIRE_LIMIT):
    selector = Selector(entries)
    histories = {}
    for i, row in enumerate(rows, 1):
        id_ = f"Q{i:02}"
        progress.task, progress.known = id_, len(rows)
        progress.emit("TASK")
        history = histories.setdefault(row["dialog"], []) if "dialog" in row else []
        body, trace = selector.select(row["question"], history, wire_limit=wire_limit)
        result = dict(id=id_, selection=trace, review="UNREVIEWED")
        if not trace["local_bound_ok"]:
            raise Stop(f"{id_}: mandatory evidence cannot fit the pre-dispatch bound")
        if trace["gate"]:
            reason = ("Практическая рекомендация заблокирована из-за противоречивых указаний о разъёме. "
                      "До подключения требуется подтверждение изготовителя."
                      if trace["gate"] == "safety_conflict" else "В выборке недостаточно подтверждённых сведений.")
            result.update(status="LOCAL_LIMITATION", sent=False, answer=reason)
        else:
            answer = journal.execute(id_, "/chat/completions", body, reserve(OUTPUT_LIMIT), post,
                                     lambda data: reply(data, OUTPUT_LIMIT), prefix=trace["context_sha256"])
            result.update(status="MODEL_UNREVIEWED", sent=True, usage=answer["usage"], cost_nd=answer["cost_nd"],
                          finish_reason=answer["finish_reason"], answer=render_references(answer["text"], trace["sources"]))
            progress.spent += answer["cost_nd"]
            if answer["usage"]["prompt_tokens"] > PROMPT_LIMIT:
                result["status"] = "PROMPT_LIMIT_EXCEEDED"
                results.append(result)
                raise Stop(f"{id_}: provider prompt usage exceeded 50000")
            if answer["finish_reason"] != "stop" or not answer["text"].strip():
                result["status"] = "INCOMPLETE_MODEL_RESPONSE"
                results.append(result)
                raise Stop(f"{id_}: unusable model response")
            history.append(dict(question=row["question"], answer=answer["text"]))
        results.append(result)
        progress.completed += 1


def live(args):
    live_gate()
    workspace = args.workspace.resolve(strict=True)
    if not args.allow_partial or not args.confirm_provider_contract or not args.owner_go.strip():
        raise Stop("Confirm PARTIAL, provider contract and a distinct CONSULT-02 Owner GO")
    old = json.loads((workspace / "private-consult-01/owner-go.json").read_bytes())
    if args.owner_go.strip() == old["owner_go"].strip():
        raise Stop("CONSULT-02 requires a distinct Owner GO")
    state, reports = workspace / PRIVATE_DIR, workspace / REPORT_DIR
    if state.is_symlink() or reports.is_symlink() or reports.exists():
        raise Stop("Require fresh private state and report paths")
    with locked(workspace / ".r4-budget"), locked(state):
        if {p.name for p in state.iterdir()} != {".lock"} or reports.exists():
            raise Stop("CONSULT-02 is single-use")
        plan, entries, _, rows = approved(workspace, args.preflight, args.plan_sha256)
        cap, total = money(args.owner_go_usd), money(args.total_go_usd)
        if not plan["next_reserve_nd"] <= cap <= total <= plan["finance"]["max_new_total_nd"]:
            raise Stop("Approved cap exceeds remaining exposure limit or cannot fund the next reserve")
        identity = sha(encode([args.plan_sha256, args.owner_go, cap, total]))
        journal = Ledger(state / "ledger.json", "consult", cap, total, identity)
        key = getpass.getpass("Ключ DeepSeek: ")
        if not key:
            raise Stop("Empty key")
        save(journal.path, journal.data)
        save(state / "owner-go.json", dict(owner_go=args.owner_go, plan_sha256=args.plan_sha256,
                                          identity=identity, cap_nd=cap, total_nd=total))
        results = []
        progress = Progress("CONSULT-02", reports)
        diagnostic = None
        with reporting(progress):
            try:
                conduct(entries, rows, journal, transport(key), results, progress, wire_limit=plan["local_wire_bytes"])
            except Stop as error:
                diagnostic = str(error)
                raise
            except BaseException:
                diagnostic = "Local execution interrupted"
                raise
            finally:
                ops = journal.data["ops"]
                status = ("STOP" if diagnostic else "PARTIAL" if any(not row["sent"] for row in results)
                          else "COMPLETE_UNREVIEWED")
                bundle = {"consult02.json": encode(dict(status=status, diagnostic=diagnostic, results=results,
                            retained_nd=sum(op["reserve_nd"] for op in ops if op["status"] != "SETTLED"),
                            settled_nd=sum(op["cost_nd"] for op in ops if op["status"] == "SETTLED")))}
                bundle["SHA256SUMS"] = sums(bundle)
                archive(reports / "consult02-results.zip", bundle)
        progress.terminal(status)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--workspace", required=True, type=Path)
    cli.add_argument("--preflight", required=True, type=Path)
    for flag in ("plan-sha256", "owner-go", "owner-go-usd", "total-go-usd"):
        cli.add_argument("--" + flag, required=True)
    cli.add_argument("--allow-partial", action="store_true")
    cli.add_argument("--confirm-provider-contract", action="store_true")
    live(cli.parse_args())


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (Stop, OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
