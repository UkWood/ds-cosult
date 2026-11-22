"""Offline replay integrity regressions use disposable synthetic private files."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest


WORKER = Path(__file__).resolve().parents[1] / "ds_dc/dc04b_r1_replay.py"


def invoke(stage, ledger, artifacts):
    return subprocess.run(
        [sys.executable, str(WORKER), "--stage", stage,
         "--private-root", str(ledger), "--artifacts", str(artifacts)],
        cwd=WORKER.parents[1], capture_output=True, text=True, timeout=20,
    )


def test_missing_private_history_writes_blocked_diagnostic_without_creating_ledger(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    ledger = tmp_path / "ledger"

    result = invoke("baseline", ledger, artifacts)

    assert result.returncode == 3, result.stderr
    assert not ledger.exists()
    assert json.loads((artifacts / "replay-checks.json").read_text()) == {
        "status": "BLOCKED", "failure_code": "private_history_missing",
        "criteria": {"R1-03": "BLOCKED", "R1-04": "BLOCKED"},
    }


def test_symlinked_private_response_fails_without_reading_target(tmp_path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(mode=0o700)
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    proof = ledger / "dc04b-q01-n"
    proof.mkdir(mode=0o700)
    for item in (ledger / ".lock", ledger / "ledger.json", proof / "report.json",
                 proof / "actual-request.sha256"):
        item.touch(mode=0o600)
    sibling = tmp_path / "secret"
    sibling.write_text("private response target")
    (proof / "native-response.bin").symlink_to(sibling)

    result = invoke("baseline", ledger, artifacts)

    assert result.returncode == 2, result.stderr
    assert json.loads((artifacts / "replay-checks.json").read_text())["failure_code"] == "private_history_permissions"
    assert all("private response target" not in path.read_text() for path in artifacts.iterdir())
    assert sibling.read_text() == "private response target"


def response(content):
    return {
        "model": "deepseek-flash",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content,
                                 "reasoning_content": "PRIVATE REASONING"}}],
        "usage": {"prompt_tokens": 40836, "prompt_cache_hit_tokens": 0,
                  "prompt_cache_miss_tokens": 40836, "completion_tokens": 5905,
                  "total_tokens": 46741, "completion_tokens_details": {"reasoning_tokens": 5013}},
    }


HISTORICAL_TELEMETRY = {
    "tokens": {"prompt": 40836, "hit": 0, "miss": 40836,
               "completion": 5905, "total": 46741, "reasoning": 5013},
    "cost_micro_usd": {"known": 37337},
}


def test_extract_candidate_keeps_original_message_content_bytes():
    from ds_dc.dc04b_r1_replay import extract_candidate

    content = ' \n{ "x": "Ё", "preserve": "\\u0061" }\n'
    payload = json.dumps(response(content), ensure_ascii=True).encode()
    encoded = content.encode()

    assert extract_candidate(payload, hashlib.sha256(encoded).hexdigest(), HISTORICAL_TELEMETRY) == encoded


@pytest.mark.parametrize("mutation", ["duplicate", "duplicate_nested", "alternate_finish", "role",
                                     "multiple_choices", "tools", "wrong_usage", "wrong_digest", "invalid_utf8"])
def test_extract_rejects_invalid_or_mismatched_envelope(mutation):
    from ds_dc.dc04b_r1_replay import ReplayError, extract_candidate

    content = '{"ordinary": "fixture"}'
    envelope = response(content)
    if mutation == "alternate_finish":
        envelope["choices"][0]["finish_reason"] = "length"
    elif mutation == "role":
        envelope["choices"][0]["message"]["role"] = "user"
    elif mutation == "multiple_choices":
        envelope["choices"].append(envelope["choices"][0])
    elif mutation == "tools":
        envelope["choices"][0]["message"]["tool_calls"] = [{"type": "function"}]
    elif mutation == "wrong_usage":
        envelope["usage"]["completion_tokens_details"]["reasoning_tokens"] += 1
    payload = json.dumps(envelope).encode()
    if mutation == "duplicate":
        payload = b'{"model":"deepseek-flash",' + payload[1:]
    elif mutation == "duplicate_nested":
        payload = payload.replace(b'"finish_reason": "stop"', b'"finish_reason":"stop","finish_reason":"stop"')
    elif mutation == "invalid_utf8":
        payload = payload.replace(b"PRIVATE REASONING", b"\xff")
    candidate_sha = hashlib.sha256(content.encode()).hexdigest()
    if mutation == "wrong_digest":
        candidate_sha = "0" * 64

    with pytest.raises(ReplayError):
        extract_candidate(payload, candidate_sha, HISTORICAL_TELEMETRY)


def test_unsafe_output_rejects_ledger_subdirectory_without_writes(tmp_path):
    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    artifacts = ledger / "unsafe-output"
    artifacts.mkdir(mode=0o700)

    result = invoke("baseline", ledger, artifacts)

    assert result.returncode == 2, result.stderr
    assert json.loads(result.stdout)["failure_code"] == "unsafe_replay_output"
    assert list(artifacts.iterdir()) == []


def test_replay_lock_respects_an_active_exclusive_lock(tmp_path):
    import fcntl

    from ds_dc.dc04b_r1_replay import ReplayError, historical_lock

    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    lock = ledger / ".lock"
    lock.touch(mode=0o600)
    with lock.open("rb") as current:
        fcntl.flock(current, fcntl.LOCK_EX)
        with pytest.raises(ReplayError, match="private_history_busy") as error:
            with historical_lock(ledger):
                pytest.fail("active lock unexpectedly granted a replay snapshot")
    assert error.value.status == "BLOCKED"


def test_snapshot_detects_historical_proof_bytes_changed_under_lock(tmp_path):
    from ds_dc.dc04b_r1_replay import fingerprints, historical_lock

    ledger = tmp_path / "ledger"
    ledger.mkdir(mode=0o700)
    proof = ledger / "dc04b-q01-n"
    proof.mkdir(mode=0o700)
    for item in (ledger / ".lock", ledger / "ledger.json", proof / "report.json",
                 proof / "actual-request.sha256", proof / "native-response.bin"):
        item.touch(mode=0o600)
    response_file = proof / "native-response.bin"
    response_file.write_bytes(b"first bytes")
    with historical_lock(ledger) as snapshot:
        initial = fingerprints(snapshot())
        response_file.write_bytes(b"changed bytes")
        after = fingerprints(snapshot())
    assert set(initial) == set(after)
    assert initial.pop(response_file.name) != after.pop(response_file.name)
    assert initial == after
