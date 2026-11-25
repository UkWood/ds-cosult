"""Independent offline comparison. Only this verifier opens the test card."""
import argparse
import json
import os
import sys
from pathlib import Path

from bundle import archive, sums
from consult02 import BASELINE_SHA, CARD_SHA, baseline_path, pins, read_zip
from consult_d import select as select_v1
from protocol import Stop, encode, offline, save, sha
from qa_pins import PINS, QUESTION_SHA256
from selector_v2 import Selector

CARD = Path(__file__).with_name("test_fixtures") / "DS-DX-02-CONSULT-02-SELECTOR-CARD.json"


def match(groups, ids):
    return [dict(need=group["need"], matched=sorted(set(group["any_of"]) & ids)) for group in groups]


def benchmark(entries, rows, card, previous):
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
        _, v2 = selector.select(question, history)
        chosen = match(groups, set(v2["fact_ids"]))
        actual, same_case = None, chosen
        if position == 11:
            _, actual = selector.select(question, [{"question": rows[9]["question"], "answer": answers[9]["text"]}])
            same_case = match(groups, set(actual["fact_ids"]))
        comparisons[key] = dict(historical_v1=historical, historical_v1_fact_ids=sorted(old_ids),
                                dryrun_v1=dict(fact_ids=v1["fact_ids"], wire_bytes=len(v1_body),
                                               groups=match(groups, set(v1["fact_ids"]))),
                                dryrun_v2=v2, groups_v2=chosen,
                                actual_history_v2=actual, groups_actual_history=same_case)
        baseline_total += sum(bool(group["matched"]) for group in historical)
        v2_total += sum(bool(group["matched"]) for group in chosen)
        actual_total += sum(bool(group["matched"]) for group in same_case)
        needed += len(groups)
    if needed != 54:
        raise Stop("Unexpected independent card group count")
    bounds = all(case["dryrun_v2"]["local_bound_ok"] and
                 (case["actual_history_v2"] is None or case["actual_history_v2"]["local_bound_ok"])
                 for case in comparisons.values())
    gated = {key: case["dryrun_v2"]["gate"] for key, case in comparisons.items() if case["dryrun_v2"]["gate"]}
    safety = all(gated.get(case) == "safety_conflict" for case in ("Q02", "Q08"))
    abstention = comparisons["Q12"]["dryrun_v2"]["abstention_guard"]
    passed = (baseline_total == 42 and v2_total == actual_total == needed and bounds and safety and abstention
              and all(gate == "safety_conflict" for gate in gated.values())
              and comparisons["Q11"]["actual_history_v2"]["gate"] is None)
    summary = dict(status="PASS" if passed else "FAIL", matched=v2_total, expected=needed,
                   baseline_historical_matched=baseline_total, actual_history_matched=actual_total,
                   local_bounds_pass=bounds, safety_conflict_pass=safety, abstention_guard_pass=abstention,
                   local_deviations=gated, card_sha256=CARD_SHA, paid_calls=0, provider_usage=None)
    return summary, comparisons


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
    summary, details = benchmark(entries, rows, card, previous)
    output = workspace / "consult02-offline"
    if output.is_symlink() or (output / "plan.json").exists():
        raise Stop("Use fresh offline acceptance output")
    preflight_zip = args.preflight.with_name("DS-DX-02-D-preflight.zip")
    tests = read_zip(preflight_zip, sha(preflight_zip.read_bytes()))
    if tests["preflight.json"] != args.preflight.read_bytes():
        raise Stop("Preflight report differs from its archive")
    package = {"summary.json": encode(summary), "cases.json": encode(details),
               "plan-pins.json": encode(plan), "tests.txt": tests["tests.txt"]}
    package["SHA256SUMS"] = sums(package)
    path = output / "consult02-dryrun.zip"
    archive(path, package)
    if summary["status"] == "PASS":
        save(output / "plan.json", dict(pins=plan, report_zip_sha256=sha(path.read_bytes()),
                                       summary_sha256=sha(package["summary.json"])))
        summary["plan_sha256"] = sha((output / "plan.json").read_bytes())
    print(encode(summary).decode())
    if summary["status"] != "PASS":
        raise Stop("Offline selector acceptance failed; inspect consult02-dryrun.zip")


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
