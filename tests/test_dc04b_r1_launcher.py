"""Exercise R1 scope and safe evidence packaging without owner materials."""
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import zipfile

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc04b_r1.py"
MEMBERS = ["summary.json", "checks.json", "ab-before-after.json", "integrity.json", "report.md", "SHA256SUMS"]


def launcher():
    spec = importlib.util.spec_from_file_location("dc04b_r1_launcher", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bad_pin_still_produces_one_checked_blocked_zip(tmp_path):
    destination = tmp_path / "reports"
    result = subprocess.run([sys.executable, "-I", str(SCRIPT), "--commit", "/tmp/do-not-print",
                             "--blob", "a" * 40, "--output", str(destination)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 2
    archive, = destination.iterdir()
    with zipfile.ZipFile(archive) as evidence:
        assert evidence.namelist() == MEMBERS
        assert evidence.testzip() is None
        expected = "".join(f"{sha256(evidence.read(name)).hexdigest()}  {name}\n" for name in MEMBERS[:-1])
        assert evidence.read("SHA256SUMS").decode() == expected
        summary = json.loads(evidence.read("summary.json"))
        assert summary["status"] == "BLOCKED"
        assert summary["failure_code"] == "invalid_launch_pin"
        assert summary["new_provider_operations"] == 0
        assert summary["expert_score"] == "NOT RUN"
        assert b"do-not-print" not in b"".join(evidence.read(member) for member in MEMBERS)


@pytest.mark.parametrize(("raw", "reason"), [
    (b":100644 100644 d05a55 e922d9 M\0ds_dc/finance.py\0", "r1_scope_path_forbidden"),
    (b":100644 100644 d05a55 e922d9 M\0tests/test_dc04a.py\0", "r1_scope_path_forbidden"),
    (b":000000 120000 000000 e922d9 A\0ds_dc/dc04b_r1_replay.py\0", "r1_scope_change_forbidden"),
    (b":100644 000000 d05a55 000000 D\0ds_dc/evidence_answer.py\0", "r1_scope_change_forbidden"),
])
def test_scope_rejects_changes_that_would_weaken_protected_history(raw, reason):
    with pytest.raises(ValueError, match=reason):
        launcher().validate_scope(raw)


def test_scope_records_only_permitted_regular_file_changes():
    assert launcher().validate_scope(
        b":100644 100644 d05a55 e922d9 M\0ds_dc/evidence_answer.py\0"
        b":000000 100644 000000 e922d9 A\0tests/test_dc04b_r1.py\0"
    ) == {"ds_dc/evidence_answer.py": "M", "tests/test_dc04b_r1.py": "A"}


def test_replay_blocked_keeps_worker_result_when_no_comparison_exists(tmp_path):
    runner = launcher()
    checkout, baseline = tmp_path / "r1", tmp_path / "baseline"
    baseline.mkdir()
    script = checkout / runner.REPLAY
    script.parent.mkdir(parents=True)
    script.write_text("""
import json
from pathlib import Path
import sys

assert sys.argv[2] == 'baseline'
assert Path.cwd().name == 'baseline'
artifacts = Path(sys.argv[-1])
(artifacts / 'replay-checks.json').write_text(json.dumps({
    'status': 'BLOCKED', 'failure_code': 'private_history_missing',
    'criteria': {'R1-03': 'BLOCKED', 'R1-04': 'BLOCKED'},
}))
(artifacts / 'integrity.json').write_text('{"historical_report_verified": false}')
sys.exit(3)
""")
    replay, comparison, integrity = runner.run_replay(
        SimpleNamespace(commit="a" * 40, ledger=tmp_path / "ledger"),
        checkout, baseline, SimpleNamespace(prefix=[], env=dict(os.environ)), tmp_path,
    )
    assert replay["failure_code"] == "private_history_missing"
    assert comparison is None
    assert integrity == {"historical_report_verified": False}
