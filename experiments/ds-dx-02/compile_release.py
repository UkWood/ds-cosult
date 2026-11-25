"""Offline preparation and owner approval pins for the final D compiler."""
import argparse
import json
import os
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from bundle import sums
from protocol import Stop, encode, kernel_release, load, offline, runtime_digest, save, sha
from r4_a import finances, score
from r4_c import CASES, original
from reconcile import summarize
from sources import verify

MODES = dict.fromkeys(("extract", "vision_photo", "vision_document", "fusion"), "disabled")
TRANSPORT = {"stream": True, "stream_options": {"include_usage": True}}
CARD_REVISION = "R4-A-ENGINEERING-01"


def pinned_json(path):
    raw = path.read_bytes()
    return json.loads(raw), sha(raw)


def engineering(workspace, card_path, snapshot):
    frozen_path = workspace / "r4-a-plan/manifest-frozen.json"
    _, frozen_sha = pinned_json(frozen_path)
    experiment, card_sha = original(workspace, card_path, frozen_sha)
    card, digest = pinned_json(card_path)
    if digest != card_sha or card["revision"] != CARD_REVISION or experiment["snapshot"] != snapshot:
        raise Stop("Full COMPILE requires the original frozen R4-A-ENGINEERING-01 card and snapshot")
    reports = {}
    for name, cases in (("r4-a", ("A-D", "A-L")), ("r4-c", CASES)):
        private = workspace / f"private-{name}"
        go, go_sha = pinned_json(private / "owner-go.json")
        ledger, ledger_sha = pinned_json(private / "ledger.json")
        if (go["manifest_sha256" if name == "r4-a" else "frozen_sha256"] != frozen_sha
                or ledger["stages"][name]["identity"] != go["identity"]):
            raise Stop("Engineering report does not bind its experiment Owner GO")
        continuation_sha = None
        if name == "r4-c":
            if go["card_sha256"] != card_sha:
                raise Stop("R4-C was evaluated against a different card")
            candidates = [path for path in workspace.glob("r4-c-plan-*.json")
                          if sha(path.read_bytes()) == go["plan_sha256"]]
            if len(candidates) != 1:
                raise Stop("Original approved R4-C plan is missing or changed")
            continuation, continuation_sha = pinned_json(candidates[0])
            if (continuation_sha != go["plan_sha256"] or continuation["card_sha256"] != card_sha
                    or continuation["frozen_sha256"] != frozen_sha or continuation["streaming"] is not True
                    or continuation["experiment"]["snapshot"] != snapshot
                    or continuation["experiment"]["cases"] != experiment["cases"][2:]):
                raise Stop("R4-C continuation does not match the frozen P/V matrix")

        report = workspace / f"reports-{name}/{name}-summary.zip"
        raw = report.read_bytes()
        summary_sha = sha(raw)
        if report.with_suffix(".zip.sha256").read_text().split() != [summary_sha, report.name]:
            raise Stop("Original experiment summary checksum mismatch")
        with ZipFile(BytesIO(raw)) as package:
            content = package.read("summary.json")
            if package.read("SHA256SUMS") != sums({"summary.json": content}):
                raise Stop("Original experiment summary contents changed")
        summary = json.loads(content)
        observed = {id_ for id_, row in summary["cases"].items() if "accepted" in row}
        settled = {op["id"]: op for op in ledger["ops"] if op["stage"] == name and op["status"] == "SETTLED"}
        if summary["execution"] != "live" or summary["snapshot"] != snapshot or observed != set(cases):
            raise Stop("Wrong engineering experiment or incomplete cases")
        for id_ in cases:
            op = settled[id_]
            checkpoint, checkpoint_sha = pinned_json(private / name / (id_ + ".json"))
            row = summary["cases"][id_]
            mode = next(case["mode"] for case in experiment["cases"] if case["id"] == id_)
            params = op["parameters"]
            requested = ("disabled" if params["thinking"]["type"] == "disabled"
                         and "reasoning_effort" not in params else params.get("reasoning_effort")
                         if params["thinking"]["type"] == "enabled" else None)
            if (requested != mode or checkpoint_sha != op["result_sha256"] or row["usage"] != checkpoint["usage"]
                    or row["peak_nd"] != checkpoint["cost_nd"] or row["mode"] != mode
                    or name == "r4-c" and any(params.get(key) != value for key, value in TRANSPORT.items())):
                raise Stop("Experiment summary disagrees with a settled case checkpoint")
        value, score_sha = pinned_json(private / "engineering/score.json")
        if score(card, value["cases"], summary) != value:
            raise Stop("Engineering score differs from the official evaluator or frozen card")
        reports[name] = dict(score_sha256=score_sha, summary_sha256=summary_sha, owner_go_sha256=go_sha,
                             ledger_sha256=ledger_sha, continuation_sha256=continuation_sha)
    return dict(card_sha256=card_sha, frozen_sha256=frozen_sha, revision=CARD_REVISION, reports=reports)


def release_plan(workspace, sources, card, preflight):
    try:
        snapshot = verify(sources, reparse=False)
        runtime, kernel = runtime_digest(), kernel_release()
        evidence, preflight_sha = pinned_json(preflight)
        if any(evidence.get(key) != value for key, value in dict(
                snapshot=snapshot, runtime=runtime, kernel=kernel, paid_calls=0,
                offline="seccomp: socket EPERM", package_count=3, r4_b_int=True).items()):
            raise Stop("Run the full INT offline preflight on this WSL host")
        review = engineering(workspace, card, snapshot)
        finance = finances(workspace, include_r4_a=True, include_r4_c=True)
        for name in ("r2", "r3", "r4-a", "r4-c"):
            root = {"r2": "private-state", "r3": "private-r3"}.get(name, "private-" + name)
            history = summarize(workspace / root / "ledger.json")
            if (history["ledger_sha256"] != finance[name.replace("-", "_") + "_sha256"]
                    or any(op["status"] == "SETTLED" and op["checkpoint"] != "verified"
                           for op in history["operations"])):
                raise Stop("Prior financial ledger or settled checkpoint failed verification")
            if name in review["reports"] and history["ledger_sha256"] != review["reports"][name]["ledger_sha256"]:
                raise Stop("Engineering and financial evidence disagree")
        return dict(schema=1, modes=MODES, transport=TRANSPORT, snapshot=snapshot, runtime=runtime,
                    kernel=kernel, preflight_sha256=preflight_sha, engineering=review, finance=finance,
                    state=str(workspace / "private-r4-b"))
    except (OSError, KeyError, TypeError, ValueError, IndexError, BadZipFile) as error:
        raise Stop("Required local approval evidence is missing or malformed (" + type(error).__name__ + ")") from None


def approved_plan(path, digest, *inputs):
    saved, actual = pinned_json(path)
    if actual != digest or saved != release_plan(*inputs):
        raise Stop("Approved compile plan or pinned evidence has changed")
    return saved


def main():
    cli = argparse.ArgumentParser()
    for arg in ("workspace", "sources", "card", "preflight", "output"):
        cli.add_argument("--" + arg, type=Path, required=True)
    args = cli.parse_args()
    os.umask(0o077)
    offline()
    workspace = args.workspace.resolve(strict=True)
    if args.output.resolve().parent != workspace or args.output.exists() or args.output.is_symlink():
        raise Stop("Write the plan to a fresh file at the workspace root")
    plan = release_plan(workspace, args.sources, args.card, args.preflight)
    save(args.output, plan)
    print(encode(plan["finance"]).decode())
    print("Approved-plan SHA256 " + sha(args.output.read_bytes()))


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
