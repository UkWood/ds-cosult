"""Read-only forensic replay of the pinned R4-B knowledge release."""
import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from bundle import FORBIDDEN, archive, sums, verify_zip
from compile_d import compile_snapshot, fact_issue, locator_issue
from progress import Progress, reporting
from protocol import Ledger, Stop, encode, load, offline, sha
from sources import verify

from qa_pins import PINS

FIELDS = ("text", "applicability", "kind", "locators", "critical", "topic")
OBSERVED = {"locator_format": 192, "fusion_kind": 49, "row_text": 45,
            "locator_outside_evidence": 38, "missing_image_locator": 3}


def pinned(path, expected):
    if path.is_symlink() or sha(path.read_bytes()) != expected:
        raise Stop(f"Pinned artifact differs: {path.name}")


def evidence(path):
    with ZipFile(path) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    checksums = entries.pop("SHA256SUMS", None)
    if checksums != sums(entries):
        raise Stop("Archive internal checksum mismatch")
    return entries


def redacted(value):
    if isinstance(value, str):
        # Preserve ordinary reviewable records; never export recognizable handles or tokens.
        raw = value.encode(errors="backslashreplace")
        if FORBIDDEN.search(raw) or re.search(rb"(?i)\bBearer[ \t]+\S+", raw):
            return "[redacted: forbidden material]"
        return raw.decode()
    if isinstance(value, list):
        return [redacted(item) for item in value]
    if isinstance(value, dict):
        return {redacted(k): redacted(v) for k, v in value.items()}
    return value


def review_row(task, ordinal, row, first, checkpoint_sha, family):
    violations = {first}
    proposed = None
    patterns = Counter()
    if isinstance(row, dict):
        expected = {"text", "applicability", "kind", "locators"}
        if not expected <= row.keys() or row.keys() - set(FIELDS) or type(row.get("critical", False)) is not bool:
            violations.add("row_shape")
        if not all(isinstance(row.get(name), str) and 0 < len(row[name].strip()) <= 4000
                   for name in ("text", "applicability")):
            violations.add("row_text")
        if row.get("kind") not in ("source_assertion", "visual_observation", "bounded_inference", "unresolved"):
            violations.add("row_kind")
        if task["kind"] == "fusion" and row.get("kind") != "unresolved":
            violations.add("fusion_kind")
        locators = row.get("locators")
        if not isinstance(locators, list) or not locators:
            violations.add("missing_locators")
        else:
            normalized = []
            for loc in locators:
                issue = locator_issue(loc, task)
                if issue:
                    violations.add(issue)
                if not isinstance(loc, str):
                    patterns[type(loc).__name__] += 1
                    normalized.append(loc)
                    continue
                key, sep, value = loc.partition(":")
                patterns["image" if key == "I" else "source" if sep else "unstructured"] += 1
                match = re.fullmatch(r"\s*([A-Za-z0-9-]+)\s*:\s*([0-9]{1,8})\s*", loc)
                candidate = f"{match[1]}:{int(match[2])}" if match else loc
                normalized.append(candidate if locator_issue(candidate, task) is None else loc)
            if row.get("kind") == "visual_observation" and not any(
                    isinstance(loc, str) and loc.startswith("I:") for loc in locators):
                violations.add("missing_image_locator")
            candidate = dict(row, locators=normalized)
            if (normalized != locators and violations <= {"locator_format", "locator_outside_evidence"}
                    and fact_issue(candidate, task) is None):
                proposed = {key: candidate[key] for key in FIELDS if key in candidate}
        from bundle import checked_bytes
        try:
            checked_bytes("ESSENCE.md", encode(row))
        except (Stop, UnicodeError, ValueError):
            violations.add("disallowed_content")
    substantive = {"locator_outside_evidence", "fusion_kind", "image_outside_evidence", "missing_image_locator"}
    classification = ("unambiguous_normalization" if proposed is not None else
                      "substantive_violation" if violations & substantive else
                      "ambiguous" if "locator_format" in violations else "engineering_review")
    raw = {key: row[key] for key in FIELDS if key in row} if isinstance(row, dict) else row
    return dict(task=task["id"], family=family, checkpoint_sha256=checkpoint_sha, ordinal=ordinal,
                first_code=first, violations=sorted(violations), classification=classification,
                raw=redacted(raw), proposed=redacted(proposed), locator_types=patterns,
                scope=task["scope"], images=task["images"], supporting_images=task.get("supporting_images", []),
                supporting_locators=task.get("supporting_locators", []))


class ReplayLedger:
    """Read adapter with no execute path and exact historical request ordering."""
    def __init__(self, path, website):
        data = load(path)
        stage = data["stages"]["compile"]
        self.ledger = Ledger(path, "compile", stage["cap"], data["total"], stage["identity"], resume=True)
        self.path, self.cap, self.total, self.data = path, stage["cap"], data["total"], self.ledger.data
        self.ops = {op["id"]: op for op in self.data["ops"]}
        self.website = website
        self.position = 0
        self.leases = {}
        self.rejected = []

    def settled(self, id_):
        return self.ledger.settled(id_)

    def has(self, id_):
        return self.ledger.has(id_)

    def result(self, id_):
        return self.ledger.result(id_)

    def execute(self, *_args, **_kwargs):
        raise Stop("Replay attempted an operation missing from the historical ledger")

    def checkpoint_request(self, id_, body, prefix):
        ops = self.data["ops"]
        if self.position >= len(ops) or ops[self.position]["id"] != id_:
            raise Stop("Replay operation order differs from historical ledger")
        self.ledger.checkpoint_request(id_, body, prefix)
        self.position += 1
        diag = load(self.path.parent / "diagnostics/compile" / (id_ + ".json"))
        if id_.startswith("upload-"):
            value = self.result(id_)
            done = datetime.fromisoformat(diag["ended_utc"])
            if done.utcoffset() is None:
                raise Stop("Historical upload timestamp lacks a timezone")
            self.leases[value["handle"]] = (done.timestamp(), value["expires_at"])
        else:
            wire = json.loads(body)
            for block in wire["messages"][1]["content"]:
                if block["type"] != "file":
                    continue
                when = datetime.fromisoformat(diag["started_utc"])
                start, end = self.leases[block["file_id"]]
                if when.utcoffset() is None or not start <= when.timestamp() < end:
                    raise Stop("Historical use of PDF lease is outside its verified interval")

    def reject(self, task, ordinal, row, code):
        family = task["kind"]
        if family == "vision":
            source, = task["scope"]
            family = "vision_photo" if self.website["records"][source]["kind"] == "image" else "vision_document"
        self.rejected.append(review_row(task, ordinal, row, code, self.ops[task["id"]]["result_sha256"], family))


def replay(workspace, output, progress):
    root = workspace / "source-pilot"
    state = workspace / "private-r4-b"
    reports = workspace / "compile-r4-b-v1"
    knowledge, compile_zip = reports / "knowledge.zip", reports / "DS-DX-02A-results.zip"
    ledger, plan_path = state / "ledger.json", workspace / "r4-b-int-plan.json"
    for path, key in ((knowledge, "knowledge"), (compile_zip, "compile"), (ledger, "ledger"), (plan_path, "plan")):
        pinned(path, PINS[key])
    meta = verify_zip(knowledge)
    if meta["identity"] != PINS["identity"] or meta["snapshot"] != PINS["snapshot"] or verify(root) != PINS["snapshot"]:
        raise Stop("Knowledge identity or SourceArchive fingerprint differs")
    plan = load(plan_path)
    journal = ReplayLedger(ledger, load(root / "source-manifest.json"))
    if len(journal.ops) != 98:
        raise Stop("Expected 98 verified settled operations")
    with TemporaryDirectory(prefix="dx02-review-") as name:
        tmp = Path(name)
        status = compile_snapshot(root, tmp / "knowledge", tmp / "reports", journal, meta["snapshot"], None,
                                  execution="live", policy=plan["modes"], progress=progress, replay=journal)
        if (journal.position != len(journal.ops)
                or evidence(tmp / "reports/knowledge.zip") != evidence(knowledge)
                or evidence(tmp / "reports/DS-DX-02A-results.zip") != evidence(compile_zip)):
            raise Stop("Replayed KnowledgeBase or compilation report differs from the original")
    coverage = json.loads(evidence(knowledge)["coverage.json"])
    observed = Counter(item["first_code"] for item in journal.rejected)
    reasons = {reason: [task for task, issue in coverage["extraction_issues"].items()
                        if issue["reason"] == reason]
               for reason in ("unconfirmed_images", "truncated", "invalid_json")}
    summary = dict(status=status, paid_calls=0, checkpoint_ops=journal.position, pins=PINS,
                   accepted_count=len(json.loads(evidence(knowledge)["index.json"])),
                   task_count=len(coverage["tasks"]), first_codes=observed, reference_first_codes=OBSERVED,
                   matches_reference=observed == OBSERVED,
                   task_reasons=reasons, family=Counter(row["family"] for row in journal.rejected),
                   classification=Counter(row["classification"] for row in journal.rejected),
                   locator_types=sum((Counter(row["locator_types"]) for row in journal.rejected), Counter()))
    examples = []
    for code in sorted(observed):
        example = next(row for row in journal.rejected if row["first_code"] == code)
        examples.append({key: example[key] for key in ("task", "ordinal", "first_code", "classification",
                                                       "raw", "proposed")})
    recommendations = []
    if summary["classification"]["unambiguous_normalization"]:
        recommendations.append("Review only exact in-scope syntax proposals independently; retain all original rows.")
    if observed["fusion_kind"]:
        recommendations.append("Inspect Fusion output against its actual supporting records; preserve unresolved semantics.")
    if reasons["unconfirmed_images"]:
        recommendations.append("Review named image candidates with the available visual facts; do not infer missing links.")
    if reasons["truncated"] or reasons["invalid_json"]:
        recommendations.append("Review surviving complete records only; keep invalid or incomplete payloads out of the knowledge.")
    entries = {"summary.json": encode(summary), "rejected.json": encode(journal.rejected),
               "examples.json": encode(examples), "recommendations.json": encode(recommendations)}
    entries["SHA256SUMS"] = sums(entries)
    archive(output, entries)
    return status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    offline(stream=sys.stderr)
    workspace = args.workspace.resolve(strict=True)
    if (args.output.resolve().parent != workspace / "qa-r4-b" or args.output.exists()
            or args.output.is_symlink() or args.output.with_suffix(".zip.sha256").exists()):
        raise Stop("Write the QA review in the separate qa-r4-b directory")
    progress = Progress("QA_REPLAY", args.output)
    with reporting(progress):
        status = replay(workspace, args.output, progress)
    progress.terminal(status)
    print(encode(dict(status=status, review_zip=args.output.name)).decode())


if __name__ == "__main__":
    try:
        main()
    except Stop as error:
        raise SystemExit(str(error)) from None
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit("Exact replay evidence unavailable (" + type(error).__name__ + ")") from None
