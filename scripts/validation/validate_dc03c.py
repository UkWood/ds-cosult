"""One-command DC-03C acceptance. Raw test output stays in a private directory."""
import argparse
import hashlib
import importlib.metadata
import json
import math
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

ROOT = Path(__file__).resolve().parent.parent.parent
BASE = "d3bff92af8fa204b8cc506d1b63154c2e16beef0"
R1_BASE = "4d928d9cdd0dcbb944e82e267b57d34ada2c3ee0"
REMOTE = "https://github.com/UkWood/ds-cosult.git"
REF = "refs/heads/feat/ds-dc-01-document-centric-pilot"
DEFAULT_OUTPUT = Path("/mnt/c/DS-Validation/Reports")
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
PROTECTED_R1 = ("ds_dc/evidence_answer.py", "ds_dc/evidence_extract.py", "ds_dc/evidence_integration.py",
                "ds_dc/structural_pdf.py", "ds_dc/structural_shadow.py", "ds_dc/technical_registry.py",
                "ds_dc/technical_verifier.py")
PDFS = ("030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a",
        "f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f")
CACHE_PDFS = {
    "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a": 3024578,
    "127961f757901dcb6d1292607a930fe8a03b2a3739f2e27f62b792bd53fefbf5": 1033424,
    "496ddc2786b8fb2cdfd8970947fadde6b7a045e7d86e20737f2ef694425d5890": 392090,
    "5eb9f8066e68c659378fcc2d5158cd6dee223e4d02a6035014bed324e4b5356f": 8284454,
    "6860bd9774b3e4e440e3f3bb1635b7fc6c4840612efd96082024cd7588988335": 1481237,
    "83bbf87d653f147c5ce68c8e83c4d31488303ab7376baf1f4a6bcc19d45cbeaa": 767850,
    "944cfc483a6961beefffe948e092f644c15c478d1567bd28ba3d5ce2186bc3ec": 1097018,
    "959f515c588ea8758cae0ccfdd17efaf396b31c84c4315e1b195c745d59db5db": 230917,
    "bf07da30d1221f61a3ecdde5b40f542b90ca2a646c5dc6019997326a2c570148": 167325,
    "c127ed20684fc47e8e5649b27ab91e738d483a04b21d1dbde12b063c512d59e2": 1526778,
    "cf6a52838c40700aac8ee9a0f8bdf81a0811491385dbf00d974c76ed8baa4905": 1326953,
    "e61e8fbcf81f020554c802d23ae05c774d8a7603f0f705089f3f3d4a136e7e89": 5452399,
    "ee407d5d32b26aff28ba193f19788df996cf1d83891ac264da70e51bed75da60": 2438820,
    "f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f": 5017331,
}
ALLOWLIST = ("FINAL-ACCEPTANCE.md", "summary.json", "checks.json", "screening.json", "SHA256SUMS")
PYTHON = sys.executable
R01_CASES = ("R01-A", "R01-B", "R01-B-positive-control", "R01-C1", "R01-C2", "R01-C-applicability-control",
             "unknown-empty-heading", "unknown-merged-geometry", "unknown-empty-value")
MOCK_CASES = ("valid", "different_quantity", "wrong_page", "foreign_source", "wrong_quote", "wrong_field",
              "wrong_request", "wrong_wire", "wrong_revision", "free_answer", "free_extract",
              "duplicate_key", "malformed_item")
MOCK_METRICS = ("manual_expected_retained", "manual_expected_source_extracts", "automated_supported_delivered",
                "automated_source_extracts_delivered", "automated_false_publications", "automated_correct_facts_lost",
                "status_partial", "status_reference", "status_invalid_contract", "status_other")
METRIC_ENUMS = {
    "r01_expected": {"supported", "semantic_pending"},
    "r01_verdict": {"supported", "semantic_pending", "invalid", "contradicted"},
    "r01_reason": {"unproved_quantity_context", "unproved_row_context_or_variant", "verified_quantity",
                   "quote_or_structure_unproved"},
    "mock_actual_status": {"partial", "reference", "invalid_contract", "full", "needs_support",
                           "clarification", "over_cap", "other"},
    "mock_expected_status": {"partial", "reference", "invalid_contract"},
}
NS = ["unshare", "--user", "--map-root-user", "--net", "--",
      "sh", "-c", 'ip link set lo up && exec "$@"', "dc03c"]
PROBE = ("import errno,os,socket; assert os.getenv('DC03C_GUARD_ACTIVE')=='1'; "
         "s=socket.socket(); s.bind(('127.0.0.1',0)); s.listen(); "
         "c=socket.create_connection(s.getsockname()); p,_=s.accept(); p.close(); c.close(); s.close(); "
         "try:\n socket.getaddrinfo('outside.invalid',443)\n"
         "except PermissionError:\n pass\nelse:\n raise AssertionError('guard missed external lookup')")


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(block)
    return checksum.hexdigest()


def sha_of_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(test, code):
    if not test:
        raise ValueError(code)


def git(env, repo, *args, prefix=()):
    command = [*prefix, "git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull,
               "-C", str(repo), *args]
    return subprocess.check_output(command, env=env, stderr=subprocess.DEVNULL, timeout=20).decode().strip()


def junit_counts(path):
    root = ET.parse(path).getroot()
    return dict(tests=len(root.findall(".//testcase")),
                failures=len(root.findall(".//failure")), errors=len(root.findall(".//error")),
                skipped=len(root.findall(".//skipped")))


def junit_evidence(path, *, reviewer=False):
    document = ET.parse(path).getroot()
    rows = []
    for index, item in enumerate(document.findall(".//testcase"), 1):
        duration = float(item.get("time", "0"))
        status, reason = next(((status, reason) for tag, status, reason in (
            ("error", "FAIL", "test_error"), ("failure", "FAIL", "test_failure"),
            ("skipped", "SKIP", "test_skipped")) if item.find(tag) is not None), ("PASS", None))
        row = {"number": index, "duration_ms": round(duration * 1000) if 0 <= duration <= 3600 else None,
               "status": status, "reason": reason}
        if not reviewer:
            name, _, params = item.get("name", "").partition("[")
            if re.fullmatch(r"test_[a-z0-9_]{1,110}", name):
                row["test"] = name
            cases = R01_CASES if name == "test_r01" else MOCK_CASES if name == "test_full_json_mock" else ()
            case = next((case for case in sorted(cases, key=len, reverse=True)
                         if params == case + "]" or params.startswith(case + "-")), None)
            if case:
                row["case"] = case
            metrics = {}
            for prop in item.findall("./properties/property"):
                key, value = prop.get("name"), prop.get("value", "")
                if key in METRIC_ENUMS and value in METRIC_ENUMS[key]:
                    metrics[key] = value
                elif key in (*MOCK_METRICS, "r01_confirmed_count", "r01_expected_supported") and re.fullmatch(
                        r"[0-9]{1,3}", value):
                    metrics[key] = int(value)
            if metrics:
                row["metrics"] = metrics
        rows.append(row)
    return {"cases": rows}


def network_env(root, args):
    # Do not pass developer, API, agent, proxy, Git credentials, or ledger variables.
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL") if key in os.environ}
    env.update(HOME=str(root), TMPDIR=str(root), PYTHONPATH=str(GUARD), PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", PYTHONNOUSERSITE="1", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="",
               DC03C_GUARD_LOG=str(root / "guard.log"), SATURN_SOURCE=str(args.site),
               DS_DC_CACHE=str(args.cache), DS_DC_Q01_CANDIDATE=str(args.fixture),
               SATURN_BKD_PDF=str(args.cache / (PDFS[0] + ".pdf")),
               SATURN_SLD_PDF=str(args.cache / (PDFS[1] + ".pdf")))
    return env


class Run:
    def __init__(self, args, *, preparing=False):
        self.args = args
        self.private = Path(tempfile.mkdtemp(prefix="dc03c-acceptance-"))
        self.env = network_env(self.private, args) if not preparing else None
        self.preparing = preparing
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
        def local(*args):
            return git(self.env, ROOT, *args, prefix=self.prefix)

        require(bool(self.pin), "invalid_external_commit_pin")
        require(local("rev-parse", "HEAD") == self.pin, "checkout_pin_mismatch")
        require(not local("status", "--porcelain", "--untracked-files=all"), "checkout_dirty")
        require(not local("diff", "--name-only", "--no-ext-diff", BASE, "HEAD", "--", *PROTECTED),
                "tracked_protected_files_changed")
        require(not local("diff", "--name-only", "--no-ext-diff", "--diff-filter=MDRT", BASE, "HEAD", "--", "tests"),
                "historical_tests_changed")
        require(not local("diff", "--name-only", "--no-ext-diff", R1_BASE, "HEAD", "--", *PROTECTED_R1),
                "evidence_first_track_changed")
        local("merge-base", "--is-ancestor", BASE, self.pin)

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
        require(git(self.env, self.args.site, "rev-parse", "HEAD", prefix=self.prefix) == SITE, "site_pin_mismatch")
        require(not git(self.env, self.args.site, "status", "--porcelain", "--untracked-files=all", prefix=self.prefix),
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
                report.update(junit_evidence(xml, reviewer=key == "independent_tests"))
            if details and (exit_code == 0 or xml.is_file() and junit or details is child_evidence):
                report.update(details(log))
                if report.get("usefulness_valid") is False:
                    report["failure"] = "mock_usefulness_regression"
                if report.get("passed") is False:
                    report["failure"] = "child_reported_failure"
        except (OSError, ValueError, subprocess.SubprocessError, ET.ParseError) as error:
            reason = str(error)
            report["failure"] = reason if reason in {
                "regression_count_or_skip", "structural_matrix_count", "mock_usefulness_regression",
                "invalid_child_evidence", "missing_child_evidence",
            } else type(error).__name__
        if exit_code not in (None, 0) and "failure" not in report:
            report["failure"] = "child_reported_failure" if "passed" in report else "nonzero_exit"
        if junit and "failure" not in report:
            if "cases" not in report:
                report["failure"] = "missing_junit_report"
            elif not report["tests"]:
                report["failure"] = "empty_junit_report"
            elif report["skipped"]:
                report["failure"] = "unexpected_test_skip"
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
                ("runner_packaging", enabled, pytest("tests/test_dc03c_runner.py", "tests/test_dc03c_r1_acceptance.py"), True, None),
                ("historical_wire_sizing", baseline, child("historical"), False, child_evidence),
                ("pinned_source_probe", baseline, child("new-wire"), False, safe_object),
                ("authentic_q01_shadow", baseline and fixture,
                 child("authentic"), False, child_evidence),
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
        result = {"task": "DS-DC-03C-R1", "environment": self.env_name, "pin": self.pin,
                  "site_pin": SITE, "isolation": self.isolation, "status": "PASS" if passed else "FAIL",
                  "checks": {key: step["status"] for key, step in self.steps.items()}}
        header = [f'# DS-DC-03C-R1 · Final Acceptance · {result["status"]}', "",
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
        protected = (self.args.site, self.args.cache) if self.preparing else (ROOT, self.args.site, self.args.cache)
        require(not any(path and self.args.output.is_relative_to(path) for path in protected), "unsafe_report_directory")
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
    require(counts["tests"] >= 273 and not counts["skipped"], "regression_count_or_skip")
    return {}


def structural_matrix(log):
    require(junit_counts(log.with_suffix(".xml"))["tests"] == 22, "structural_matrix_count")
    return {"expected_positive_cases": 4, "expected_negative_cases": 18}


def usefulness(log):
    report = dict.fromkeys(MOCK_METRICS, 0)
    root = ET.parse(log.with_suffix(".xml")).getroot()
    for item in root.findall(".//property"):
        value = item.get("value", "")
        if item.get("name") in report and re.fullmatch(r"[0-9]{1,3}", value):
            report[item.get("name")] += int(value)
    report["usefulness_valid"] = (
        report["manual_expected_retained"] > 0 and report["manual_expected_source_extracts"] > 0
        and report["manual_expected_retained"] == report["automated_supported_delivered"]
        and report["manual_expected_source_extracts"] == report["automated_source_extracts_delivered"]
        and report["automated_false_publications"] == report["automated_correct_facts_lost"] == 0)
    return report


def safe_object(log):
    data = json.loads(log.read_text())
    # Subprocess reports contain only fixed result keys and scalar measurements.
    require(isinstance(data, dict) and all(re.fullmatch(r"[a-z][a-z0-9_]{0,45}", key) and
            (type(value) in (bool, int) and (type(value) is bool or 0 <= value <= 10**9)
             or isinstance(value, str) and re.fullmatch(r"[a-z0-9_-]{1,64}", value))
            for key, value in data.items()), "invalid_child_summary")
    return data


def child_evidence(log):
    try:
        data = json.loads(log.read_text())
    except ValueError as error:
        raise ValueError("missing_child_evidence") from error

    def safe(value, depth=0):
        if depth > 10:
            return False
        if isinstance(value, dict):
            return len(value) <= 48 and all(re.fullmatch(r"[a-z][a-z0-9_]{0,48}", key)
                                            and safe(item, depth + 1) for key, item in value.items())
        if isinstance(value, list):
            return len(value) <= 32 and all(safe(item, depth + 1) for item in value)
        if isinstance(value, str):
            return bool(re.fullmatch(r"[a-z0-9_.-]{1,64}", value))
        return value is None or type(value) is bool or (
            type(value) in (int, float) and math.isfinite(value) and abs(value) <= 10**9)

    require(isinstance(data, dict) and type(data.get("passed")) is bool and safe(data), "invalid_child_evidence")
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


def prep_environment():
    # HTTPS Git transport is enabled only during preparation, with no inherited
    # credentials, global config, Git rewrite rules, hooks, or private runtime variables.
    return {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0", "GIT_ALLOW_PROTOCOL": "https"}


def unique_input(paths, name):
    found = set(paths)
    require(bool(found), name + "_not_found")
    require(len(found) == 1, name + "_ambiguous")
    return found.pop()


def discover_materials(root, args, env):
    result = {key: getattr(args, key) for key in ("site", "cache", "fixture", "python")}
    wanted = {key for key, path in result.items() if path is None}
    candidates = {key: [] for key in wanted}
    if wanted:
        require(root.is_dir(), "validation_root_not_found")
        skipped = {".git", "__pycache__", ".pytest_cache", "node_modules", "Old_Site", "site-packages"}
        for count, (directory, subdirs, files) in enumerate(os.walk(root, followlinks=False), 1):
            require(count <= 8192, "validation_discovery_limit")
            path = Path(directory)
            if len(path.relative_to(root).parts) >= 6 or "pyvenv.cfg" in files:
                subdirs[:] = []
            else:
                is_repo = ".git" in files or ".git" in subdirs
                subdirs[:] = sorted(name for name in subdirs if name not in skipped)
                if is_repo:
                    if "site" in wanted:
                        try:
                            if (git(env, path, "rev-parse", "HEAD") == SITE
                                    and not git(env, path, "status", "--porcelain", "--untracked-files=all")):
                                candidates["site"].append(path)
                        except (OSError, subprocess.SubprocessError):
                            pass
            if "cache" in wanted and {"audit.json", TOKENIZER_FILE} <= set(files):
                originals = [(path / (sha + ".pdf"), size, sha) for sha, size in CACHE_PDFS.items()]
                if (all(file.is_file() and file.stat().st_size == size for file, size, _ in originals)
                        and digest(path / TOKENIZER_FILE) == TOKENIZER
                        and all(digest(file) == sha for file, _, sha in originals)):
                    candidates["cache"].append(path)
            if "python" in wanted and "pyvenv.cfg" in files:
                config = (path / "pyvenv.cfg").read_text(encoding="utf-8")
                python = path / "bin" / "python"
                if re.search(r"^version\s*=\s*3\.12(?:\.\d+)?\s*$", config, re.M) and python.is_file():
                    candidates["python"].append(python)
            if "fixture" in wanted:
                for name in files:
                    file = path / name
                    if (name.endswith(".json") and not file.is_symlink() and file.is_file()
                            and file.stat().st_size == 5188 and digest(file) == FIXTURE):
                        candidates["fixture"].append(file)
        # Collect all missing/ambiguous material types at once.
        problems = {}
        for key in sorted(wanted):
            try:
                result[key] = unique_input(candidates[key], key)
            except ValueError as error:
                problems[key] = str(error)
    else:
        problems = {}
    for key, path in result.items():
        if path is not None:
            present = path.is_dir() if key in {"site", "cache"} else path.is_file()
            if not present:
                problems[key] = key + "_not_found"
    return result, problems


def prepare_checkout(path, pin, env):
    def call(*args):
        subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-C", str(path), *args],
                       env=env, timeout=180, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    path.mkdir()
    try:
        call("init", "--quiet", "--template=")
        call("fetch", "--quiet", "--no-tags", "--no-recurse-submodules", REMOTE, REF)
    except (OSError, subprocess.SubprocessError) as error:
        if isinstance(getattr(error, "stderr", None), bytes):
            (path.parent / "git-preparation.stderr").write_bytes(error.stderr)
        raise ValueError("draft_checkout_fetch_failed") from error
    for ancestor, tip, reason in ((pin, "FETCH_HEAD", "commit_not_in_draft_branch"),
                                  (R1_BASE, pin, "commit_not_after_r1_baseline")):
        try:
            call("merge-base", "--is-ancestor", ancestor, tip)
        except subprocess.CalledProcessError as error:
            raise ValueError(reason) from error
    require(pin != R1_BASE, "commit_not_after_r1_baseline")
    call("checkout", "--quiet", "--detach", pin)
    require(git(env, path, "rev-parse", "HEAD") == pin, "prepared_checkout_pin_mismatch")
    require(not git(env, path, "status", "--porcelain", "--untracked-files=all"), "prepared_checkout_dirty")


def finish(run, passed):
    print(f"Private diagnostics: {run.private}")
    try:
        archive = run.package(passed)
        if run.args.receipt:
            run.args.receipt.write_text(str(archive), encoding="utf-8")
        print(f"Acceptance ZIP: {archive}")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        (run.private / "packaging-error.log").write_text(repr(error) + "\n")
        print(f"Report transfer failed ({str(error) if isinstance(error, ValueError) else type(error).__name__}).")
        return 1
    return 0 if passed else 1


def prepare(args):
    run = Run(args, preparing=True)
    env = prep_environment()
    report = run.private / "preparation.json"
    receipt = run.private / "receipt"
    checkout = run.private / "checkout"
    try:
        valid_pin = run.inspect("preparation_pin", lambda: require(run.pin, "invalid_external_commit_pin"))
        started = time.monotonic()
        materials, problems = discover_materials(args.wsl_root, args, env)
        for key, path in materials.items():
            if path:
                setattr(args, key, path)
        ready = run.record("preparation_inputs", "FAIL" if problems else "PASS",
                           time.monotonic() - started, 1 if problems else 0, issues=problems)
        if not valid_pin or not ready:
            run.record("preparation_checkout", "BLOCKED")
            run.record("acceptance_runner", "BLOCKED")
            return finish(run, False)
        if not run.inspect("preparation_checkout", lambda: prepare_checkout(checkout, run.pin, env)):
            run.record("acceptance_runner", "BLOCKED")
            return finish(run, False)
        write_json(report, run.steps)
        child_path = checkout / "scripts/validation/validate_dc03c.py"
        command = [str(args.python), "-I", str(child_path), "--commit", run.pin,
                   "--site", str(args.site), "--cache", str(args.cache), "--fixture", str(args.fixture),
                   "--output", str(args.output), "--network", args.network,
                   "--preparation-record", str(report), "--receipt", str(receipt)]
        for flag, values in (("--extra-tests", args.extra_tests), ("--protected-file", args.protected_file)):
            for value in values:
                command.extend([flag, str(value)])
        # Keep proxy and credential settings used for Git out of the acceptance phase.
        code = subprocess.run(command, cwd=checkout, env={"PATH": env["PATH"], "LANG": env["LANG"]}).returncode
        if receipt.is_file():
            return code
        run.record("acceptance_runner", "FAIL", exit_code=code, reason="runner_did_not_produce_archive")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        (run.private / "preparation-error.log").write_text(repr(error) + "\n")
        label = "preparation_inputs" if "preparation_inputs" not in run.steps else "acceptance_runner"
        known = {"validation_root_not_found", "validation_discovery_limit"}
        run.record(label, "FAIL", exit_code=1,
                   reason=str(error) if str(error) in known else type(error).__name__)
        if label == "preparation_inputs":
            run.record("preparation_checkout", "BLOCKED")
            run.record("acceptance_runner", "BLOCKED")
    return finish(run, False)


def input_path(text):
    return Path(text).expanduser().absolute()


def preparation_evidence(path, pin, environment):
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"preparation_pin", "preparation_inputs", "preparation_checkout"}
    require(type(data) is dict and data.keys() == required, "invalid_preparation_record")
    for name, step in data.items():
        keys = {"pin", "environment", "status", "duration_ms", "exit_code"}
        if name == "preparation_inputs":
            keys.add("issues")
        require(type(step) is dict and step.keys() == keys and step.get("pin") == pin
                and step.get("environment") == environment and step.get("status") == "PASS"
                and type(step.get("exit_code")) is int and step["exit_code"] == 0
                and type(step.get("duration_ms")) is int and 0 <= step["duration_ms"] <= 10**9
                and step.get("issues", {}) == {}, "invalid_preparation_record")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--wsl-root", type=input_path, default=Path.home() / "ds-dc03b-validation")
    parser.add_argument("--output", type=lambda text: input_path(text).resolve(), default=DEFAULT_OUTPUT)
    for name in ("site", "cache", "fixture"):
        parser.add_argument("--" + name, type=lambda text: input_path(text).resolve())
    parser.add_argument("--python", type=input_path, help="Python interpreter in the prepared 3.12 environment")
    parser.add_argument("--extra-tests", action="append", default=[], type=lambda text: input_path(text).resolve())
    parser.add_argument("--protected-file", action="append", default=[], type=lambda text: input_path(text).resolve())
    parser.add_argument("--network", choices=("auto", "namespace", "python"), default="auto")
    parser.add_argument("--preparation-record", type=input_path, help=argparse.SUPPRESS)
    parser.add_argument("--receipt", type=input_path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.prepare:
        for key, var in (("site", "SATURN_SOURCE"), ("cache", "DS_DC_CACHE"), ("fixture", "DS_DC_Q01_CANDIDATE")):
            if getattr(args, key) is None and os.environ.get(var):
                setattr(args, key, input_path(os.environ[var]).resolve())
        return prepare(args)
    if not all((args.site, args.cache, args.fixture)):
        parser.error("use --prepare or provide --site, --cache and --fixture")
    run = Run(args)
    try:
        if args.preparation_record:
            run.steps.update(preparation_evidence(args.preparation_record, run.pin, run.env_name))
        passed = run.run()
    except Exception as error:
        (run.private / "runner-error.log").write_text(repr(error) + "\n")
        run.record("runner", "FAIL", reason=type(error).__name__)
        passed = False
    return finish(run, passed)


if __name__ == "__main__":
    raise SystemExit(main())
