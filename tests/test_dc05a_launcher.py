"""Acceptance launcher behavior without accessing a provider or owner history."""

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc05a.py"
MEMBERS = (
    "summary.json", "checks.json", "integrity.json", "ui-pipeline-feedback.json", "report.md", "SHA256SUMS",
)


def launcher():
    spec = importlib.util.spec_from_file_location("dc05a_acceptance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invalid_pin_leaves_one_checked_blocked_zip_without_echoing_input(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--commit", "/tmp/not-for-export", "--blob", "0" * 40,
         "--output", str(tmp_path)],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=20,
    )
    assert result.returncode == 2
    archive_path, = tmp_path.iterdir()
    with zipfile.ZipFile(archive_path) as archive:
        assert tuple(archive.namelist()) == MEMBERS
        assert archive.testzip() is None
        expected = "".join(f"{sha256(archive.read(name)).hexdigest()}  {name}\n" for name in MEMBERS[:-1])
        assert archive.read("SHA256SUMS").decode("ascii") == expected
        summary = json.loads(archive.read("summary.json"))
        assert summary["status"] == "BLOCKED"
        assert summary["failure_code"] == "invalid_launch_pin"
        assert summary["new_provider_operations"] == summary["new_cost_micro_usd"] == 0
        assert summary["operations"]["key_prompts"] == 0
        assert summary["live"] == "LIVE_NOT_RUN"
        assert b"not-for-export" not in b"".join(archive.read(member) for member in MEMBERS)
    assert b"not-for-export" not in result.stdout + result.stderr


@pytest.mark.parametrize("change", [
    b":100644 100644 d05a55 e922d9 M\0ds_dc/finance.py\0",
    b":100644 100644 d05a55 e922d9 M\0ds_dc/dc04b_r1_replay.py\0",
    b":100644 100644 d05a55 e922d9 M\0tests/test_dc04b_r1_replay.py\0",
    b":000000 120000 000000 e922d9 A\0ds_dc/trial_provider.py\0",
    b":000000 100644 000000 e922d9 A\0docs/reports/DS-DC-05A-RAW.md\0",
])
def test_scope_rejects_historical_writes_symlinks_and_raw_evidence(change):
    with pytest.raises(ValueError, match="scope"):
        launcher().validate_scope(change)


def test_scope_recognizes_regular_new_trial_code_and_one_compatible_seam():
    assert launcher().validate_scope(
        b":100644 100644 d05a55 e922d9 M\0ds_dc/evidence_integration.py\0"
        b":000000 100644 000000 e922d9 A\0ds_dc/trial_provider.py\0"
    ) == {"ds_dc/evidence_integration.py": "M", "ds_dc/trial_provider.py": "A"}


def test_r1_archive_refuses_substituted_pass_summary(tmp_path):
    archive_path = tmp_path / "substituted.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("summary.json", '{"status":"PASS"}')
    with pytest.raises(ValueError, match="r1_archive_digest_mismatch"):
        launcher().verify_r1_archive(archive_path)


def test_result_validates_retained_case_counts_per_historical_test(tmp_path):
    junit = tmp_path / "results.xml"
    junit.write_text(
        '<testsuites><testsuite>'
        '<testcase classname="tests.test_historical" name="test_history[0]"/>'
        '<testcase classname="tests.test_dc05a_pipeline" name="test_history[1]"/>'
        '</testsuite></testsuites>',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="historical_test_cases_changed"):
        launcher().verify_test_cases(junit, {"test_history": 2})


def test_internal_worker_cannot_write_outside_isolation(tmp_path):
    result = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), "--isolated", str(tmp_path)],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=20,
    )
    assert result.returncode == 2
    assert not list(tmp_path.iterdir())


def test_internal_worker_with_isolation_requires_parent_workspace(tmp_path, monkeypatch):
    import os

    module = launcher()
    monkeypatch.setattr(module, "ensure_isolated", lambda: None)
    monkeypatch.delenv(module.WORKSPACE_FD, raising=False)
    assert module.isolated(tmp_path, prepared=False) == 2
    assert not list(tmp_path.iterdir())

    other = tmp_path.parent
    fd = os.open(other, os.O_RDONLY | os.O_DIRECTORY)
    try:
        monkeypatch.setenv(module.WORKSPACE_FD, str(fd))
        assert module.isolated(tmp_path, prepared=True) == 2
        assert not list(tmp_path.iterdir())
    finally:
        os.close(fd)
