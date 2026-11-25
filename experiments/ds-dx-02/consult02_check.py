"""Independent offline comparison. Only this verifier opens the test card."""
import argparse
import json
import os
import sys
from pathlib import Path

from bundle import archive, sums
from consult02 import BASELINE_SHA, CARD_SHA, OFFLINE_DIR, R1_SWEEP_SHA, baseline_path, pins, r1_sweep_path, read_zip
from consult_d import select as select_v1
from protocol import Stop, encode, offline, save, sha
from progress import Progress, reporting
from qa_pins import PINS, QUESTION_SHA256
from selector_v2 import CONTEXT_PROFILES, Selector, WIRE_LIMIT

CARD = Path(__file__).with_name("test_fixtures") / "DS-DX-02-CONSULT-02-SELECTOR-CARD.json"


def match(groups, ids):
    return [dict(need=group["need"], matched=sorted(set(group["any_of"]) & ids)) for group in groups]


def benchmark(entries, rows, card, previous, *, wire_limit=WIRE_LIMIT):
    known = {row["fact_id"] for row in json.loads(entries["index.json"])}
    selector = Selector(entries)
    answers = previous["answers"]
    if len(answers) != len(rows) or any(item["knowledge"] != PINS["identity"] for item in answers):
        raise Stop("Historical answers do not bind original knowledge and frozen series")
    comparisons, baseline_total, v2_total, actual_total, needed = {}, 0, 0, 0, 0
    for position, (row, old) in enumerate(zip(rows, answers, strict=True), 1):
        key = f"Q{position:02}"
        question = row["question"]
        case = card["cases"][key]
        if case["question"] != question or old["question"] != question:
            raise Stop("Historical question or test-card question changed")
        groups = case["required_groups"]
        for group in groups:
            if not group["any_of"] or not set(group["any_of"]) <= known:
                raise Stop("Card includes an unknown original fact ID")
        original = old["selection"]
        old_ids = set(original["fact_ids"])
        if not old_ids <= known:
            raise Stop("Baseline selected IDs differ from the original index")
        historical = match(groups, old_ids)
        v1_body, v1 = select_v1(entries, question, [] if position != 11 else [
            {"question": rows[9]["question"], "answer": "[Синтетическая реплика для dry-run]"}])
        history = [] if position != 11 else [
            {"question": rows[9]["question"], "answer": "[Синтетическая реплика для dry-run]"}]
        _, v2 = selector.select(question, history, wire_limit=wire_limit)
        chosen = match(groups, set(v2["fact_ids"]))
        actual, same_case = None, chosen
        if position == 11:
            _, actual = selector.select(question, [{"question": rows[9]["question"], "answer": answers[9]["text"]}],
                                        wire_limit=wire_limit)
            same_case = match(groups, set(actual["fact_ids"]))
        comparisons[key] = dict(historical_v1=historical, historical_v1_fact_ids=sorted(old_ids),
                                dryrun_v1=dict(fact_ids=v1["fact_ids"], wire_bytes=len(v1_body),
                                               groups=match(groups, set(v1["fact_ids"]))),
                                dryrun_v2=v2, groups_v2=chosen,
                                actual_history_v2=actual, groups_actual_history=same_case,
                                missing_groups=[group["need"] for group in chosen if not group["matched"]],
                                missing_groups_actual_history=[group["need"] for group in same_case if not group["matched"]])
        baseline_total += sum(bool(group["matched"]) for group in historical)
        v2_total += sum(bool(group["matched"]) for group in chosen)
        actual_total += sum(bool(group["matched"]) for group in same_case)
        needed += len(groups)
    if needed != 54:
        raise Stop("Unexpected independent card group count")
    bounds = all(case["dryrun_v2"]["local_bound_ok"] and
                 (case["actual_history_v2"] is None or case["actual_history_v2"]["local_bound_ok"])
                 for case in comparisons.values())
    safety_preserved = all(case["dryrun_v2"]["safety_preserved"] and
                           (case["actual_history_v2"] is None or case["actual_history_v2"]["safety_preserved"])
                           for case in comparisons.values())
    gated = {key: case["dryrun_v2"]["gate"] for key, case in comparisons.items() if case["dryrun_v2"]["gate"]}
    expected_safety = {"Q02", "Q08"}
    safety = all(gated.get(case) == "safety_conflict" and
                 "xt2" in comparisons[case]["dryrun_v2"]["conflict_evidence"] for case in expected_safety)
    unexpected = {key: value for key, value in gated.items() if key not in expected_safety}
    abstention = comparisons["Q12"]["dryrun_v2"]["abstention_guard"]
    passed = (baseline_total == 42 and v2_total == actual_total == needed and bounds and safety and abstention and safety_preserved
              and not unexpected
              and comparisons["Q11"]["actual_history_v2"]["gate"] is None)
    summary = dict(status="PASS" if passed else "FAIL", matched=v2_total, expected=needed,
                   baseline_historical_matched=baseline_total, actual_history_matched=actual_total,
                   local_bounds_pass=bounds, relevant_safety_preserved=safety_preserved, safety_conflict_pass=safety, abstention_guard_pass=abstention,
                   local_deviations=gated, unexpected_local_deviations=unexpected, card_sha256=CARD_SHA, paid_calls=0, provider_usage=None)
    return summary, comparisons


def sufficient_case(key, detail):
    trace = detail["dryrun_v2"]
    if (not trace["local_bound_ok"] or not trace["safety_preserved"] or detail["missing_groups"]):
        return False
    if key in {"Q02", "Q08"}:
        if trace["gate"] != "safety_conflict" or "xt2" not in trace["conflict_evidence"]:
            return False
    elif trace["gate"] is not None:
        return False
    if key == "Q12" and not trace["abstention_guard"]:
        return False
    actual = detail["actual_history_v2"]
    return actual is None or (actual["local_bound_ok"] and actual["safety_preserved"]
                              and actual["gate"] is None and not detail["missing_groups_actual_history"])


def context_sweep(entries, rows, card, previous, *, progress=None):
    profiles, cases, minimum_question = {}, {}, {}
    for profile, wire_limit in CONTEXT_PROFILES.items():
        if progress:
            progress.task, progress.known = profile, len(CONTEXT_PROFILES)
            progress.emit("PROFILE")
        summary, details = benchmark(entries, rows, card, previous, wire_limit=wire_limit)
        profiles[profile] = dict(summary, json_byte_limit=wire_limit)
        cases[profile] = details
        if progress:
            progress.completed += 1
        for key, item in details.items():
            if sufficient_case(key, item):
                minimum_question.setdefault(key, dict(profile=profile, json_byte_limit=wire_limit))
    minimum = next((profile for profile, result in profiles.items() if result["status"] == "PASS"), None)
    questions = tuple(next(iter(cases.values())))
    summary = dict(status="PASS" if minimum else "FAIL",
                   matched=profiles[minimum]["matched"] if minimum else max(p["matched"] for p in profiles.values()),
                   expected=54, minimum_series_profile=minimum,
                   minimum_series_json_bytes=CONTEXT_PROFILES[minimum] if minimum else None,
                   minimum_by_question={key: minimum_question.get(key) for key in questions},
                   profiles=profiles, card_sha256=CARD_SHA, paid_calls=0, provider_usage=None)
    return summary, cases


def compare_r1(summary, cases, r1):
    baseline = json.loads(r1["summary.json"])
    old_cases = json.loads(r1["cases.json"])
    comparison = {}
    for profile, limit in CONTEXT_PROFILES.items():
        old, new = baseline["profiles"][profile], summary["profiles"][profile]
        if old["json_byte_limit"] != limit or old["card_sha256"] != CARD_SHA:
            raise Stop("R1 profile does not match the independent Context Sweep contract")
        before = old_cases[profile]
        after = cases[profile]
        rows = {}
        for key, detail in after.items():
            old_case = before[key]
            old_missing = set(old_case["missing_groups"])
            new_missing = set(detail["missing_groups"])
            rows[key] = dict(recovered=sorted(old_missing - new_missing),
                             newly_missing=sorted(new_missing - old_missing),
                             prior_gate=old_case["dryrun_v2"]["gate"],
                             current_gate=detail["dryrun_v2"]["gate"])
        comparison[profile] = dict(r1_status=old["status"], r2_status=new["status"],
                                  r1_matched=old["matched"], r2_matched=new["matched"],
                                  delta=new["matched"] - old["matched"], cases=rows,
                                  r1_q11_actual_history=sum(bool(g["matched"]) for g in before["Q11"]["groups_actual_history"]),
                                  r2_q11_actual_history=sum(bool(g["matched"]) for g in after["Q11"]["groups_actual_history"]))
    return comparison


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--workspace", required=True, type=Path)
    cli.add_argument("--preflight", required=True, type=Path)
    args = cli.parse_args()
    os.umask(0o077)
    offline(stream=sys.stderr)
    workspace = args.workspace.resolve(strict=True)
    plan, entries, _, rows = pins(workspace, args.preflight)
    raw = CARD.read_bytes()
    if sha(raw) != CARD_SHA:
        raise Stop("Test-only selector card fingerprint differs")
    card = json.loads(raw)
    if any(card.get(key) != value for key, value in dict(
            knowledge_identity=PINS["identity"], knowledge_zip_sha256=PINS["knowledge"],
            baseline_results_zip_sha256=BASELINE_SHA, questions_sha256=QUESTION_SHA256).items()):
        raise Stop("Test-only selector card is for another release")
    previous = json.loads(read_zip(baseline_path(workspace), BASELINE_SHA)["consult.json"])
    output = workspace / OFFLINE_DIR
    if output.is_symlink() or (output / "plan.json").exists():
        raise Stop("Use fresh offline acceptance output")
    preflight_zip = args.preflight.with_name("DS-DX-02-D-preflight.zip")
    tests = read_zip(preflight_zip, sha(preflight_zip.read_bytes()))
    if tests["preflight.json"] != args.preflight.read_bytes():
        raise Stop("Preflight report differs from its archive")
    path = output / "consult02-context-sweep.zip"
    progress = Progress("CONSULT-02-R2-SWEEP", path)
    with reporting(progress):
        summary, details = context_sweep(entries, rows, card, previous, progress=progress)
        comparison = compare_r1(summary, details, read_zip(r1_sweep_path(workspace), R1_SWEEP_SHA))
        summary["r1_sweep_sha256"] = R1_SWEEP_SHA
        summary["r1_coverage"] = {key: row["r1_matched"] for key, row in comparison.items()}
    package = {"summary.json": encode(summary), "cases.json": encode(details),
               "plan-pins.json": encode(plan), "r1-comparison.json": encode(comparison), "tests.txt": tests["tests.txt"]}
    package["SHA256SUMS"] = sums(package)
    archive(path, package)
    if summary["status"] == "PASS":
        profile = summary["minimum_series_profile"]
        save(output / "plan.json", dict(pins=plan, selected_profile=profile,
                                       local_wire_bytes=CONTEXT_PROFILES[profile], report_zip_sha256=sha(path.read_bytes()),
                                       summary_sha256=sha(package["summary.json"])))
        summary["plan_sha256"] = sha((output / "plan.json").read_bytes())
    print(encode(summary).decode())
    progress.terminal("COMPLETE_UNREVIEWED" if summary["status"] == "PASS" else "STOP")
    if summary["status"] != "PASS":
        raise Stop("Offline selector acceptance failed; inspect consult02-context-sweep.zip")


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
