"""Run the pinned DC-05A offline WSL acceptance and write one verified report."""
import argparse
from collections import Counter
from hashlib import sha1, sha256
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from xml.etree import ElementTree
import zipfile


TASK = "DS-DC-05A"
R1_COMMIT = "9f9bb5b489c71daaae309a60d4be6535ce7e64e9"
START = "c8e0ed0e1122e3a17781c4a5497bbc4c8830d38b"
BASELINE = "2dac638843b1ce4ac7506de8fb3e3bb222d2199d"
R1_LAUNCHER_BLOB = "5e328e699820e02941667bae2a4530da45bbf032"
R1_ARCHIVE = "dc04b-r1-ri2rhny_.zip"
R1_ARCHIVE_SHA = "31f7c098c74020002312b647ad38e726a63f780686bb35eb73c9ced2ba00106f"
CANDIDATE = "5fbae4db9a008331e1f1f1314144856b120a65901172f7d48199b38389018c7c"
REMOTE = "https://github.com/UkWood/ds-cosult.git"
REF = "refs/heads/feat/ds-dc-01-document-centric-pilot"
LAUNCHER = "scripts/validation/validate_dc05a.py"
OWNER_LAUNCHER = "scripts/validation/launch_dc05a.py"
PREVIOUS_LAUNCHER = "scripts/validation/validate_dc04b_r1.py"
HANDOFF = "docs/handoffs/DS-DC-05A-HANDOFF.md"
CR01_HANDOFF = "docs/handoffs/DS-DC-05A-CR01-HANDOFF.md"
FINAL_HANDOFF = "docs/handoffs/DS-DC-05A-CR01-FINAL-HANDOFF.md"
REPORT_BASE = "05a6096c58804598087a3ef3ce394b7aaf00c9c4"
WORKSPACE_FD = "DC05A_WORKSPACE_FD"
RUNBOOK = "docs/runbooks/DS-DC-05A-OWNER-TRIAL.md"
ARCHITECTURE = "docs/architecture/A-DS-DC-12-OWNER-DRIVEN-PRACTICAL-EVALUATION.md"
SMOKE_NODE = "tests/test_dc05a_pipeline.py::test_acceptance_smoke"
GUARD = "scripts/validation/dc03c-offline"
PARENT_NS = "DC04B_R1_PARENT_NETNS"
OUTPUT = Path("/mnt/c/DS-Validation/Reports")
PIN = re.compile(r"[0-9a-f]{40}")
SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,79}")
TEST_NAME = re.compile(r"test_[a-z0-9_]{1,110}")
TARGETS = frozenset({"pipeline", "web", "native", "start", "launcher"})
SOURCE_LEAK = re.compile(rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----|\bsk-[a-zA-Z0-9]{32,}\b")
REDACTED_FIELDS = {"api_key", "authorization", "cookie", "csrf", "file_id", "handle", "headers", "ledger",
                   "native_response", "raw", "raw_response", "reasoning", "reasoning_content"}
NEW_SOURCE = re.compile(r"ds_dc/trial[a-z0-9_]*\.(?:py|js|css|html)")
NEW_TEST = re.compile(r"tests/test_dc05a_[a-z0-9_]+\.py")
R1_MEMBERS = ("summary.json", "checks.json", "ab-before-after.json", "integrity.json", "report.md", "SHA256SUMS")
MEMBERS = ("summary.json", "checks.json", "integrity.json", "ui-pipeline-feedback.json", "report.md", "SHA256SUMS")
CRITERIA = tuple(f"05A-{index:02}" for index in range(1, 9))
R1_TESTS = 428
PROJECTED_REPLAY = ("A", "B_before", "B_after", "verification_before", "verification_after", "grades")
PAYLOAD_ERRORS = (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError,
                  ElementTree.ParseError, zipfile.BadZipFile, RuntimeError)
EXIT = {"PASS": 0, "FAIL": 1, "BLOCKED": 2}


class Blocked(ValueError):
    """An independent acceptance prerequisite could not be established."""


class Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise Blocked("invalid_arguments")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def evidence_status(status, code=None, **details):
    return {"status": status, "failure_code": code, **details}


def gate(*statuses):
    if "FAIL" in statuses:
        return "FAIL"
    return "BLOCKED" if "BLOCKED" in statuses else "PASS"


def attempt(check, failure_code):
    try:
        return evidence_status("PASS", **(check() or {}))
    except (Blocked, FileNotFoundError) as error:
        code = str(error)
        return evidence_status("BLOCKED", code if SAFE_CODE.fullmatch(code) else failure_code)
    except PAYLOAD_ERRORS as error:
        code = str(error)
        return evidence_status("FAIL", code if isinstance(error, ValueError)
                               and SAFE_CODE.fullmatch(code) else failure_code)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def read_object(path, limit=1 << 20):
    require(path.is_file() and not path.is_symlink(), "evidence_file_missing")
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    require(len(raw) <= limit, "evidence_file_oversize")
    value = json.loads(raw)
    require(isinstance(value, dict), "evidence_object_invalid")
    return value


def git_environment(*, online=False):
    return {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
            "GIT_ALLOW_PROTOCOL": "https" if online else ""}


def git(tree, *args, online=False):
    return subprocess.check_output(
        ["git", "-C", str(tree), "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
         "-c", "credential.helper=", *args],
        env=git_environment(online=online), stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180,
    )


def git_text(tree, *args):
    return git(tree, *args).decode("ascii").strip()


def blob_id(path):
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def validate_scope(raw):
    require(raw.endswith(b"\0"), "scope_malformed")
    fields = raw[:-1].decode("ascii").split("\0")
    require(len(fields) % 2 == 0, "scope_malformed")
    changes = {}
    for header, filename in zip(fields[::2], fields[1::2]):
        require(filename not in changes and (
            filename in {LAUNCHER, OWNER_LAUNCHER, HANDOFF, CR01_HANDOFF, FINAL_HANDOFF, RUNBOOK, ARCHITECTURE, "ds_dc/evidence_integration.py"}
            or NEW_SOURCE.fullmatch(filename) or NEW_TEST.fullmatch(filename)
        ), "scope_path_forbidden")
        expected = (":100644", "100644", "M") if filename == "ds_dc/evidence_integration.py" else (
            ":000000", "100644", "A")
        parts = header.split()
        require(len(parts) == 5 and (parts[0], parts[1], parts[4]) == expected, "scope_change_forbidden")
        changes[filename] = parts[4]
    return changes


def verify_checkout(args, checkout, baseline):
    for pin, tree in ((args.commit, checkout), (BASELINE, baseline)):
        require(git_text(tree, "rev-parse", "HEAD") == pin, "checkout_pin_mismatch")
        require(not git(tree, "status", "--porcelain", "--untracked-files=all"), "checkout_dirty")
    require(git_text(checkout, "rev-parse", f"HEAD:{LAUNCHER}") == args.blob
            and blob_id(checkout / LAUNCHER) == args.blob, "launcher_blob_mismatch")
    require(git_text(checkout, "rev-parse", f"{R1_COMMIT}:{PREVIOUS_LAUNCHER}") == R1_LAUNCHER_BLOB
            and blob_id(checkout / PREVIOUS_LAUNCHER) == R1_LAUNCHER_BLOB, "historical_launcher_changed")
    require(git_text(checkout, "merge-base", R1_COMMIT, START) == R1_COMMIT
            and args.commit != START and git_text(checkout, "merge-base", START, args.commit) == START,
            "checkout_ancestry_mismatch")
    require(git_text(checkout, "merge-base", args.commit, "FETCH_HEAD") == args.commit,
            "commit_not_in_draft_branch")
    require(not git(checkout, "rev-list", "--merges", f"{START}..{args.commit}"), "merge_in_acceptance_scope")
    changes = validate_scope(git(checkout, "diff", "--raw", "--no-renames", "--no-ext-diff", "-z", START, args.commit))
    required = {LAUNCHER, OWNER_LAUNCHER, *(f"tests/test_dc05a_{key}.py" for key in TARGETS)}
    require(required <= changes.keys(), "scope_required_artifacts_missing")
    require(not any(SOURCE_LEAK.search((checkout / name).read_bytes()) for name in changes),
            "scope_forbidden_secret_pattern")
    return changes


def verify_handoff(args, checkout, scope):
    require({ARCHITECTURE, RUNBOOK} <= scope.keys(), "trial_runbook_or_architecture_missing")
    raw = git(checkout, "diff", "--raw", "--no-renames", "--no-ext-diff", "-z", args.commit, "FETCH_HEAD")
    require(raw and validate_scope(raw) == {FINAL_HANDOFF: "A"}, "handoff_descendant_missing")
    require(git_text(checkout, "merge-base", REPORT_BASE, args.commit) == REPORT_BASE
            and set(git_text(checkout, "diff", "--name-only", REPORT_BASE, args.commit).splitlines())
                == {LAUNCHER, "tests/test_dc05a_launcher.py"},
            "cr01_scope_mismatch")
    handoff = git(checkout, "show", f"FETCH_HEAD:{FINAL_HANDOFF}")
    require(args.commit.encode() in handoff and args.blob.encode() in handoff, "handoff_launch_pins_missing")
    require(not SOURCE_LEAK.search(handoff), "handoff_forbidden_secret_pattern")
    return {"commit": git_text(checkout, "rev-parse", "FETCH_HEAD"), "runbook_present": True,
            "architecture_decision_present": True}


def prepare_checkouts(args, work):
    checkout, baseline = work / "trial", work / "baseline"
    checkout.mkdir()
    try:
        git(checkout, "init", "--quiet", "--template=")
        git(checkout, "fetch", "--quiet", "--no-tags", "--no-recurse-submodules", REMOTE, REF, online=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise Blocked("draft_checkout_fetch_failed") from error
    git(checkout, "checkout", "--quiet", "--detach", args.commit)
    git(checkout, "worktree", "add", "--quiet", "--detach", str(baseline), BASELINE)
    return checkout, baseline


def load_module(path):
    spec = importlib.util.spec_from_file_location("accepted_r1_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_members(path, members):
    with zipfile.ZipFile(path) as archive:
        require(tuple(archive.namelist()) == members and archive.testzip() is None, "zip_crc_or_members")
        contents = {name: archive.read(name) for name in members[:-1]}
        expected = "".join(f"{sha256(raw).hexdigest()}  {name}\n" for name, raw in contents.items())
        require(archive.read("SHA256SUMS").decode("ascii") == expected, "zip_member_sha_mismatch")
    return contents


def archive_path(args):
    if args.r1_report:
        return args.r1_report
    candidates = (OUTPUT / R1_ARCHIVE, args.wsl_root / R1_ARCHIVE, Path.cwd() / R1_ARCHIVE,
                  args.wsl_root.parent / R1_ARCHIVE)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise Blocked("accepted_r1_archive_missing")


def verify_r1_archive(path):
    with path.open("rb") as source:
        raw = source.read((2 << 20) + 1)
    require(sha256(raw).hexdigest() == R1_ARCHIVE_SHA, "r1_archive_digest_mismatch")
    contents = verify_members(BytesIO(raw), R1_MEMBERS)
    summary = json.loads(contents["summary.json"])
    checks = json.loads(contents["checks.json"])
    integrity = json.loads(contents["integrity.json"])
    replay = json.loads(contents["ab-before-after.json"])
    regression = checks["prior_acceptance"]["full_regression"]
    counts = Counter(case["test"] for case in regression["cases"] if case["status"] == "PASS")
    require(summary["status"] == "PASS" and summary["pin"] == R1_COMMIT
            and summary["launcher_blob"] == R1_LAUNCHER_BLOB
            and summary["new_provider_operations"] == summary["new_cost_micro_usd"] == 0
            and checks["criteria"] == {f"R1-{index:02}": "PASS" for index in range(1, 11)}
            and regression["tests"] == sum(counts.values()) == R1_TESTS
            and not any(regression[key] for key in ("failures", "errors", "skipped"))
            and integrity["replay"]["private_history_immutable"] is True
            and replay["A"]["candidate_sha256"] == CANDIDATE
            and replay["grades"]["published_pairs"] == 2, "r1_archive_criteria_mismatch")
    return counts, {key: replay[key] for key in PROJECTED_REPLAY}


def regression_diagnostics(junit):
    """Project identifiers and fixed codes only. Never include parameter values or traceback."""
    occurrences = Counter()
    rows = []
    for item in ElementTree.parse(junit).iter("testcase"):
        name = item.get("name", "").partition("[")[0]
        module = item.get("classname", "").split(".")[-1]
        safe = TEST_NAME.fullmatch(name) and TEST_NAME.fullmatch(module)
        identifier = f"{module}::{name}" if safe else "test_id_unavailable"
        occurrences[identifier] += 1
        for tag in ("failure", "error", "skipped"):
            node = item.find(tag)
            if node is None:
                continue
            message = node.get("message", "")
            match = re.match(r"^(AssertionError|PermissionError|FileNotFoundError|TimeoutError|CalledProcessError|ModuleNotFoundError|ValueError|TypeError)(?::|$)", message)
            rows.append({"test_id": identifier, "case_ordinal": occurrences[identifier],
                         "code": "pytest_" + tag, "exception": match[1] if match else None})
    return {"nonpassing_tests": rows}


def verify_test_cases(junit, expected):
    historical, targeted = Counter(), Counter()
    for item in ElementTree.parse(junit).iter("testcase"):
        name = item.get("name", "").partition("[")[0]
        module = re.search(r"(?:^|\.)test_dc05a_([a-z0-9_]+)(?:\.|$)", item.get("classname", ""))
        require(TEST_NAME.fullmatch(name), "unrecognized_test_name")
        require(all(item.find(tag) is None for tag in ("failure", "error", "skipped")), "test_not_passed")
        if module:
            targeted[module[1]] += 1
        else:
            historical[name] += 1
    require(historical == expected, "historical_test_cases_changed")
    require(TARGETS <= targeted.keys(), "targeted_test_modules_missing")
    return {"historical_tests": sum(historical.values()), "targeted_tests": sum(targeted.values()),
            "targeted_modules": dict(sorted(targeted.items())), "failures": 0, "errors": 0, "skipped": 0}


def historical_replay(r1, args, checkout, baseline, run, work, accepted_replay):
    report, comparison, integrity = r1.run_replay(args, checkout, baseline, run, work)
    safe = {key: value for key, value in integrity.items() if isinstance(value, bool)}
    if report["status"] == "PASS":
        require(integrity.get("private_history_immutable") is True and integrity.get("ledger_immutable") is True,
                "historical_artifact_changed")
        details = {"original_candidate_sha256": CANDIDATE, **safe, **comparison["grades"]}
        if accepted_replay is None:
            return evidence_status("BLOCKED", "r1_replay_comparison_unavailable", **details)
        matched = {key: comparison[key] for key in PROJECTED_REPLAY} == accepted_replay
        return evidence_status("PASS", **details) if matched else evidence_status(
            "FAIL", "r1_replay_projection_changed", **details)
    return evidence_status(report["status"], report["failure_code"], **safe)


def exchange_has_private_fields(value):
    if isinstance(value, dict):
        return any(key.casefold() in REDACTED_FIELDS or exchange_has_private_fields(item)
                   for key, item in value.items())
    return isinstance(value, list) and any(exchange_has_private_fields(item) for item in value)


def smoke_result(run, prior):
    output = run.private / "dc05a-smoke.json"
    run.env["DC05A_SMOKE_EVIDENCE"] = str(output)
    try:
        if not run.command("trial_asgi_smoke", prior.pytest(SMOKE_NODE), junit=True):
            raise ValueError("trial_asgi_smoke_failed")
        smoke = read_object(output, 64 << 10)
    finally:
        run.env.pop("DC05A_SMOKE_EVIDENCE", None)
    booleans = {"feedback_saved", "exported", "refresh_no_calls", "theme_switched", "history_retained",
                "artifact_screened"}
    zeros = {"live_provider_operations", "new_cost_micro_usd", "key_prompts"}
    counts = {"requests", "chat_posts", "uploads", "verified_facts", "citations"}
    require(smoke.keys() == booleans | zeros | counts | {
        "mode", "prompt_version", "statuses", "representative_exchange",
    }, "trial_smoke_fields_invalid")
    require(all(smoke[key] is True for key in booleans)
            and all(type(smoke[key]) is int and smoke[key] == 0 for key in zeros)
            and all(type(smoke[key]) is int and 0 < smoke[key] <= 100 for key in counts)
            and smoke["requests"] >= 3 and smoke["chat_posts"] <= smoke["requests"]
            and smoke["mode"] == "mock" and smoke["prompt_version"] == "evidence-integration/2"
            and isinstance(smoke["statuses"], list) and len(smoke["statuses"]) == smoke["requests"]
            and all(isinstance(status, str) and SAFE_CODE.fullmatch(status) for status in smoke["statuses"]),
            "trial_smoke_outcomes_invalid")
    exchange = smoke["representative_exchange"]
    require(isinstance(exchange, dict) and exchange.keys() == {"question", "A", "B", "sources"}
            and isinstance(exchange["question"], str) and exchange["question"].strip()
            and exchange["A"] and exchange["B"] and isinstance(exchange["sources"], list) and exchange["sources"],
            "trial_smoke_exchange_missing")
    require(not exchange_has_private_fields(exchange), "trial_smoke_private_fields")
    prior.screen(json_bytes(smoke).decode())
    return smoke


def network_audit(run, prior):
    files = (Path(os.environ["DC03C_GUARD_LOG"]), Path(run.env["DC03C_GUARD_LOG"]))
    count = sum(len(path.read_bytes().splitlines()) for path in files if path.is_file())
    require(count == 0, "unexpected_external_python_socket_attempt")
    require(run.steps["offline_network"]["status"] == "PASS", "python_socket_audit_not_verified")
    report = {"isolation": "linux_network_namespace_plus_python_socket_audit",
              "blocked_python_socket_operations": count}
    prior.screen(json_bytes(report).decode())
    return report


def run_acceptance(args, work, checkout, baseline, r1, prior, evidence, accepted_cases, accepted_replay):
    checks = evidence["checks"]
    integrity = evidence["integrity"]
    lock, sealed = None, {}
    try:
        lock, sealed = r1.ledger_snapshot(args)
        checks["historical_ledger"] = evidence_status("PASS", checked_files=len(sealed))
    except (FileNotFoundError, r1.Blocked):
        checks["historical_ledger"] = evidence_status("BLOCKED", "historical_ledger_unavailable")
    except PAYLOAD_ERRORS:
        checks["historical_ledger"] = evidence_status("FAIL", "historical_ledger_validation_failed")
    try:
        # Inherit the accepted historical regression checks with the new checkout
        # as their root. The R1 helper takes no live credential or finance input.
        try:
            run = r1.accepted_checks(prior, args, work)
        except ImportError:
            checks["regression"] = evidence_status("BLOCKED", "venv_dependency_missing")
            return
        results = run.steps
        integrity["corpus"] = {key: results["frozen_originals"].get(key) for key in (
            "pdf_files", "physical_pages", "manifest_sha256", "status",
        )}
        if results["full_regression"]["status"] == "PASS" and accepted_cases is not None:
            checks["regression"] = attempt(
                lambda: verify_test_cases(run.private / "full_regression.xml", accepted_cases),
                "historical_test_cases_unverifiable",
            )
        else:
            status = results["full_regression"]["status"]
            checks["regression"] = evidence_status("FAIL" if status == "FAIL" else "BLOCKED",
                                                   "full_regression_unverified")
        if results["full_regression"]["status"] == "FAIL":
            diagnostic = attempt(lambda: regression_diagnostics(run.private / "full_regression.xml"),
                                 "regression_junit_unavailable")
            checks["regression"]["diagnostics"] = diagnostic
        if lock and all(results[key]["status"] == "PASS" for key in (
                "dependencies", "offline_network", "pinned_site", "frozen_originals")):
            replay = {}
            def replay_case():
                replay.update(historical_replay(r1, args, checkout, baseline, run, work, accepted_replay))
            checked = attempt(replay_case, "offline_replay_failed")
            checks["authentic_replay"] = replay or checked
        else:
            checks["authentic_replay"] = evidence_status("BLOCKED", "private_replay_prerequisites_unavailable")
        if all(results[key]["status"] == "PASS" for key in ("dependencies", "offline_network", "pinned_site",
                                                          "frozen_originals")):
            smoke = {}
            checks["trial_asgi_smoke"] = attempt(lambda: smoke.update(smoke_result(run, prior)),
                                                "trial_asgi_smoke_failed")
            if smoke:
                evidence["smoke"] = smoke
        else:
            checks["trial_asgi_smoke"] = evidence_status("BLOCKED", "smoke_prerequisites_unavailable")
        checks["network_audit"] = attempt(lambda: network_audit(run, prior), "network_audit_failed")
        checks["historical_checks"] = {key: {field: entry[field] for field in (
            "status", "exit_code", "duration_ms", "reason", "failure", "tests", "failures", "errors", "skipped"
        ) if field in entry} for key, entry in results.items() if not entry.get("optional")}
    finally:
        if lock:
            try:
                require(all(sha256(r1.private_bytes(path)).hexdigest() == digest for path, digest in sealed.items()),
                        "historical_artifact_changed")
                checks["historical_ledger"]["byte_identical"] = True
            except PAYLOAD_ERRORS:
                checks["historical_ledger"] = evidence_status("FAIL", "historical_artifact_changed",
                                                              byte_identical=False)
            finally:
                lock.close()


def isolated_acceptance(args, checkout, baseline, work, r1, prior):
    evidence = {"checks": {}, "integrity": {"site_commit": prior.SITE, "manifest_sha256": prior.MANIFEST,
                                          "source_baseline": START, "r1_commit": R1_COMMIT}}
    checks = evidence["checks"]
    scope = verify_checkout(args, checkout, baseline)
    evidence["integrity"]["scope_diff"] = scope
    checks["checkout"] = evidence_status("PASS", pinned_ancestry=True, no_merge_in_scope=True,
                                         historical_paths_protected=True, secret_pattern_scan_passed=True)
    checks["handoff"] = attempt(lambda: verify_handoff(args, checkout, scope), "handoff_unverifiable")

    accepted = {}
    def accepted_archive():
        counts, replay = verify_r1_archive(archive_path(args))
        accepted.update(counts=counts, replay=replay)
        return {"sha256": R1_ARCHIVE_SHA, "members": len(R1_MEMBERS), "member_checksums": len(R1_MEMBERS) - 1,
                "historical_tests": R1_TESTS, "criteria_passed": 10}
    checks["accepted_r1_archive"] = attempt(accepted_archive, "accepted_r1_archive_unavailable")

    paths, issues = prior.discover_materials(args.wsl_root, args, git_environment())
    if issues:
        checks["materials"] = evidence_status("BLOCKED", "wsl_materials_unavailable", issues=issues)
        return finish(evidence)
    checks["materials"] = evidence_status("PASS", inputs_resolved=True)
    starting_materials = material_checksums(prior, paths)
    run_acceptance(args, work, checkout, baseline, r1, prior, evidence, accepted.get("counts"),
                   accepted.get("replay"))
    checks["final_checkout"] = attempt(lambda: verify_checkout(args, checkout, baseline) and {},
                                       "final_checkout_verification_failed")
    def unchanged_materials():
        require(material_checksums(prior, paths) == starting_materials, "frozen_materials_changed")
        require(git_text(paths["site"], "rev-parse", "HEAD") == prior.SITE and not git(
            paths["site"], "status", "--porcelain", "--untracked-files=all"), "site_checkout_changed")
        return {"files_byte_identical": True, "site_read_only_confirmed": True}
    checks["final_materials"] = attempt(unchanged_materials, "frozen_materials_changed")
    return finish(evidence)


def material_checksums(prior, paths):
    files = [paths["fixture"], *(paths["cache"] / (sha + ".pdf") for sha in prior.CACHE_PDFS)]
    files.extend(paths["cache"] / name for name in ("audit.json", "preflight.json", prior.TOKENIZER_FILE)
                 if (paths["cache"] / name).is_file())
    return {path: prior.digest(path) for path in files}


def finish(evidence):
    checks = evidence["checks"]

    def check(name):
        return checks.get(name, {}).get("status", "BLOCKED")

    historical = checks.get("historical_checks", {})
    historical_status = gate(*(entry["status"] for entry in historical.values())) if historical else "BLOCKED"
    regression = gate(check("regression"), historical_status)
    smoke = check("trial_asgi_smoke")
    checks["criteria"] = dict(zip(CRITERIA, (
        gate(check("checkout"), check("final_checkout"), check("final_materials"), check("historical_ledger")),
        gate(check("accepted_r1_archive"), regression, check("authentic_replay")),
        smoke,
        gate(smoke, regression),
        gate(smoke, regression, check("historical_ledger")),
        gate(smoke, regression),
        gate(smoke, check("network_audit")),
        gate(regression, check("handoff")),
    )))
    status = gate(*checks["criteria"].values())
    code = next((entry.get("failure_code") for entry in checks.values()
                 if isinstance(entry, dict) and entry.get("status") == status and entry.get("failure_code")), None)
    return evidence | evidence_status(status, code or (
        "offline_acceptance_incomplete" if status != "PASS" else None))


def ensure_isolated():
    require(os.environ.get(PARENT_NS) and os.environ[PARENT_NS] != os.readlink("/proc/self/ns/net")
            and os.environ.get("DC03C_GUARD_ACTIVE") == "1"
            and {name for _, name in socket.if_nameindex()} == {"lo"}, "mandatory_network_isolation_missing")


def verify_worker_workspace(work):
    fd = int(os.environ.get(WORKSPACE_FD, "-1"))
    require(fd >= 3, "worker_workspace_descriptor_missing")
    opened = os.fstat(fd)
    named = work.lstat()
    require(stat.S_ISDIR(opened.st_mode) and stat.S_ISDIR(named.st_mode)
            and opened.st_uid == os.getuid() and not opened.st_mode & 0o077
            and (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)
            and work.resolve() == work
            and Path(__file__).resolve() == work / "trial" / LAUNCHER,
            "worker_workspace_mismatch")


def isolated(work, prepared):
    try:
        ensure_isolated()
        verify_worker_workspace(work)
        checkout, baseline = work / "trial", work / "baseline"
        values = read_object(work / "inputs.json")
        args = SimpleNamespace(**{key: Path(value) if value is not None and key not in {"commit", "blob"} else value
                                  for key, value in values.items()})
        verify_checkout(args, checkout, baseline)
    except PAYLOAD_ERRORS:
        return EXIT["BLOCKED"]

    evidence = {}
    try:
        (work / "isolated").touch()
        r1 = load_module(checkout / PREVIOUS_LAUNCHER)
        prior = r1.prior_runner(checkout)
        if not prepared:
            paths, issues = prior.discover_materials(args.wsl_root, args, git_environment())
            if not issues:
                values.update({key: str(path) for key, path in paths.items()})
                (work / "inputs.json").write_bytes(json_bytes(values))
                os.execve(values["python"], [values["python"], str(checkout / LAUNCHER),
                                            "--isolated", str(work), "prepared"], dict(os.environ))
        evidence = isolated_acceptance(args, checkout, baseline, work, r1, prior)
        prior.screen(json_bytes(evidence).decode())
    except Blocked as error:
        evidence = evidence_status("BLOCKED", str(error))
    except PAYLOAD_ERRORS as error:
        code = str(error)
        evidence = evidence_status("FAIL", code if isinstance(error, ValueError) and SAFE_CODE.fullmatch(code)
                                   else "isolated_acceptance_failed")
    (work / "result.json").write_bytes(json_bytes(evidence))
    return EXIT[evidence["status"]]


def conduct(args, work):
    if not PIN.fullmatch(args.commit) or not PIN.fullmatch(args.blob):
        raise Blocked("invalid_launch_pin")
    if blob_id(Path(__file__)) != args.blob:
        raise Blocked("launcher_blob_mismatch")
    if "microsoft" not in os.uname().release.lower():
        raise Blocked("trusted_wsl_required")
    checkout, baseline = prepare_checkouts(args, work)
    verify_checkout(args, checkout, baseline)
    private = work / "environment"
    private.mkdir(mode=0o700)
    env = git_environment() | {"HOME": str(private), "TMPDIR": str(private),
                               "PYTHONPATH": str(checkout / GUARD), "PYTHONDONTWRITEBYTECODE": "1",
                               "PYTHONNOUSERSITE": "1", PARENT_NS: os.readlink("/proc/self/ns/net"),
                               "DC03C_GUARD_LOG": str(private / "guard.log")}
    inputs = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    (work / "inputs.json").write_bytes(json_bytes(inputs))
    command = ["unshare", "--user", "--map-root-user", "--net", "--", "sh", "-c",
               'ip link set lo up && exec "$@"', "dc05a", sys.executable, str(checkout / LAUNCHER),
               "--isolated", str(work)]
    fd = os.open(work, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with (work / "isolated.log").open("wb") as log:
            result = subprocess.run(command, cwd=checkout, env=env | {WORKSPACE_FD: str(fd)},
                                    pass_fds=(fd,), stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=log, timeout=7200)
    except FileNotFoundError as error:
        raise Blocked("network_namespace_unavailable") from error
    finally:
        os.close(fd)
    if not (work / "isolated").is_file():
        raise Blocked("network_namespace_or_socket_audit_unavailable")
    evidence = read_object(work / "result.json", 1 << 20)
    require(EXIT.get(evidence.get("status")) == result.returncode, "offline_result_invalid")
    return evidence


def bundle(destination, summary, evidence):
    checks = evidence.get("checks", {})
    criteria = dict.fromkeys(CRITERIA, "BLOCKED") | checks.get("criteria", {})
    report = [f'# DS-DC-05A · {summary["status"]}', "", "- DeepSeek: LIVE_NOT_RUN",
              "- Экспертная оценка и Windows live browser UX: NOT RUN.",
              "- Новые операции DeepSeek, расходы и запросы ключа: 0."]
    if summary["failure_code"]:
        report.append(f'- Код завершения: `{summary["failure_code"]}`.')
    report.extend(("", "| Критерий | Результат |", "|---|---|"))
    report.extend(f"| {key} | {status} |" for key, status in criteria.items())
    values = (json_bytes(summary), json_bytes(checks | {"criteria": criteria}),
              json_bytes(evidence.get("integrity", {})),
              json_bytes(evidence.get("smoke") or evidence_status("BLOCKED", "smoke_evidence_unavailable")),
              ("\n".join(report) + "\n").encode())
    contents = dict(zip(MEMBERS, values))
    contents["SHA256SUMS"] = "".join(f"{sha256(raw).hexdigest()}  {name}\n"
                                     for name, raw in contents.items()).encode("ascii")
    destination.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix=".dc05a-", suffix=".zip", dir=destination)
    os.close(fd)
    staging = Path(filename)
    output = staging.with_name(staging.name[1:])
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in contents.items():
                archive.writestr(name, raw)
        verify_members(staging, MEMBERS)
        require(not output.exists(), "report_name_collision")
        staging.rename(output)
    finally:
        staging.unlink(missing_ok=True)
    return output


def parse_path(value):
    return Path(value).expanduser().absolute()


def main():
    os.umask(0o077)
    sys.dont_write_bytecode = True
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--isolated":
        return isolated(Path(sys.argv[2]), prepared=len(sys.argv) == 4)
    home = Path.home().resolve()
    parser = Parser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--blob", required=True)
    parser.add_argument("--wsl-root", type=parse_path, default=home / "ds-dc03b-validation")
    default_site = home / "ds-dc02-cal-validation/Saturn-Main-Site"
    parser.add_argument("--site", type=parse_path, default=default_site if default_site.is_dir() else None)
    parser.add_argument("--cache", type=parse_path, default=os.environ.get("DS_DC_CACHE"))
    parser.add_argument("--fixture", type=parse_path, default=os.environ.get("DS_DC_Q01_CANDIDATE"))
    parser.add_argument("--python", type=parse_path)
    parser.add_argument("--r1-report", type=parse_path)
    parser.add_argument("--ledger", type=parse_path, default=home / ".local/state/ds-dc02/ledger")
    parser.add_argument("--output", type=parse_path, default=OUTPUT)
    summary = {"task": TASK, "pin": None, "launcher_blob": None, "live": "LIVE_NOT_RUN",
               "owner_evaluation": "NOT RUN", "windows_live_browser": "NOT RUN", "new_provider_operations": 0,
               "new_cost_micro_usd": 0, "operations": dict.fromkeys(
                   ("paid_requests", "uploads", "chats", "statuses", "deletes", "retries", "key_prompts"), 0)}
    destination = OUTPUT
    with tempfile.TemporaryDirectory(prefix="dc05a-acceptance-", dir="/tmp") as temporary:
        try:
            args = parser.parse_args()
            summary.update(pin=args.commit if PIN.fullmatch(args.commit) else None,
                           launcher_blob=args.blob if PIN.fullmatch(args.blob) else None)
            requested = args.output.resolve()
            protected = (args.site, args.cache, args.ledger.parent, args.wsl_root)
            if any(root and requested.is_relative_to(root.resolve()) for root in protected):
                if any(root and OUTPUT.resolve().is_relative_to(root.resolve()) for root in protected):
                    destination = Path(tempfile.mkdtemp(prefix="dc05a-reports-", dir="/tmp"))
                raise Blocked("unsafe_report_directory")
            destination = requested
            evidence = conduct(args, Path(temporary))
        except Blocked as error:
            evidence = evidence_status("BLOCKED", str(error))
        except (*PAYLOAD_ERRORS, KeyboardInterrupt) as error:
            code = str(error)
            evidence = evidence_status("FAIL", code if isinstance(error, ValueError) and SAFE_CODE.fullmatch(code)
                                       else "launcher_failed")
        summary.update(status=evidence["status"], failure_code=evidence["failure_code"])
        output = bundle(destination, summary, evidence)
    print(f"DC-05A ZIP: {output}")
    return EXIT[summary["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
