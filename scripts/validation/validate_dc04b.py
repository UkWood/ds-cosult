"""Prepare the pinned checkout, run isolated acceptance and export one DC-04B ZIP."""
import argparse
import fcntl
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import zipfile

BASELINE = "e1ca91cfc467565662c2b421a11a726840171b8d"
REMOTE = "https://github.com/UkWood/ds-cosult.git"
REF = "refs/heads/feat/ds-dc-01-document-centric-pilot"
LAUNCHER = "scripts/validation/validate_dc04b.py"
PRIOR = "scripts/validation/validate_dc03c.py"
OUTPUT = Path("/mnt/c/DS-Validation/Reports")
PIN = re.compile(r"[a-f0-9]{40}")
SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,79}")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def git_environment(*, online):
    return dict(PATH=os.environ.get("PATH", os.defpath), LANG="C.UTF-8", GIT_CONFIG_NOSYSTEM="1",
                GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0",
                GIT_ALLOW_PROTOCOL="https" if online else "", PYTHONNOUSERSITE="1",
                PYTHONDONTWRITEBYTECODE="1")


def git(repo, env, *command):
    return subprocess.check_output(["git", "-C", str(repo), "-c", "core.hooksPath=" + os.devnull,
                                    "-c", "core.fsmonitor=false", *command],
                                   env=env, stderr=subprocess.PIPE, timeout=180).decode().strip()


def check_checkout(checkout, args, env):
    require(git(checkout, env, "rev-parse", "HEAD") == args.commit, "checkout_pin_mismatch")
    require(not git(checkout, env, "status", "--porcelain", "--untracked-files=all"), "checkout_dirty")
    require(git(checkout, env, "rev-parse", f"HEAD:{LAUNCHER}") == args.blob, "launcher_blob_mismatch")
    require(git(checkout, env, "merge-base", BASELINE, args.commit) == BASELINE and args.commit != BASELINE,
            "checkout_baseline_mismatch")


def checkout_for(args):
    args.state.mkdir(parents=True, mode=0o700, exist_ok=True)
    info = args.state.lstat()
    require(not args.state.is_symlink() and info.st_uid == os.getuid() and not info.st_mode & 0o077,
            "launcher_state_must_be_private")
    checkout = args.state / ("checkout-" + args.commit)
    lock_path = args.state / ".lock"
    with os.fdopen(os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600), "r+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        env = git_environment(online=False)
        if not checkout.exists():
            online = git_environment(online=True)
            with tempfile.TemporaryDirectory(dir=args.state, prefix=".checkout-") as staging:
                repo = Path(staging) / "repo"
                repo.mkdir()
                git(repo, online, "init", "--quiet", "--template=")
                git(repo, online, "fetch", "--quiet", "--no-tags", "--no-recurse-submodules", REMOTE, REF)
                require(git(repo, env, "merge-base", args.commit, "FETCH_HEAD") == args.commit,
                        "commit_not_in_draft_branch")
                git(repo, env, "checkout", "--quiet", "--detach", args.commit)
                check_checkout(repo, args, env)
                repo.rename(checkout)
        require(not checkout.is_symlink(), "launcher_checkout_invalid")
        check_checkout(checkout, args, env)
    return checkout


def prior_runner(checkout):
    spec = importlib.util.spec_from_file_location("dc04a_acceptance", checkout / PRIOR)
    prior = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prior)
    return prior


def isolated_acceptance(args, checkout, work, ledger, financial):
    prior = prior_runner(checkout)
    offline_args = SimpleNamespace(commit=args.commit, site=args.site, cache=args.cache, fixture=args.fixture,
                                   output=work, financial_ledger=args.ledger, network="namespace", receipt=None,
                                   protected_file=[args.ledger / "ledger.json"], extra_tests=[])
    # The DC-04B gate in Ledger.reserve is the only exception to the DC-04A protected set.
    prior.PROTECTED = tuple(path for path in prior.PROTECTED if path != "ds_dc/finance.py")
    acceptance = prior.Run(offline_args)
    passed = acceptance.run()
    acceptance_zip = acceptance.package(passed)
    prior.verify_archive(acceptance_zip)
    with zipfile.ZipFile(acceptance_zip) as source:
        details = source.read("checks.json")
        report = source.read("summary.json")
    proof = work / "offline-summary.json"
    proof.write_bytes(report)
    (work / "offline-checks.json").write_bytes(details)
    matrix = json.loads(details).get("full_regression", {})
    require(passed and matrix.get("tests", 0) > 328 and matrix.get("skipped") == 0,
            "offline_acceptance_failed")
    archive = find_archive(args, ledger, financial)
    env = acceptance.env | {"DC04B_PARENT_NETNS": os.readlink("/proc/self/ns/net")}
    code, reason = invoke(args, checkout, "preflight", work, prefix=acceptance.prefix, env=env, archive=archive)
    require(code in {0, 4}, reason or "financial_preflight_failed")
    require(not (acceptance.private / "guard.log").exists(), "offline_socket_audit_failed")
    return report, archive


def invoke(args, checkout, stage, work, *, prefix=(), env=None, archive=None):
    if env is None:
        env = git_environment(online=False)
    output = work / "experiment.json"
    command = [str(args.python), "-m", "ds_dc.quality_lab", "live", "--stage", stage, "--commit", args.commit,
               "--site", str(args.site), "--cache", str(args.cache), "--ledger", str(args.ledger),
               "--receipt", str(work / "admission.json"), "--output", str(output),
               "--offline-summary", str(work / "offline-summary.json")]
    if archive is not None:
        command.extend(["--history-archive", str(archive)])
    log = work / f"{stage}.log"
    with log.open("wb") as diagnostics:
        process = subprocess.run([*prefix, *command], cwd=checkout, env=env, stdout=diagnostics,
                                 stderr=subprocess.STDOUT, timeout=1800)
    status = None
    try:
        lines = log.read_text(encoding="utf-8").splitlines()
        if lines:
            code = json.loads(lines[-1]).get("status")
            if isinstance(code, str) and SAFE_CODE.fullmatch(code):
                status = code
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return process.returncode, status


def replay_saved(ledger, work):
    paths = (ledger, ledger / ".lock", ledger / "ledger.json", ledger / "dc04b-q01-n",
             ledger / "dc04b-q01-n/report.json")
    if not all(path.exists() for path in paths):
        return False
    for path in paths:
        info = path.lstat()
        require(not path.is_symlink() and info.st_uid == os.getuid() and not info.st_mode & 0o077,
                "saved_report_integrity_error")
    with paths[1].open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        events = json.loads(paths[2].read_bytes()).get("dc04b_events", [])
        if len(events) != 2 or events[1].get("kind") != "report_saved":
            return False
        raw = paths[-1].read_bytes()
        require(sha256(raw).hexdigest() == events[1].get("digest"), "saved_report_integrity_error")
        (work / "experiment.json").write_bytes(raw)
    return True


def conduct(args, work, summary):
    require(PIN.fullmatch(args.commit) and PIN.fullmatch(args.blob), "invalid_launch_pin")
    require("microsoft" in os.uname().release.lower(), "trusted_wsl_required")
    checkout = checkout_for(args)
    require(not any(args.output.is_relative_to(root) for root in (checkout, args.state, args.ledger, args.site)),
            "unsafe_report_directory")
    require(args.ledger.resolve() == Path.home().resolve() / ".local/state/ds-dc02/ledger", "ledger_path_invalid")
    if replay_saved(args.ledger, work):
        summary.update(status="replayed", live="PREVIOUSLY_RESERVED", new_provider_operations=0)
        return True
    prior = prior_runner(checkout)
    materials, problems = prior.discover_materials(args.wsl_root, args, git_environment(online=False))
    for field, path in materials.items():
        if path is not None:
            setattr(args, field, path)
    require(not problems, "wsl_materials_missing_or_ambiguous")
    require(not args.output.is_relative_to(args.cache), "unsafe_report_directory")

    # Read-only probe for a previous attempt. It precedes even expiry checks and needs no network.
    replay, _ = invoke(args, checkout, "replay", work)
    if replay == 0:
        summary.update(status="replayed", live="PREVIOUSLY_RESERVED", new_provider_operations=0)
        return True
    command = [str(args.python), "-I", str(checkout / LAUNCHER), "--coordinate-work", str(work),
               "--commit", args.commit, "--blob", args.blob, "--site", str(args.site),
               "--cache", str(args.cache), "--fixture", str(args.fixture), "--wsl-root", str(args.wsl_root),
               "--python", str(args.python)]
    if args.history_archive:
        command.extend(["--history-archive", str(args.history_archive)])
    try:
        result = subprocess.run(command, cwd=checkout, env=git_environment(online=False), timeout=7200)
        code = result.returncode
    except (subprocess.SubprocessError, KeyboardInterrupt):
        code = 1

    marker = work / "execution-started"
    experiment = work / "experiment.json"
    if (work / "replayed").is_file():
        summary.update(status="replayed", live="PREVIOUSLY_RESERVED", new_provider_operations=0)
        return True
    if marker.is_file():
        summary.update(live="NOT_CONFIRMED", new_provider_operations=None)
        if not experiment.exists():
            replay, _ = invoke(args, checkout, "replay", work)
            if replay == 3:
                summary.update(live="LIVE_NOT_RUN", new_provider_operations=0)
    if experiment.is_file():
        report = json.loads(experiment.read_bytes())
        money = report["financial"]
        summary.update(live="ATTEMPT_RECORDED",
                       new_provider_operations=money["attempted_uploads"] + money["attempted_chat"])
    reason_path = work / "failure"
    reason = reason_path.read_text().strip() if reason_path.is_file() else ""
    summary["status"] = reason if SAFE_CODE.fullmatch(reason) else (
        "completed" if code == 0 else "experiment_stopped" if marker.is_file() else "offline_acceptance_failed")
    return code == 0


def find_archive(args, ledger, financial):
    roots = (args.wsl_root, args.site.parent, ledger.path.parent)
    with ledger.transaction(maintain=False) as state:
        if args.history_archive is not None:
            financial.confirm_archive(state, args.history_archive, ledger.path.parent)
            return args.history_archive
        for root in dict.fromkeys(roots):
            for directory, names, files in os.walk(root, followlinks=False):
                path = Path(directory)
                names[:] = sorted(name for name in names if not name.startswith(".")
                                  and not name.startswith("checkout-") and name not in {"node_modules", "lib", "Old_Site"})
                if len(path.relative_to(root).parts) >= 6:
                    names.clear()
                if {"go-Q01.json", "ledger.json"} <= set(files):
                    try:
                        financial.confirm_archive(state, path, ledger.path.parent)
                    except ValueError:
                        continue
                    return path
    raise ValueError("confirmed_incident_archive_missing")


def coordinate(args, checkout, work):
    require("microsoft" in os.uname().release.lower(), "trusted_wsl_required")
    check_checkout(checkout, args, git_environment(online=False))
    sys.path.insert(0, str(checkout))
    from ds_dc import dc04b, dc04b_permit as financial
    from ds_dc.corpus import encoded

    ledger = financial.open_ledger(financial.canonical_ledger())
    args.ledger = ledger.path
    previous = dc04b.replay_report(ledger)
    if previous is not None:
        dc04b.write_private(work / "experiment.json", encoded(previous).encode())
        (work / "replayed").touch()
        return 0

    summary, archive = isolated_acceptance(args, checkout, work, ledger, financial)
    if (work / "experiment.json").is_file():
        (work / "replayed").touch()
        return 0

    (work / "execution-started").touch()
    try:
        report = dc04b.execute_prepared(args.site, args.cache, args.commit, ledger,
                                        work / "admission.json", summary, archive)
    except ValueError as error:
        if str(error) != "dc04b_already_reserved":
            raise
        previous = dc04b.replay_report(ledger)
        if previous is not None:
            dc04b.write_private(work / "experiment.json", encoded(previous).encode())
        (work / "replayed").touch()
        return 0
    dc04b.write_private(work / "experiment.json", encoded(report).encode())
    return 0 if report["status"] == "completed" and report["candidate_status"] in {
        "full", "partial", "reference", "needs_support"} else 1


def bundle(destination, work, summary, *, screen=None):
    names = ("offline-summary.json", "offline-checks.json", "experiment.json")
    members = {"summary.json": (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode()}
    members.update({name: (work / name).read_bytes() for name in names if (work / name).is_file()})
    if screen is not None:
        try:
            for raw in members.values():
                screen(raw.decode())
        except ValueError:
            summary["status"] = "report_screening_failed"
            members = {"summary.json": (json.dumps(summary) + "\n").encode()}
    checksums = "".join(f"{sha256(raw).hexdigest()}  {name}\n" for name, raw in members.items())

    destination.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".dc04b-", suffix=".zip", dir=destination)
    os.close(fd)
    staging = Path(temporary)
    report = staging.with_name(staging.name[1:])
    try:
        with zipfile.ZipFile(staging, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in members.items():
                archive.writestr(name, raw)
            archive.writestr("SHA256SUMS", checksums)
        with zipfile.ZipFile(staging) as archive:
            require(archive.testzip() is None and archive.namelist() == [*members, "SHA256SUMS"]
                    and all(sha256(archive.read(name)).digest() == sha256(raw).digest()
                            for name, raw in members.items()), "zip_validation_failed")
        staging.rename(report)
    finally:
        staging.unlink(missing_ok=True)
    return report


def path(value):
    return Path(value).expanduser().absolute()


def main():
    os.umask(0o077)
    sys.dont_write_bytecode = True
    home = Path.home()
    state = home / ".local/state/ds-dc02"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--blob", required=True)
    parser.add_argument("--wsl-root", type=path, default=home / "ds-dc03b-validation")
    parser.add_argument("--site", type=path, default=home / "ds-dc02-cal-validation/Saturn-Main-Site")
    parser.add_argument("--cache", type=path, default=os.environ.get("DS_DC_CACHE"))
    parser.add_argument("--fixture", type=path, default=os.environ.get("DS_DC_Q01_CANDIDATE"))
    parser.add_argument("--python", type=path)
    parser.set_defaults(ledger=state / "ledger")
    parser.add_argument("--history-archive", type=path, default=os.environ.get("DS_DC_ARCHIVE"))
    parser.add_argument("--state", type=path, default=state / "dc04b-launcher")
    parser.add_argument("--output", type=path, default=OUTPUT)
    parser.add_argument("--coordinate-work", type=path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.coordinate_work is not None:
        try:
            return coordinate(args, Path(__file__).resolve().parents[2], args.coordinate_work)
        except (OSError, ValueError, KeyError, TypeError, EOFError, subprocess.SubprocessError,
                KeyboardInterrupt) as error:
            reason = str(error)
            (args.coordinate_work / "failure").write_text(
                reason if SAFE_CODE.fullmatch(reason) else "coordinator_failed", encoding="ascii")
            return 1
    args.output = args.output.resolve()
    summary = dict(task="DS-DC-04B", status="blocked", pin=args.commit if PIN.fullmatch(args.commit) else None,
                   launcher_blob=args.blob if PIN.fullmatch(args.blob) else None, live="LIVE_NOT_RUN",
                   new_provider_operations=0, expert_score="NOT RUN")
    with tempfile.TemporaryDirectory(prefix="dc04b-launch-") as temporary:
        work = Path(temporary)
        screen = None
        try:
            passed = conduct(args, work, summary)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, KeyboardInterrupt) as error:
            summary["status"] = str(error) if isinstance(error, ValueError) and SAFE_CODE.fullmatch(str(error)) else "workflow_failed"
            passed = False
        cached = args.state / ("checkout-" + args.commit) if PIN.fullmatch(args.commit) else None
        if cached and ((work / "offline-summary.json").is_file() or summary["status"] == "replayed"):
            screen = prior_runner(cached).screen
        if summary["status"] == "unsafe_report_directory":
            args.output = OUTPUT
        archive = bundle(args.output, work, summary, screen=screen)
        print(f"DC-04B ZIP: {archive}")
        return 0 if passed and summary["status"] != "report_screening_failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
