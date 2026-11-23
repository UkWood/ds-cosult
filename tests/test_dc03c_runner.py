"""The acceptance packager is exercised without any owner data."""
import argparse
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc03c.py"
SPEC = importlib.util.spec_from_file_location("dc03c_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def sample_run(tmp_path, monkeypatch):
    private = tmp_path / "private"
    private.mkdir()
    monkeypatch.setattr(runner.tempfile, "mkdtemp", lambda **_: str(private))
    args = argparse.Namespace(commit="a" * 40, site=tmp_path / "site", cache=tmp_path / "cache",
                              fixture=tmp_path / "fixture", output=tmp_path / "output")
    return runner.Run(args)


@pytest.mark.parametrize("passed", [True, False])
def test_package_allowlist_and_verdict(tmp_path, monkeypatch, passed):
    run = sample_run(tmp_path, monkeypatch)
    (run.private / "raw.log").write_text("198.51.100.10 /tmp/private file-api-sensitive")
    run.record("sample", "PASS" if passed else "FAIL", exit_code=0 if passed else 1)
    report = run.package(passed)
    runner.verify_archive(report)
    with zipfile.ZipFile(report) as bundle:
        assert set(bundle.namelist()) == set(runner.ALLOWLIST)
        assert json.loads(bundle.read("summary.json"))["status"] == ("PASS" if passed else "FAIL")
        assert b"sensitive" not in b"".join(bundle.read(member) for member in bundle.namelist())
    second = run.package(passed)
    assert report != second and report.exists()


def test_screening_prevents_copy(tmp_path, monkeypatch):
    run = sample_run(tmp_path, monkeypatch)
    run.record("sample", "FAIL", unsafe="file-api-redacted")
    with pytest.raises(ValueError, match="screening_forbidden_pattern"):
        run.package(False)
    assert not run.args.output.exists()
    assert (run.private / "checks.json").exists()


def test_hash_verification_detects_a_changed_member(tmp_path, monkeypatch):
    run = sample_run(tmp_path, monkeypatch)
    report = run.package(False)
    altered = tmp_path / "altered.zip"
    with zipfile.ZipFile(report) as original, zipfile.ZipFile(altered, "w") as changed:
        for member in original.namelist():
            data = original.read(member) + (b" " if member == "summary.json" else b"")
            changed.writestr(member, data)
    with pytest.raises(ValueError, match="zip_member_sha_mismatch"):
        runner.verify_archive(altered)
