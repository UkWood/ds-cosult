"""Run the pinned DC-04B-R1 offline WSL acceptance and export one checked ZIP."""
import argparse
import fcntl
from hashlib import sha1, sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import zipfile


BASELINE = "2dac638843b1ce4ac7506de8fb3e3bb222d2199d"
REMOTE = "https://github.com/UkWood/ds-cosult.git"
REF = "refs/heads/feat/ds-dc-01-document-centric-pilot"
LAUNCHER = "scripts/validation/validate_dc04b_r1.py"
PRIOR = "scripts/validation/validate_dc03c.py"
GUARD = "scripts/validation/dc03c-offline"
REPLAY = "ds_dc/dc04b_r1_replay.py"
OUTPUT = Path("/mnt/c/DS-Validation/Reports")
PIN = re.compile(r"[0-9a-f]{40}")
SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,79}")
MODIFIED = {"ds_dc/technical_verifier.py", "ds_dc/evidence_answer.py", "ds_dc/evidence_integration.py",
            "ds_dc/quality_report.py", "ds_dc/structural_pdf.py"}
ADDED = {LAUNCHER, REPLAY, "tests/test_dc04b_r1.py", "tests/test_dc04b_r1_launcher.py",
         "tests/test_dc04b_r1_replay.py", "docs/handoffs/DS-DC-04B-R1-HANDOFF.md"}
MEMBERS = ("summary.json", "checks.json", "ab-before-after.json", "integrity.json", "report.md", "SHA256SUMS")
STATUSES = {"PASS", "FAIL", "BLOCKED"}
BASELINE_TESTS = 371
R1_TESTS = {
    "R1-06": {"test_inadmissible_alternatives_keep_their_negative_verdict",
              "test_action_requires_safe_context_and_a_verified_published_cause"},
    "R1-07": {"test_exact_roles_normalize_and_original_fields_are_preserved"},
    "R1-08": {"test_future_prompt_changes_wire_and_preserves_historical_payload"},
}
HISTORICAL_ARCHIVE_SHA = "7d38da0eec91e8db293267e86c383983a749da54309f4eccb163d1c9c56bf5e7"
HISTORICAL_REPORT_SHA = "062a7656a1afdb324506e80392f8bbba5f2be6282cb4411508501a6e7ce501ff"
PARENT_NS = "DC04B_R1_PARENT_NETNS"
GUARD_ACTIVE = "DC03C_GUARD_ACTIVE"
ASSERT_NAMESPACE = 'test "$(readlink /proc/self/ns/net)" != "$DC04B_R1_PARENT_NETNS" && exec "$@"'
REPLAY_COMMAND = "import runpy,sys; sys.argv=sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')"


class Blocked(ValueError):
    """A prerequisite for independent acceptance is unavailable."""


def require(condition, code):
    if not condition:
        raise ValueError(code)


def code_for(error, fallback):
    reason = str(error)
    return reason if isinstance(error, ValueError) and SAFE_CODE.fullmatch(reason) else fallback


def git_environment(*, online=False):
    return dict(PATH=os.environ.get("PATH", os.defpath), LANG="C.UTF-8", GIT_CONFIG_NOSYSTEM="1",
                GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0",
                GIT_ALLOW_PROTOCOL="https" if online else "")


def git(repo, env, *command):
    return subprocess.check_output(["git", "-C", str(repo), "-c", "core.hooksPath=" + os.devnull,
                                    "-c", "core.fsmonitor=false", *command], env=env,
                                   stderr=subprocess.PIPE, timeout=180)


def git_text(repo, env, *command):
    return git(repo, env, *command).decode("ascii").strip()


def launcher_blob(path):
    data = path.read_bytes()
    return sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def validate_scope(raw):
    require(raw.endswith(b"\0"), "r1_scope_malformed")
    parts = raw[:-1].decode("ascii").split("\0")
    require(len(parts) % 2 == 0, "r1_scope_malformed")
    changes = {}
    for header, path in zip(parts[::2], parts[1::2]):
        require(path in MODIFIED | ADDED and path not in changes, "r1_scope_path_forbidden")
        expected = (":100644", "100644", "M") if path in MODIFIED else (":000000", "100644", "A")
        old, new, _, _, action = header.split()
        require((old, new, action) == expected, "r1_scope_change_forbidden")
        changes[path] = action
    return changes


def verify_checkouts(args, checkout, baseline, env):
    for pin, tree in ((args.commit, checkout), (BASELINE, baseline)):
        require(git_text(tree, env, "rev-parse", "HEAD") == pin, "checkout_pin_mismatch")
        require(not git(tree, env, "status", "--porcelain", "--untracked-files=all"), "checkout_dirty")
    require(git_text(checkout, env, "rev-parse", f"HEAD:{LAUNCHER}") == args.blob
            and launcher_blob(checkout / LAUNCHER) == args.blob, "launcher_blob_mismatch")
    require(args.commit != BASELINE and git_text(checkout, env, "merge-base", BASELINE, args.commit) == BASELINE,
            "checkout_baseline_mismatch")
    require(git_text(checkout, env, "merge-base", args.commit, "FETCH_HEAD") == args.commit,
            "commit_not_in_draft_branch")
    changes = validate_scope(git(checkout, env, "diff", "--raw", "--no-renames", "--no-ext-diff", "-z",
                                 BASELINE, args.commit))
    require({LAUNCHER, REPLAY, "tests/test_dc04b_r1.py"} <= changes.keys(), "r1_scope_artifacts_missing")
    return changes


def prepare_checkouts(args, work):
    checkout, baseline = work / "r1", work / "baseline"
    checkout.mkdir()
    offline = git_environment()
    try:
        git(checkout, offline, "init", "--quiet", "--template=")
        git(checkout, git_environment(online=True), "fetch", "--quiet", "--no-tags", "--no-recurse-submodules",
            REMOTE, REF)
    except (OSError, subprocess.SubprocessError) as error:
        raise Blocked("draft_checkout_fetch_failed") from error
    git(checkout, offline, "checkout", "--quiet", "--detach", args.commit)
    git(checkout, offline, "worktree", "add", "--quiet", "--detach", str(baseline), BASELINE)
    return checkout, baseline


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def read_object(path, limit=1 << 20):
    require(path.is_file() and not path.is_symlink(), "evidence_file_missing")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "evidence_file_oversize")
    value = json.loads(raw)
    require(isinstance(value, dict), "evidence_object_invalid")
    return value


def prior_runner(checkout):
    spec = importlib.util.spec_from_file_location("dc04a_acceptance", checkout / PRIOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ensure_isolated():
    require(bool(os.environ.get(PARENT_NS)) and os.environ[PARENT_NS] != os.readlink("/proc/self/ns/net")
            and os.environ.get(GUARD_ACTIVE) == "1", "mandatory_network_isolation_missing")


def accepted_checks(prior, args, work):
    # The namespace encloses the whole acceptance. Also check that every child inherited it.
    class InheritedRun(prior.Run):
        def offline(self):
            ensure_isolated()
            self.env[PARENT_NS] = os.environ[PARENT_NS]
            self.prefix = ["sh", "-c", ASSERT_NAMESPACE, "dc04b-r1"]
            with (self.private / "network.log").open("wb") as log:
                subprocess.run(self.prefix + [sys.executable, "-c", prior.PROBE.replace("try:\n", "\ntry:\n")],
                               env=self.env | {"DC03C_GUARD_PROBE": "1"}, timeout=15, check=True,
                               stdout=log, stderr=log)
            self.isolation = "linux_network_namespace_plus_python_socket_audit"
            return {"isolation": self.isolation}

    # R1's exact-baseline scope check retains finance and every historical test byte for byte.
    # The previous gate allowed finance for accepted DC-04B. Permit only scoped R1 changes here.
    prior.PROTECTED = tuple(path for path in prior.PROTECTED if path != "ds_dc/finance.py")
    prior.PROTECTED_R2 = tuple(path for path in prior.PROTECTED_R2 if path not in MODIFIED)
    args.output = work
    args.financial_ledger = None
    args.protected_file = []
    args.extra_tests = []
    run = InheritedRun(args)
    run.run()
    regression = run.steps["full_regression"]
    if regression["status"] == "PASS" and (regression["tests"] < BASELINE_TESTS
            or any(regression[key] for key in ("failures", "errors", "skipped"))):
        regression.update(status="FAIL", failure="r1_regression_count_or_outcomes")
    return run


def private_info(info, kind):
    return kind(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077


def private_bytes(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        require(private_info(os.fstat(stream.fileno()), stat.S_ISREG), "historical_artifact_not_private")
        raw = stream.read((64 << 20) + 1)
    require(len(raw) <= 64 << 20, "historical_artifact_oversize")
    return raw


def ledger_snapshot(args):
    require(args.ledger.resolve() == args.ledger
            and private_info(args.ledger.lstat(), stat.S_ISDIR), "ledger_path_invalid")
    lock_path = args.ledger / ".lock"
    lock = os.fdopen(os.open(lock_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb")
    try:
        require(private_info(os.fstat(lock.fileno()), stat.S_ISREG), "ledger_path_invalid")
        try:
            fcntl.flock(lock, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Blocked("ledger_busy") from error
        ledger_path = args.ledger / "ledger.json"
        evidence = {lock_path: sha256(private_bytes(lock_path)).hexdigest(),
                    ledger_path: sha256(private_bytes(ledger_path)).hexdigest()}
        return lock, evidence
    except BaseException:
        lock.close()
        raise


def run_replay(args, checkout, baseline, run, work):
    artifacts = work / "replay"
    artifacts.mkdir(mode=0o700)
    for stage, repo, pin in (("baseline", baseline, BASELINE), ("r1", checkout, args.commit)):
        command = [sys.executable, "-c", REPLAY_COMMAND, str(checkout / REPLAY), "--stage", stage,
                   "--commit", pin, "--private-root", str(args.ledger), "--artifacts", str(artifacts)]
        with (work / f"replay-{stage}.log").open("wb") as log:
            result = subprocess.run(run.prefix + command, cwd=repo, env=run.env,
                                    timeout=600, stdout=log, stderr=log)
        if result.returncode:
            break
    report = read_object(artifacts / "replay-checks.json")
    status, failure, criteria = report.get("status"), report.get("failure_code"), report.get("criteria")
    require(status in STATUSES and (status == "PASS") == (result.returncode == 0)
            and ((status == "PASS" and failure is None) or (isinstance(failure, str) and SAFE_CODE.fullmatch(failure)))
            and isinstance(criteria, dict) and criteria.keys() == {"R1-03", "R1-04"}
            and all(value in STATUSES for value in criteria.values())
            and (status == "PASS") == all(value == "PASS" for value in criteria.values()),
            "replay_status_invalid")
    comparison = artifacts / "ab-before-after.json"
    return (report, read_object(comparison) if status == "PASS" or comparison.exists() else None,
            read_object(artifacts / "integrity.json"))


def verdict(status, reason=None, **details):
    return {"status": status, "failure_code": reason, **details}


def isolated_acceptance(args, checkout, baseline, work, prior):
    env = git_environment()
    scope = verify_checkouts(args, checkout, baseline, env)
    integrity = {"baseline_commit": BASELINE, "r1_commit": args.commit, "launcher_blob": args.blob,
                 "site_commit": prior.SITE, "manifest_sha256": prior.MANIFEST,
                 "historical_fixture_sha256": prior.FIXTURE, "accepted_archive_sha256": HISTORICAL_ARCHIVE_SHA,
                 "accepted_report_sha256": HISTORICAL_REPORT_SHA, "scope_diff": scope}
    lock, sealed = None, {}
    ledger_status = verdict("BLOCKED", "historical_ledger_missing")
    try:
        lock, sealed = ledger_snapshot(args)
        ledger_status = verdict("PASS", checked_files=len(sealed))
    except Blocked as error:
        ledger_status = verdict("BLOCKED", code_for(error, "historical_ledger_missing"))
    except FileNotFoundError:
        pass
    except (OSError, ValueError, KeyError, TypeError) as error:
        ledger_status = verdict("FAIL", code_for(error, "historical_ledger_validation_failed"))
    replay, ab = verdict("BLOCKED", "replay_prerequisites_unavailable"), None
    try:
        run = accepted_checks(prior, args, work)
        if ledger_status["failure_code"] != "ledger_busy" and all(run.steps[key]["status"] == "PASS" for key in (
                "dependencies", "offline_network", "pinned_site", "frozen_originals")):
            replay_materials = run.sealed_materials(True, run.steps["authentic_fixture"]["status"] == "PASS")
            try:
                replay, ab, integrity["replay"] = run_replay(args, checkout, baseline, run, work)
            except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
                replay = verdict("FAIL", code_for(error, "offline_replay_failed"))

            def unchanged_corpus():
                run.pinned_site()
                require(all(prior.digest(path) == digest for path, digest in replay_materials.items()),
                        "replay_material_changed")
                return {"checked_files": len(replay_materials)}

            run.inspect("final_replay_material_checksums", unchanged_corpus)
        else:
            run.record("final_replay_material_checksums", "BLOCKED")
        if sealed:
            try:
                require(all(sha256(private_bytes(path)).hexdigest() == digest for path, digest in sealed.items()),
                        "historical_artifact_changed")
                ledger_status["byte_identical"] = True
            except (OSError, ValueError) as error:
                ledger_status = verdict("FAIL", code_for(error, "historical_artifact_changed"), byte_identical=False)
    finally:
        if lock:
            lock.close()

    audits = (Path(run.env["DC03C_GUARD_LOG"]), Path(os.environ["DC03C_GUARD_LOG"]))
    blocked_sockets = sum(len(audit.read_bytes().splitlines()) for audit in audits if audit.exists())
    network = run.steps["offline_network"]["status"]
    network_audit = verdict("FAIL" if blocked_sockets else network,
                            "unexpected_external_python_socket_attempt" if blocked_sockets else None,
                            blocked_python_socket_operations=blocked_sockets, isolation=run.isolation)
    verify_checkouts(args, checkout, baseline, env)
    acceptance = [entry for entry in run.steps.values() if not entry.get("optional")]
    old_results = {entry["status"] for entry in acceptance}
    acceptance_status = "FAIL" if "FAIL" in old_results else "BLOCKED" if "BLOCKED" in old_results else "PASS"
    integrity["historical_ledger"] = ledger_status
    integrity["baseline_and_r1_checkouts_clean_after"] = True
    sealed_materials = acceptance_gate([run.steps[key]["status"] for key in (
        "frozen_originals", "authentic_fixture", "initial_material_checksums", "final_material_checksums",
        "final_replay_material_checksums")])
    integrity["frozen_materials_byte_identical"] = sealed_materials == "PASS"
    regression = run.steps["full_regression"]
    passed_tests = {case.get("test") for case in regression.get("cases", []) if case["status"] == "PASS"}
    targeted = {criterion: acceptance_gate([regression["status"],
                "PASS" if names <= passed_tests else "FAIL" if regression["status"] == "PASS" else "BLOCKED"])
                for criterion, names in R1_TESTS.items()}
    historical = [run.steps[key]["status"] for key in (
        "historical_matrix", "structural_matrix", "v2_r01_provenance", "evidence_context_r2",
        "frozen_pdf_context_r2", "historical_wire_sizing", "authentic_q01_shadow")]
    immutable = integrity.get("replay", {}).get("private_history_immutable")
    history_status = "PASS" if immutable is True else "FAIL" if immutable is False else "BLOCKED"
    criteria = {"R1-01": acceptance_gate([ledger_status["status"], sealed_materials, history_status]),
                "R1-02": regression["status"], "R1-03": "BLOCKED", "R1-04": "BLOCKED",
                "R1-05": acceptance_gate(historical), **targeted,
                "R1-08": acceptance_gate([targeted["R1-08"], run.steps["historical_wire_sizing"]["status"]]),
                "R1-09": acceptance_gate([network_audit["status"], ledger_status["status"], history_status]),
                "R1-10": "PASS"}
    criteria.update(replay.get("criteria", {}))
    checks = {"criteria": criteria, "prior_acceptance": run.steps, "replay": replay, "network_audit": network_audit}
    status = acceptance_gate([acceptance_status, replay["status"], *criteria.values()])
    reason = next((item["failure_code"] for item in (network_audit, ledger_status, replay)
                   if item["status"] == status and item["failure_code"]), None)
    return {"checks": checks, "integrity": integrity, "ab": ab,
            **verdict(status, reason or ("offline_acceptance_failed" if status != "PASS" else None))}


def acceptance_gate(statuses):
    return "FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PASS"


def isolated(work, prepared):
    ensure_isolated()
    (work / "isolated").touch()
    checkout, baseline = work / "r1", work / "baseline"
    values = read_object(work / "inputs.json")
    args = SimpleNamespace(**{key: Path(raw) if raw is not None and key not in {"commit", "blob"} else raw
                              for key, raw in values.items()})
    try:
        verify_checkouts(args, checkout, baseline, git_environment())
        prior = prior_runner(checkout)
        if not prepared:
            paths, issues = prior.discover_materials(args.wsl_root, args, git_environment())
            if issues:
                result = {"checks": {"materials": verdict("BLOCKED", "wsl_materials_unavailable", issues=issues)},
                          **verdict("BLOCKED", "wsl_materials_unavailable")}
                (work / "result.json").write_bytes(json_bytes(result))
                return 2
            for key, path in paths.items():
                values[key] = str(path.absolute())
            (work / "inputs.json").write_bytes(json_bytes(values))
            os.execve(values["python"], [values["python"], str(checkout / LAUNCHER),
                                        "--isolated", str(work), "prepared"], dict(os.environ))
        result = isolated_acceptance(args, checkout, baseline, work, prior)
        prior.screen(json_bytes(result).decode())
    except Blocked as error:
        result = verdict("BLOCKED", code_for(error, "offline_prerequisite_unavailable"))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = verdict("FAIL", code_for(error, "offline_acceptance_failed"))
    (work / "result.json").write_bytes(json_bytes(result))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[result["status"]]


def conduct(args, work):
    if not PIN.fullmatch(args.commit) or not PIN.fullmatch(args.blob):
        raise Blocked("invalid_launch_pin")
    if launcher_blob(Path(__file__)) != args.blob:
        raise Blocked("launcher_blob_mismatch")
    if "microsoft" not in os.uname().release.lower():
        raise Blocked("trusted_wsl_required")
    checkout, baseline = prepare_checkouts(args, work)
    verify_checkouts(args, checkout, baseline, git_environment())
    private = work / "environment"
    private.mkdir(mode=0o700)
    env = git_environment() | {"HOME": str(private), "TMPDIR": str(private),
                               "PYTHONPATH": str(checkout / GUARD), "PYTHONDONTWRITEBYTECODE": "1",
                               "PYTHONNOUSERSITE": "1", PARENT_NS: os.readlink("/proc/self/ns/net"),
                               "DC03C_GUARD_LOG": str(private / "guard.log")}
    args.output = None
    (work / "inputs.json").write_bytes(json_bytes({key: str(value) if isinstance(value, Path) else value
                                                 for key, value in vars(args).items()}))
    command = ["unshare", "--user", "--map-root-user", "--net", "--", "sh", "-c",
               'ip link set lo up && exec "$@"', "dc04b-r1", sys.executable,
               str(checkout / LAUNCHER), "--isolated", str(work)]
    try:
        with (work / "isolated.log").open("wb") as log:
            result = subprocess.run(command, cwd=checkout, env=env, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=log, timeout=7200)
    except FileNotFoundError as error:
        raise Blocked("network_namespace_unavailable") from error
    if not (work / "isolated").is_file():
        raise Blocked("network_namespace_unavailable")
    evidence = read_object(work / "result.json", 8 << 20)
    require(evidence.get("status") in STATUSES and (evidence["status"] == "PASS") == (result.returncode == 0),
            "offline_result_invalid")
    return evidence


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        require(tuple(archive.namelist()) == MEMBERS and archive.testzip() is None, "zip_crc_or_members")
        expected = "".join(f"{sha256(archive.read(name)).hexdigest()}  {name}\n" for name in MEMBERS[:-1])
        require(archive.read("SHA256SUMS").decode("ascii") == expected, "zip_member_sha_mismatch")


def bundle(destination, summary, evidence):
    checks = evidence.get("checks", {})
    criteria = {f"R1-{index:02}": "BLOCKED" for index in range(1, 11)}
    criteria.update(checks.get("criteria", {}))
    criteria["R1-10"] = "PASS"
    checks = checks | {"criteria": criteria}
    fallback = verdict("BLOCKED", summary["failure_code"] or "replay_not_available")
    integrity = {"baseline_commit": BASELINE, "r1_commit": summary["pin"],
                 "launcher_blob": summary["launcher_blob"]} | evidence.get("integrity", {})
    report = [f'# DS-DC-04B-R1 · {summary["status"]}', "", "- Экспертная оценка — NOT RUN",
              "- Новый prompt на модели — NOT RUN", "- Новые операции провайдера и расходы — 0"]
    if summary["failure_code"]:
        report.append(f'- Код завершения — `{summary["failure_code"]}`')
    report += ["", "| Критерий | Результат |", "|---|---|"]
    report.extend(f"| {criterion} | {state} |" for criterion, state in criteria.items())
    values = (json_bytes(summary), json_bytes(checks), json_bytes(evidence.get("ab") or fallback),
              json_bytes(integrity), ("\n".join(report) + "\n").encode())
    contents = dict(zip(MEMBERS, values))
    contents["SHA256SUMS"] = "".join(f"{sha256(raw).hexdigest()}  {name}\n"
                                     for name, raw in contents.items()).encode("ascii")
    destination.mkdir(parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix=".dc04b-r1-", suffix=".zip", dir=destination)
    os.close(fd)
    staging = Path(filename)
    final = staging.with_name(staging.name[1:])
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in contents.items():
                archive.writestr(name, raw)
        verify_archive(staging)
        require(not final.exists(), "report_name_collision")
        staging.rename(final)
    finally:
        staging.unlink(missing_ok=True)
    return final


def path(value):
    return Path(value).expanduser().absolute()


def main():
    os.umask(0o077)
    sys.dont_write_bytecode = True
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--isolated":
        return isolated(Path(sys.argv[2]), prepared=len(sys.argv) == 4)
    home = Path.home().resolve()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--blob", required=True)
    parser.add_argument("--wsl-root", type=path, default=home / "ds-dc03b-validation")
    parser.add_argument("--site", type=path, default=home / "ds-dc02-cal-validation/Saturn-Main-Site")
    parser.add_argument("--cache", type=path, default=os.environ.get("DS_DC_CACHE"))
    parser.add_argument("--fixture", type=path, default=os.environ.get("DS_DC_Q01_CANDIDATE"))
    parser.add_argument("--python", type=path)
    parser.add_argument("--output", type=path, default=OUTPUT)
    parser.set_defaults(ledger=home / ".local/state/ds-dc02/ledger")
    args = parser.parse_args()
    destination = args.output.resolve()
    protected = (args.site, args.cache, args.ledger.parent, args.wsl_root)
    summary = {"task": "DS-DC-04B-R1", "pin": args.commit if PIN.fullmatch(args.commit) else None,
               "launcher_blob": args.blob if PIN.fullmatch(args.blob) else None,
               "live": "LIVE_NOT_RUN", "new_prompt_provider_evaluation": "NOT RUN", "expert_score": "NOT RUN",
               "new_provider_operations": 0, "new_cost_micro_usd": 0,
               "operations": dict.fromkeys(("paid_requests", "uploads", "chats", "statuses", "deletes", "retries",
                                             "key_prompts"), 0)}
    with tempfile.TemporaryDirectory(prefix="dc04b-r1-") as temporary:
        try:
            if any(root and destination.is_relative_to(root.resolve()) for root in protected):
                destination = OUTPUT
                raise Blocked("unsafe_report_directory")
            evidence = conduct(args, Path(temporary))
        except Blocked as error:
            evidence = verdict("BLOCKED", code_for(error, "offline_prerequisite_unavailable"))
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, KeyboardInterrupt) as error:
            evidence = verdict("FAIL", code_for(error, "launcher_failed"))
        summary.update(status=evidence["status"], failure_code=evidence["failure_code"])
        archive = bundle(destination, summary, evidence)
    print(f"DC-04B-R1 ZIP: {archive}")
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[summary["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
