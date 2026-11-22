"""Preparation and shareable evidence checks use synthetic local data."""
import importlib.util
import json
from pathlib import Path

from ds_dc.validation_dc03c import WSL_ESTIMATES, q01_evidence


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc03c.py"
SPEC = importlib.util.spec_from_file_location("dc03c_r1", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_wsl_sizing_pins():
    assert WSL_ESTIMATES == {"Q01": 53287, "Q02": 315382}


def test_q01_safe_evidence_uses_only_verdict_flags_and_coordinates():
    raw = {
        "v1": {"legacy": "invalid_locator"}, "coverage": "semantic_pending",
        "confirmed_claim_ids": [],
        "v2_claims": [{"id": "1", "technical_status": "semantic_pending", "relation_verified": False,
                       "locators": [{"page": 60, "table": 1, "row": 2, "column": 0,
                                     "bbox": [0, 1, 2, 3], "quote": "PRIVATE", "source": "/home/example"}]}],
    }
    evidence = q01_evidence(raw)
    assert evidence["claims"][0]["locators"] == [{"page": 60, "table": 1, "row": 2, "column": 0,
                                                  "bbox": [0, 1, 2, 3]}]
    assert "PRIVATE" not in json.dumps(evidence) and "/home" not in json.dumps(evidence)


def test_case_evidence_keeps_result_on_failure_and_hides_private_parameters(tmp_path):
    xml = tmp_path / "check.xml"
    xml.write_text('<testsuite><testcase classname="test_dc03c" name="test_r01[R01-A-private]" time="0.2">'
                   '<failure message="file-api-sensitive">/home/a/b</failure>'
                   '<properties><property name="r01_expected_supported" value="0"/></properties>'
                   '</testcase></testsuite>')
    case, = runner.junit_evidence(xml)["cases"]
    assert case["status"] == "FAIL" and case["case"] == "R01-A"
    assert case["metrics"] == {"r01_expected_supported": 0}
    assert "private" not in json.dumps(case) and "file-api" not in json.dumps(case)
    reviewer, = runner.junit_evidence(xml, reviewer=True)["cases"]
    assert "case" not in reviewer and "test" not in reviewer


def inputs(**overrides):
    from argparse import Namespace

    return Namespace(**(dict(site=None, cache=None, fixture=None, python=None) | overrides))


def make_repo(path):
    import subprocess

    path.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(path), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", *args],
            stderr=subprocess.DEVNULL, text=True).strip()

    git("init", "--quiet", "-b", "draft", "--template=")
    git("commit", "--quiet", "--allow-empty", "-m", "baseline")
    base = git("rev-parse", "HEAD")
    git("commit", "--quiet", "--allow-empty", "-m", "target")
    return git, base, git("rev-parse", "HEAD")


def test_preparation_checkout_pins_branch_and_leaves_existing_repo_clean(tmp_path, monkeypatch):
    import pytest

    git, base, pin = make_repo(tmp_path / "upstream")
    monkeypatch.setattr(runner, "REMOTE", str(tmp_path / "upstream"))
    monkeypatch.setattr(runner, "REF", "refs/heads/draft")
    monkeypatch.setattr(runner, "R1_BASE", base)
    env = runner.prep_environment() | {"GIT_ALLOW_PROTOCOL": "file"}
    runner.prepare_checkout(tmp_path / "prepared", pin, env)
    assert runner.git(env, tmp_path / "prepared", "rev-parse", "HEAD") == pin
    assert not runner.git(env, tmp_path / "prepared", "status", "--porcelain")
    assert git("rev-parse", "HEAD") == pin and not git("status", "--porcelain")
    with pytest.raises(ValueError, match="commit_not_in_draft_branch"):
        runner.prepare_checkout(tmp_path / "wrong", "f" * 40, env)
    with pytest.raises(ValueError, match="commit_not_after_r1_baseline"):
        runner.prepare_checkout(tmp_path / "old", base, env)


def test_discovery_helpers_reuse_verified_inputs_and_refuse_ambiguity(tmp_path, monkeypatch):
    import hashlib

    _, _, site_pin = make_repo(tmp_path / "website")
    monkeypatch.setattr(runner, "SITE", site_pin)
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "audit.json").write_text("{}")
    originals = {hashlib.sha256(bytes([n])).hexdigest(): bytes([n]) for n in range(14)}
    monkeypatch.setattr(runner, "CACHE_PDFS", dict.fromkeys(originals, 1))
    for sha, data in originals.items():
        (cache / (sha + ".pdf")).write_bytes(data)
    stale = tmp_path / "stale"
    stale.mkdir()
    (stale / "audit.json").write_text("{}")
    (stale / runner.TOKENIZER_FILE).write_text("frozen")
    first = next(iter(originals))
    (stale / (first + ".pdf")).write_bytes(originals[first])
    tokenizer = cache / runner.TOKENIZER_FILE
    tokenizer.write_text("frozen")
    monkeypatch.setattr(runner, "TOKENIZER", runner.digest(tokenizer))
    fixture = tmp_path / "q01-candidate.json"
    fixture.write_bytes(b"x" * 5188)
    monkeypatch.setattr(runner, "FIXTURE", hashlib.sha256(fixture.read_bytes()).hexdigest())
    env = tmp_path / "dc03b" / ".venv"
    (env / "bin").mkdir(parents=True)
    (env / "pyvenv.cfg").write_text("version = 3.12.14\n")
    python = env / "bin/python"
    python.touch()

    found, issues = runner.discover_materials(tmp_path, inputs(), runner.prep_environment())
    assert found == {"site": tmp_path / "website", "cache": cache, "fixture": fixture, "python": python}
    assert issues == {}
    (tmp_path / "second.json").write_bytes(fixture.read_bytes())
    python.unlink()
    _, issues = runner.discover_materials(tmp_path, inputs(), runner.prep_environment())
    assert issues == {"fixture": "fixture_ambiguous", "python": "python_not_found"}


def test_missing_inputs_produce_zip_without_fetch(tmp_path, monkeypatch):
    import subprocess
    import sys
    import zipfile

    for key in ("DS_DC_CACHE", "DS_DC_Q01_CANDIDATE", "SATURN_SOURCE"):
        monkeypatch.delenv(key, raising=False)
    root = tmp_path / "empty"
    root.mkdir()
    result = subprocess.run([sys.executable, "-I", str(SCRIPT), "--prepare", "--commit", "a" * 40,
                             "--wsl-root", str(root), "--output", str(tmp_path / "reports")],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 1, result.stderr
    report, = (tmp_path / "reports").glob("*.zip")
    runner.verify_archive(report)
    with zipfile.ZipFile(report) as zip_file:
        checks = json.loads(zip_file.read("checks.json"))
    assert checks["preparation_checkout"]["status"] == "BLOCKED"
    assert checks["preparation_inputs"]["issues"] == {
        "cache": "cache_not_found", "fixture": "fixture_not_found",
        "python": "python_not_found", "site": "site_not_found",
    }
    assert str(tmp_path) not in json.dumps(checks)


def test_checkout_validation_rejects_mismatching_head(tmp_path, monkeypatch):
    import pytest

    _, base, pin = make_repo(tmp_path / "repo")
    monkeypatch.setattr(runner, "ROOT", tmp_path / "repo")
    run = runner.Run(inputs(commit=base, site=tmp_path, cache=tmp_path, fixture=tmp_path / "fixture"))
    assert pin != base
    with pytest.raises(ValueError, match="checkout_pin_mismatch"):
        run.checkout()


def test_preparation_report_allowlists_only_phase_statuses(tmp_path):
    import pytest

    path = tmp_path / "prep.json"
    pin = "a" * 40
    record = dict(pin=pin, environment="WSL", status="PASS", duration_ms=250, exit_code=0)
    steps = {"preparation_pin": record.copy(),
             "preparation_inputs": record | {"issues": {}},
             "preparation_checkout": record.copy()}
    path.write_text(json.dumps(steps))
    assert runner.preparation_evidence(path, pin, "WSL") == steps
    steps["preparation_pin"]["notes"] = "private text"
    path.write_text(json.dumps(steps))
    with pytest.raises(ValueError, match="invalid_preparation_record"):
        runner.preparation_evidence(path, pin, "WSL")


def test_cache_discovery_pins_match_the_frozen_manifest():
    manifest = json.loads((SCRIPT.parents[2] / "docs/reports/ds-dc-02/corpus-manifest.json").read_text())
    assert runner.CACHE_PDFS == {row["sha256"]: row["bytes"] for row in manifest["files"]}
