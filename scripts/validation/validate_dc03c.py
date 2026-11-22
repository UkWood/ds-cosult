"""One-command DC-03C acceptance. Raw test output stays in a private directory."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = "d3bff92af8fa204b8cc506d1b63154c2e16beef0"
SITE = "084d759487bfab6e111549c9b5469711ac5fc13e"
FIXTURE = "ae646fb4ae9d3b83c22edc9717b4d8ddb0ef228ac54b9f5a1aec222bcb24cb26"
TOKENIZER = "81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99"
TOKENIZER_FILE = "deepseek-v41-tokenizer.json"
MANIFEST = "13fd98159f05809c019dd11a522b1c87fff3faebc505621bde7318880e3051f9"
REPORTS = ROOT / "docs/reports/ds-dc-02"
GUARD = Path(__file__).resolve().parent / "dc03c-offline"
PROTECTED = ("requirements.txt", "requirements-dev.txt", "ds_dc/context.py", "ds_dc/runtime.py",
             "ds_dc/native.py", "ds_dc/finance.py",
             "ds_dc/recovery.py", "ds_dc/owner_web.py", "ds_dc/candidate_fixture.py",
             "ds_dc/evidence_lab.py", "ds_pilot", "tests/test_structural_evidence.py",
             "docs/runbooks/ds-dc-02", "docs/reports/ds-dc-02", "docs/runbooks/ds-dc-03b")
PDFS = ("030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a",
        "f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f")
ALLOWLIST = ("FINAL-ACCEPTANCE.md", "summary.json", "checks.json", "screening.json", "SHA256SUMS")
PYTHON = sys.executable
NS = ["unshare", "--user", "--map-root-user", "--net", "--",
      "sh", "-c", 'ip link set lo up && exec "$@"', "dc03c"]
PROBE = ("import errno,os,socket; assert os.getenv('DC03C_GUARD_ACTIVE')=='1'; "
         "s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(); "
         "c=socket.create_connection(s.getsockname()); p,_=s.accept(); p.close(); c.close(); s.close(); "
         "try:\n socket.getaddrinfo('outside.invalid',443)\n"
         "except PermissionError:\n pass\nelse:\n raise AssertionError('guard missed external lookup')")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def sha_of_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(test, code):
    if not test:
        raise ValueError(code)


def git(env, repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env,
                                   stderr=subprocess.DEVNULL, timeout=20).decode().strip()


def junit_counts(path):
    root = ET.parse(path).getroot()
    return dict(tests=len(root.findall(".//testcase")),
                failures=len(root.findall(".//failure")), errors=len(root.findall(".//error")),
                skipped=len(root.findall(".//skipped")))


def network_env(root, args):
    # Do not pass developer, API, agent, proxy, Git credentials, or ledger variables.
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
    env.update(HOME=str(root), TMPDIR=str(root), PYTHONPATH=str(GUARD), PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONNOUSERSITE="1", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
               DC03C_GUARD_LOG=str(root / "guard.log"), SATURN_SOURCE=str(args.site),
               DS_DC_CACHE=str(args.cache), DS_DC_Q01_CANDIDATE=str(args.fixture),
               SATURN_BKD_PDF=str(args.cache / (PDFS[0] + ".pdf")),
               SATURN_SLD_PDF=str(args.cache / (PDFS[1] + ".pdf")))
    return env


class Run:
    def __init__(self, args):
        self.args = args
        self.private = Path(tempfile.mkdtemp(prefix="dc03c-acceptance-"))
        self.env = network_env(self.private, args)
        self.pin = args.commit if re.fullmatch(r"[0-9a-f]{40}", args.commit) else None
        self.env_name = "WSL" if "microsoft" in os.uname().release.lower() else "Linux"
        self.isolation = "not_run"
        self.steps = {}
        self.prefix = []

    def record(self, key, status, elapsed=0, exit_code=None, **details):
        self.steps[key] = dict(status=status, exit_code=exit_code, duration_ms=round(elapsed * 1000),
                               environment=self.env_name, pin=self.pin, **details)
        return status == "PASS"

    def inspect(self, name, action):
        started = time.monotonic()
        try:
            details = action() or {}
        except (OSError, ValueError, subprocess.SubprocessError, KeyError, TypeError) as error:
            # Only internal short reason codes enter the shareable report.
            (self.private / f"{name}.log").write_text(repr(error) + "\n")
            code = str(error)
            return self.record(name, "FAIL", time.monotonic() - started, 1,
                               reason=code if re.fullmatch(r"[a-z][a-z0-9_]{0,60}", code)
                               else type(error).__name__)
        return self.record(name, "PASS", time.monotonic() - started, 0, **details)

    def checkout(self):
        require(bool(self.pin), "invalid_external_commit_pin")
        require(git(self.env, ROOT, "rev-parse", "HEAD") == self.pin, "checkout_pin_mismatch")
        require(not git(self.env, ROOT, "status", "--porcelain", "--untracked-files=all"), "checkout_dirty")
        require(not git(self.env, ROOT, "diff", "--name-only", BASE, "HEAD", "--", *PROTECTED),
                "tracked_protected_files_changed")
        require(not git(self.env, ROOT, "diff", "--name-only", "--diff-filter=MDRT", BASE, "HEAD", "--", "tests"),
                "historical_tests_changed")
        subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", BASE, self.pin],
                       env=self.env, check=True, timeout=20, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def dependencies(self):
        require(sys.version_info[:2] == (3, 12), "python_312_required")
        for program in ("git", "prlimit", "pdftotext", "pdfinfo"):
            require(shutil.which(program, path=self.env["PATH"]), "local_binary_missing")
        files = [ROOT / "requirements.txt", ROOT / "requirements-dev.txt"]
        for path in files:
            for line in path.read_text().splitlines():
                if "==" in line and not line.lstrip().startswith("#"):
                    name, expected = line.strip().split("==")
                    require(importlib.metadata.version(name) == expected, "dependency_pin_mismatch")
        return {"python": ".".join(map(str, sys.version_info[:3]))}

    def offline(self):
        probe = self.env | {"DC03C_GUARD_PROBE": "1"}
        program = PROBE.replace("try:\n", "\ntry:\n")
        with (self.private / "network.log").open("wb") as log:
            if self.args.network != "python" and shutil.which("unshare") and shutil.which("ip"):
                try:
                    result = subprocess.run(NS + [PYTHON, "-c", program], env=probe, timeout=10,
                                            stdout=log, stderr=log)
                    if result.returncode == 0:
                        self.prefix = NS
                        self.isolation = "linux_network_namespace_plus_python_socket_audit"
                except (OSError, subprocess.TimeoutExpired):
                    pass
            if not self.prefix:
                require(self.args.network != "namespace", "network_namespace_unavailable")
                subprocess.run([PYTHON, "-c", program], env=probe, timeout=10, check=True,
                               stdout=log, stderr=log)
                self.isolation = "python_socket_audit_only"
        return {"isolation": self.isolation}

    def pinned_site(self):
        require(git(self.env, self.args.site, "rev-parse", "HEAD") == SITE, "site_pin_mismatch")
        require(not git(self.env, self.args.site, "status", "--porcelain", "--untracked-files=all"),
                "site_checkout_dirty")

    def frozen_materials(self):
        manifest = json.loads((REPORTS / "corpus-manifest.json").read_text())
        canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        require(sha_of_bytes(canonical) == MANIFEST and manifest["site_commit"] == SITE, "stored_freeze_mismatch")
        require(digest(self.args.cache / TOKENIZER_FILE) == TOKENIZER, "local_tokenizer_mismatch")
        require((self.args.cache / "audit.json").is_file(), "cache_receipts_missing")
        for doc in manifest["files"]:
            path = self.args.cache / (doc["sha256"] + ".pdf")
            require(path.stat().st_size == doc["bytes"] and digest(path) == doc["sha256"], "pdf_original_mismatch")
            result = subprocess.check_output(self.prefix + ["prlimit", "--as=536870912", "--cpu=15", "--",
                                             "pdfinfo", str(path)], env=self.env, stderr=subprocess.DEVNULL,
                                             timeout=20)
            found = re.search(rb"^Pages:\s+(\d+)", result, re.M)
            require(found and int(found[1]) == doc["pages"], "physical_page_count_mismatch")
        return dict(pdf_files=len(manifest["files"]), physical_pages=sum(d["pages"] for d in manifest["files"]),
                    manifest_sha256=MANIFEST)

    def authentic(self):
        require(self.args.fixture.stat().st_size == 5188 and digest(self.args.fixture) == FIXTURE,
                "authentic_fixture_mismatch")
        return {"fixture_sha256": FIXTURE, "bytes": 5188}

    def sealed_materials(self, frozen, fixture):
        paths = list(self.args.protected_file)
        if frozen:
            manifest = json.loads((REPORTS / "corpus-manifest.json").read_text())
            paths.extend(self.args.cache / (doc["sha256"] + ".pdf") for doc in manifest["files"])
            paths.extend(self.args.cache / key for key in (TOKENIZER_FILE, "audit.json", "preflight.json")
                         if (self.args.cache / key).is_file())
        if fixture:
            paths.append(self.args.fixture)
        return {path: digest(path) for path in paths}

    def command(self, key, arguments, *, junit=False, details=None):
        started = time.monotonic()
        log = self.private / f"{key}.log"
        xml = self.private / f"{key}.xml"
        exit_code = None
        report = {}
        try:
            with log.open("wb") as stream:
                proc = subprocess.run(self.prefix + arguments + (["--junitxml", str(xml)] if junit else []),
                                      cwd=ROOT, env=self.env, stdout=stream, stderr=subprocess.STDOUT,
                                      timeout=600)
            exit_code = proc.returncode
            if junit and xml.is_file():
                report.update(junit_counts(xml))
            if details and exit_code == 0:
                report.update(details(log))
        except (OSError, ValueError, subprocess.SubprocessError, ET.ParseError) as error:
            report["failure"] = type(error).__name__
        passed = exit_code == 0 and "failure" not in report and (
            not junit or report.get("tests", 0) > 0 and not report.get("skipped"))
        return self.record(key, "PASS" if passed else "FAIL", time.monotonic() - started, exit_code, **report)

    def run(self):
        code = self.inspect("checkout", self.checkout)
        deps = self.inspect("dependencies", self.dependencies)
        network = self.inspect("offline_network", self.offline) if deps else self.record("offline_network", "BLOCKED")
        site = self.inspect("pinned_site", self.pinned_site)
        frozen = self.inspect("frozen_originals", self.frozen_materials) if network and code else self.record(
            "frozen_originals", "BLOCKED")
        fixture = self.inspect("authentic_fixture", self.authentic)
        starting = {}

        def seal():
            nonlocal starting
            starting = self.sealed_materials(frozen, fixture)
            return {"checked_files": len(starting)}

        sealed = self.inspect("initial_material_checksums", seal)
        enabled = code and deps and network and sealed
        baseline = (self.command("canonical_freeze", child("freeze"), details=safe_object)
                    if enabled and site and frozen else self.record("canonical_freeze", "BLOCKED"))
        jobs = [("historical_matrix", enabled, [PYTHON, "-m", "ds_dc.evidence_lab", "matrix"], False, matrix),
                ("structural_matrix", enabled, pytest("tests/test_structural_evidence.py", "-k",
                    "test_structural_numeric_values or test_numeric_mutations or test_troubleshooting_links"),
                 True, structural_matrix),
                ("v2_r01_provenance", enabled, pytest("tests/test_dc03c.py", "-k",
                    "not test_pinned_site_function_without_pdf_gate"), True, usefulness),
                ("pinned_site_source_identity", enabled and site,
                 pytest("tests/test_dc03c.py::test_pinned_site_function_without_pdf_gate"), True, None),
                ("runner_packaging", enabled, pytest("tests/test_dc03c_runner.py"), True, None),
                ("historical_wire_sizing", baseline, child("historical"), False, safe_object),
                ("pinned_source_probe", baseline, child("new-wire"), False, safe_object),
                ("authentic_q01_shadow", baseline and fixture,
                 child("authentic"), False, safe_object),
                ("full_regression", baseline and fixture, pytest("tests"), True, regression)]
        for key, ready, command, junit, details in jobs:
            if ready:
                self.command(key, command, junit=junit, details=details)
            else:
                self.record(key, "BLOCKED")
        if self.args.extra_tests and baseline:
            self.command("independent_tests", pytest(*map(str, self.args.extra_tests)), junit=True)
        else:
            self.record("independent_tests", "BLOCKED" if self.args.extra_tests else "NOT RUN",
                        optional=not self.args.extra_tests)

        def unchanged():
            require(all(digest(path) == sha for path, sha in starting.items()), "protected_material_changed")
            site and self.pinned_site()
            return {"checked_files": len(starting)}

        self.inspect("final_material_checksums", unchanged) if sealed else self.record(
            "final_material_checksums", "BLOCKED")
        self.inspect("final_checkout", self.checkout) if code else self.record("final_checkout", "BLOCKED")

        def no_requests():
            log = self.private / "guard.log"
            count = len(log.read_bytes().splitlines()) if log.exists() else 0
            require(count == 0, "unexpected_external_python_socket_attempt")
            return {"blocked_python_socket_operations": count,
                    "provider_network": "blocked" if self.prefix else "python_socket_guard",
                    "external_network_sandbox": bool(self.prefix)}

        if network:
            self.inspect("offline_audit", no_requests)
        else:
            self.record("offline_audit", "BLOCKED")
        return all(step["status"] == "PASS" or step.get("optional") for step in self.steps.values())

    def package(self, passed):
        result = {"task": "DS-DC-03C", "environment": self.env_name, "pin": self.pin,
                  "site_pin": SITE, "isolation": self.isolation, "status": "PASS" if passed else "FAIL",
                  "checks": {key: step["status"] for key, step in self.steps.items()}}
        header = [f'# DS-DC-03C · Final Acceptance · {result["status"]}', "",
                  f"- Environment: {self.env_name}", f"- Checkout pin: {self.pin or 'unavailable'}",
                  f"- Isolation: {self.isolation}", "", "| Check | Status | Exit | Milliseconds |",
                  "|---|---|---:|---:|"]
        rows = [f'| {key} | {row["status"]} | {row["exit_code"]} | {row["duration_ms"]} |'
                for key, row in self.steps.items()]
        (self.private / ALLOWLIST[0]).write_text("\n".join(header + rows) + "\n", encoding="utf-8")
        write_json(self.private / ALLOWLIST[1], result)
        write_json(self.private / ALLOWLIST[2], self.steps)
        write_json(self.private / ALLOWLIST[3], {"included": list(ALLOWLIST),
            "excluded": ["raw command output", "raw JUnit", "source documents and original fixtures",
                         "private operational records", "local paths and machine metadata"],
            "method": "explicit allowlist of generated summaries, forbidden-pattern scan, CRC and SHA-256"})
        sums = "".join(f"{digest(self.private / name)}  {name}\n" for name in ALLOWLIST[:-1])
        (self.private / ALLOWLIST[4]).write_text(sums, encoding="ascii")
        for name in ALLOWLIST:
            screen((self.private / name).read_text(encoding="utf-8"))
        fd, filename = tempfile.mkstemp(prefix="dc03c-", suffix=".zip", dir=self.private)
        os.close(fd)
        archive = Path(filename)
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            for name in ALLOWLIST:
                output.write(self.private / name, name)
        verify_archive(archive)
        require(not any(self.args.output.is_relative_to(path)
                        for path in (ROOT, self.args.site, self.args.cache)), "unsafe_report_directory")
        self.args.output.mkdir(parents=True, exist_ok=True)
        fd, staged = tempfile.mkstemp(prefix=".dc03c-", dir=self.args.output)
        os.close(fd)
        staged = Path(staged)
        try:
            shutil.copyfile(archive, staged)
            require(digest(archive) == digest(staged), "zip_copy_sha_mismatch")
            verify_archive(staged)
            destination = self.args.output / archive.name
            require(not destination.exists(), "report_name_collision")
            staged.rename(destination)
        finally:
            staged.unlink(missing_ok=True)
        return destination


def pytest(*args):
    return [PYTHON, "-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider",
            "-o", "junit_family=xunit1", *args]


def child(name):
    return [PYTHON, "-m", "ds_dc.validation_dc03c", name]


def matrix(log):
    data = json.loads(log.read_text())
    require(len(data) == 12 and all(row["expected"] == row["actual"] for row in data), "historical_matrix_mismatch")
    return {"cases": 12, "passed": 12}


def regression(log):
    counts = junit_counts(log.with_suffix(".xml"))
    require(counts["tests"] >= 230 and not counts["skipped"], "regression_count_or_skip")
    return {}


def structural_matrix(log):
    require(junit_counts(log.with_suffix(".xml"))["tests"] == 22, "structural_matrix_count")
    return {"expected_positive_cases": 4, "expected_negative_cases": 18}


def usefulness(log):
    properties = ("manual_expected_retained", "manual_expected_source_extracts", "automated_supported_delivered",
                  "automated_source_extracts_delivered", "automated_false_publications",
                  "automated_correct_facts_lost", "status_partial", "status_reference", "status_invalid_contract")
    report = dict.fromkeys(properties, 0)
    root = ET.parse(log.with_suffix(".xml")).getroot()
    for item in root.findall(".//property"):
        if item.get("name") in report:
            report[item.get("name")] += int(item.get("value"))
    require(report["manual_expected_retained"] > 0 and report["manual_expected_source_extracts"] > 0
            and report["manual_expected_retained"] == report["automated_supported_delivered"]
            and report["manual_expected_source_extracts"] == report["automated_source_extracts_delivered"]
            and report["automated_false_publications"] == report["automated_correct_facts_lost"] == 0,
            "mock_usefulness_regression")
    return report


def safe_object(log):
    data = json.loads(log.read_text())
    # Subprocess reports contain only fixed result keys and scalar measurements.
    require(isinstance(data, dict) and all(re.fullmatch(r"[a-z][a-z0-9_]{0,45}", key) and
            (type(value) in (bool, int) and (type(value) is bool or 0 <= value <= 10**9)
             or isinstance(value, str) and re.fullmatch(r"[a-z0-9_-]{1,64}", value))
            for key, value in data.items()), "invalid_child_summary")
    return data


def screen(content):
    pattern = (r"(?i)file-api-|\bsk-[a-z0-9_-]{8,}|bearer\s+\S+|private key|"
               r"[\w.+%-]+@[\w.-]+\.[a-z]{2,}|(?:[a-z]:[\\/]|/(?:mnt|workspace|tmp|home|users)/)|"
               r"(?<![\d.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![\d.])|"
               r"\b[0-9a-f]{0,4}:(?:[0-9a-f]{0,4}:){2,}[0-9a-f]{0,4}\b")
    match = re.search(pattern, content)
    if match:
        raise ValueError("screening_forbidden_pattern")


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        require(tuple(archive.namelist()) == ALLOWLIST and archive.testzip() is None, "zip_crc_or_members")
        expected = "".join(f"{sha_of_bytes(archive.read(name))}  {name}\n" for name in ALLOWLIST[:-1])
        require(archive.read("SHA256SUMS").decode() == expected, "zip_member_sha_mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    for name in ("site", "cache", "fixture", "output"):
        parser.add_argument("--" + name, required=True, type=lambda text: Path(text).resolve())
    parser.add_argument("--extra-tests", action="append", default=[], type=lambda text: Path(text).resolve())
    parser.add_argument("--protected-file", action="append", default=[], type=lambda text: Path(text).resolve())
    parser.add_argument("--network", choices=("auto", "namespace", "python"), default="auto")
    run = Run(parser.parse_args())
    try:
        passed = run.run()
    except Exception as error:
        (run.private / "runner-error.log").write_text(repr(error) + "\n")
        run.record("runner", "FAIL", reason=type(error).__name__)
        passed = False
    print(f"Private diagnostics: {run.private}")
    try:
        print(f"Acceptance ZIP: {run.package(passed)}")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        (run.private / "packaging-error.log").write_text(repr(error) + "\n")
        print(f"Report transfer failed ({str(error) if isinstance(error, ValueError) else type(error).__name__}).")
        return 1
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
