import hashlib
import json
from email.parser import BytesParser
from email.policy import default

import httpx
import pytest

from ds_dc.evidence_integration import FUTURE_PROMPT_VERSION, PROMPTS
from ds_dc.trial_native import TrialNative


NOW = 1_797_206_400
KEY = "synthetic-native-credential"
BUDGET = 2_000_000


def make_request(tmp_path, *documents):
    cache = tmp_path / "cache"
    cache.mkdir(exist_ok=True)
    files = {}
    for raw, pages in documents:
        sha = hashlib.sha256(raw).hexdigest()
        (cache / (sha + ".pdf")).write_bytes(raw)
        files[sha] = pages
    metadata = {"prompt_version": "evidence-integration/2", "sources": {
        f"S{i}": {"kind": "pdf", "file_part": i, "physical_pages": count}
        for i, count in enumerate(files.values(), 1)}}
    parts = [{"type": "file", "file_id": f"OFFLINE_SLOT_{i}"}
             for i in range(1, len(files) + 1)]
    parts.extend([{"type": "text", "text": json.dumps(metadata)},
                  {"type": "text", "text": json.dumps({"question": "Question", "history": []})}])
    payload = {"model": "deepseek-flash", "thinking": {"type": "enabled"}, "reasoning_effort": "high",
               "stream": False, "max_tokens": 8192, "response_format": {"type": "json_object"}, "messages": [
        {"role": "system", "content": PROMPTS[FUTURE_PROMPT_VERSION]}, {"role": "user", "content": parts}]}
    sizing = {"estimate": 1000, "unique_files": len(files), "physical_pages": sum(files.values())}
    return cache, payload, files, sizing


def completion(*, finish="stop", model="deepseek-flash", content='{"candidate":"visible"}', **changes):
    return {"id": "synthetic-completion", "object": "chat.completion", "created": NOW, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content,
                                                 "reasoning_content": "private-test-reasoning"},
                         "finish_reason": finish}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 100, "total_tokens": 1100,
                      "prompt_cache_hit_tokens": 100, "prompt_cache_miss_tokens": 900,
                      "completion_tokens_details": {"reasoning_tokens": 25}}} | changes


def boundary(now, calls, *, answer=completion, wrong_filename=False):
    def handle(request):
        assert request.url.scheme == "https" and request.url.host == "api.deepseek.com"
        assert request.method == "POST"
        if request.url.path == "/files":
            multipart = BytesParser(policy=default).parsebytes(
                b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.read())
            purpose, anchor, ttl, document = list(multipart.iter_parts())
            assert purpose.get_payload(decode=True) == b"text_recognition"
            assert anchor.get_payload(decode=True) == b"created_at"
            assert ttl.get_payload(decode=True) == b"3600"
            pdf = document.get_payload(decode=True)
            sha = hashlib.sha256(pdf).hexdigest()
            assert document.get_filename() == sha + ".pdf"
            handle = f"file-api-mock-{len(calls)}"
            calls.append((request.url.path, handle))
            return httpx.Response(200, json={"id": handle, "object": "file", "purpose": "text_recognition",
                "created_at": int(now()), "expires_at": int(now()) + 3600, "bytes": len(pdf),
                "filename": "wrong.pdf" if wrong_filename else document.get_filename()})
        assert request.url.path == "/chat/completions"
        calls.append((request.url.path, json.loads(request.read())))
        result = answer()
        return result if isinstance(result, httpx.Response) else httpx.Response(200, json=result)
    return httpx.MockTransport(handle)


def adapter(tmp_path, cache, calls, *, now=lambda: NOW, key=KEY, budget=BUDGET, expires_at=None, **mock_options):
    return TrialNative(cache, tmp_path / "provider", budget, key=key, clock=now,
                       transport=boundary(now, calls, **mock_options), expires_at=expires_at)


def test_native_wire_reuses_verified_handle_until_ttl(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path, (b"%PDF-1.4\nverified pdf bytes", 2))
    clock = [NOW]
    calls = []
    native = adapter(tmp_path, cache, calls, now=lambda: clock[0])
    result = native.dispatch(payload, files, "first", sizing)
    assert result.status == "completed" and result.content == b'{"candidate":"visible"}'
    assert result.telemetry["estimated_micro_usd"] == 10581
    assert result.telemetry["known_micro_usd"] == 841
    assert result.telemetry["held_micro_usd"] == 0
    assert result.telemetry["usage"]["reasoning_tokens"] == 25
    assert result.telemetry["provider"] == "mock"
    assert result.telemetry["upload"] == {"attempted": 1, "completed": 1, "reused": 0, "pages": 2}
    assert calls[1][1] == payload | {"messages": [payload["messages"][0], {"role": "user", "content": [
        {"type": "file", "file_id": "file-api-mock-0"}, *payload["messages"][1]["content"][1:]]}]}
    assert payload["messages"][1]["content"][0]["file_id"] == "OFFLINE_SLOT_1"
    clock[0] += 60
    restarted = adapter(tmp_path, cache, calls, now=lambda: clock[0])
    assert restarted.dispatch(payload, files, "first", sizing).status == "duplicate_request"
    reused = restarted.dispatch(payload, files, "second", sizing)
    assert reused.telemetry["upload"] == {"attempted": 0, "completed": 0, "reused": 1, "pages": 0}
    assert reused.telemetry["known_micro_usd"] == 391
    assert calls[2][1]["messages"][1]["content"][0]["file_id"] == "file-api-mock-0"
    clock[0] += 3600
    refreshed = restarted.dispatch(payload, files, "third", sizing)
    assert refreshed.status == "completed" and refreshed.telemetry["upload"]["attempted"] == 1
    assert [call[0] for call in calls] == ["/files", "/chat/completions", "/chat/completions",
                                            "/files", "/chat/completions"]
    assert calls[4][1]["messages"][1]["content"][0]["file_id"] == "file-api-mock-3"
    all_state = []
    for path in (tmp_path / "provider").iterdir():
        assert not path.stat().st_mode & 0o077
        all_state.append(path.read_text())
    assert KEY not in "".join(all_state)
    assert "private-test-reasoning" not in "".join(all_state)
    assert "visible" not in "".join(all_state)
    assert '"prompt_tokens":1000' in "".join(all_state)
    assert "file-api-" not in json.dumps(result.telemetry)


def test_rotated_key_does_not_reuse_old_handles(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path, (b"%PDF-1.4\nverified pdf bytes", 1))
    calls = []
    assert adapter(tmp_path, cache, calls).dispatch(payload, files, "first", sizing).status == "completed"
    another = adapter(tmp_path, cache, calls, key="rotated-synthetic-native-credential")
    reply = another.dispatch(payload, files, "second", sizing)
    assert reply.status == "completed" and reply.telemetry["upload"]["reused"] == 0
    assert [call[0] for call in calls] == ["/files", "/chat/completions"] * 2


@pytest.mark.parametrize(("mode", "operation", "reason", "known", "attempts"), [
    ("timeout", "chat", "read_timeout", 450, 2),
    ("http", "chat", "http_error", 450, 2),
    ("redirect", "chat", "http_error", 450, 2),
    ("malformed", "chat", "invalid_json", 450, 2),
    ("error_envelope", "chat", "unexpected_envelope", 450, 2),
    ("duplicate_usage", "chat", "invalid_json", 450, 2),
    ("bad_usage", "chat", "incomplete_usage", 450, 2),
    ("bad_model", "chat", "model_mismatch", 450, 2),
    ("wrong_pdf", "upload", "filename_mismatch", 0, 1),
])
def test_unknown_charge_blocks_new_requests_and_never_retries(tmp_path, mode, operation, reason, known, attempts):
    cache, payload, files, sizing = make_request(tmp_path, (b"%PDF-1.4\nverified pdf bytes", 2))
    calls = []

    def answer():
        if mode == "timeout":
            raise httpx.ReadTimeout(f"private incident {KEY}")
        if mode == "http":
            return httpx.Response(503, json={"error": {"code": "503", "message": KEY}})
        if mode == "redirect":
            return httpx.Response(307, headers={"Location": "https://api.deepseek.com/chat/completions"})
        if mode == "malformed":
            return httpx.Response(200, content=b'{')
        if mode == "error_envelope":
            return completion(error={"message": KEY})
        if mode == "duplicate_usage":
            return httpx.Response(200, content=json.dumps(completion()).encode()[:-1] + b',"usage":{}}')
        if mode == "bad_usage":
            return completion(content="no candidate", usage={"prompt_tokens": True})
        return completion(model=KEY)

    native = adapter(tmp_path, cache, calls, answer=answer, wrong_filename=mode == "wrong_pdf")
    assert not TrialNative.check_state(tmp_path / "provider")
    reply = native.dispatch(payload, files, "first", sizing)
    assert reply.status == "provider_failure" and reply.content is None
    assert reply.telemetry["known_micro_usd"] == known
    assert reply.telemetry["held_micro_usd"] > 0
    failure = reply.telemetry["provider_failure"]
    assert failure["operation_kind"] == operation and failure["safe_reason_code"] == reason
    assert failure["financial_outcome_unknown"] is True
    assert KEY not in json.dumps(reply.telemetry)
    assert TrialNative.check_state(tmp_path / "provider")
    restarted = adapter(tmp_path, cache, calls, key="rotated-synthetic-credential", budget=BUDGET * 10)
    assert restarted.dispatch(payload, files, "first", sizing).status == "duplicate_request"
    assert restarted.dispatch(payload, files, "second", sizing).status == "provider_unknown"
    assert len(calls) == attempts


@pytest.mark.parametrize("usage", [None, {"prompt_tokens": True}])
def test_complete_candidate_is_available_when_usage_is_unknown(tmp_path, usage):
    cache, payload, files, sizing = make_request(tmp_path)
    calls = []
    native = adapter(tmp_path, cache, calls, answer=lambda: completion(usage=usage))
    reply = native.dispatch(payload, files, "first", sizing)
    assert reply.status == "completed_usage_unknown"
    assert reply.content == b'{"candidate":"visible"}'
    assert reply.telemetry["usage"] is None
    assert reply.telemetry["held_micro_usd"] == 324_404
    assert reply.telemetry["provider_failure"]["financial_outcome_unknown"] is True
    assert native.dispatch(payload, files, "another", sizing).status == "provider_unknown"
    assert len(calls) == 1


def test_new_submit_stops_at_provider_contract_expiry(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path)
    clock = [NOW]
    calls = []
    native = adapter(tmp_path, cache, calls, now=lambda: clock[0], expires_at=NOW + 30)
    assert native.dispatch(payload, files, "first", sizing).status == "completed"
    clock[0] += 30
    reply = native.dispatch(payload, files, "another", sizing)
    assert reply.status == "contract_expired"
    assert not reply.telemetry["chat_attempted"] and reply.telemetry["upload"]["attempted"] == 0
    assert len(calls) == 1


@pytest.mark.parametrize(("answer", "status"), [
    (lambda: completion(finish="length", content=None), "finish_not_stop"),
    (lambda: completion(content="broken candidate"), "invalid_candidate"),
    (lambda: completion(content=json.dumps({"echo": KEY})), "invalid_candidate"),
    (lambda: completion(content='{"echo":"' + ''.join(f'\\u{ord(x):04x}' for x in KEY) + '"}'),
        "invalid_candidate"),
    (lambda: completion(content='{"echo":"file-api-synthetic-private"}'), "invalid_candidate"),
])
def test_settled_chat_with_unusable_candidate_does_not_export_or_hold(tmp_path, answer, status):
    cache, payload, files, sizing = make_request(tmp_path)
    calls = []
    native = adapter(tmp_path, cache, calls, answer=answer)
    result = native.dispatch(payload, files, "first", sizing)
    assert result.status == status and result.content is None
    assert result.telemetry["known_micro_usd"] == 391
    assert result.telemetry["held_micro_usd"] == 0
    assert not TrialNative.check_state(tmp_path / "provider")
    assert native.contains_secret(KEY) and native.contains_secret("file-api-mock-0")
    assert KEY not in repr(result)
    assert len(calls) == 1


def test_budget_reserve_uses_protocol_capacity_not_local_estimate(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path, (b"%PDF-1.4\nverified pdf bytes", 2))
    calls = []
    native = adapter(tmp_path, cache, calls, budget=100_000)
    reply = native.dispatch(payload, files, "first", sizing)
    assert reply.status == "budget_exhausted"
    assert reply.telemetry["estimated_micro_usd"] < 100_000 < reply.telemetry["planned_reserve_micro_usd"]
    assert not calls


def test_settlements_reduce_the_launch_budget_before_each_reservation(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path)
    calls = []
    native = adapter(tmp_path, cache, calls, budget=324_795)
    assert native.dispatch(payload, files, "first", sizing).status == "completed"
    assert native.dispatch(payload, files, "second", sizing).status == "completed"
    reply = native.dispatch(payload, files, "third", sizing)
    assert reply.status == "budget_exhausted"
    assert reply.telemetry["budget"]["known_micro_usd"] == 782
    assert reply.telemetry["budget"]["remaining_micro_usd"] == 324_013
    assert len(calls) == 2


def test_native_preflight_rejects_modified_pdf_and_wrong_wire(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path, (b"%PDF-1.4\nverified pdf bytes", 2))
    calls = []
    native = adapter(tmp_path, cache, calls)
    assert native.dispatch(payload | {"tools": []}, files, "tools", sizing).status == "invalid_native_request"
    (cache / (next(iter(files)) + ".pdf")).write_bytes(b"%PDF-1.4\nchanged bytes")
    assert native.dispatch(payload, files, "changed", sizing).status == "file_unavailable"
    assert not calls


def test_offline_native_has_no_side_effects(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path)
    native = TrialNative(cache, tmp_path / "provider", None)
    assert native.dispatch(payload, files, "first", sizing).status == "offline"
    assert not (tmp_path / "provider").exists()


def test_inflight_operation_is_durable_and_unfinished_hold_survives(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path, (b"%PDF-1.4\nverified pdf bytes", 2))
    calls = []

    def stop_process():
        # An abrupt exit at the boundary leaves an in-flight Chat record, and no replayable body.
        raise KeyboardInterrupt

    native = adapter(tmp_path, cache, calls, answer=stop_process)
    with pytest.raises(KeyboardInterrupt):
        native.dispatch(payload, files, "first", sizing)
    assert TrialNative.check_state(tmp_path / "provider")
    next_native = adapter(tmp_path, cache, calls)
    assert next_native.dispatch(payload, files, "first", sizing).status == "duplicate_request"
    assert next_native.dispatch(payload, files, "second", sizing).status == "provider_unknown"
    assert [call[0] for call in calls] == ["/files", "/chat/completions"]


def test_private_state_rejects_duplicate_records_before_posting(tmp_path):
    cache, payload, files, sizing = make_request(tmp_path)
    calls = []
    provider = tmp_path / "provider"
    native = adapter(tmp_path, cache, calls)
    assert native.dispatch(payload, files, "first", sizing).status == "completed"
    record = next(path for path in provider.iterdir() if path.suffix == ".json")
    record.write_bytes(record.read_bytes()[:-1] + b',"requests":{}}')
    assert native.dispatch(payload, files, "first", sizing).status == "native_state_unavailable"
    assert len(calls) == 1


def test_state_write_loss_after_call_reports_uncertain_financial_outcome(tmp_path, monkeypatch):
    cache, payload, files, sizing = make_request(tmp_path)
    calls = []
    provider = tmp_path / "provider"
    native = adapter(tmp_path, cache, calls)
    save = native._ledger.save

    def fail_after_request(state):
        if calls:
            raise OSError("synthetic crash after post")
        save(state)

    monkeypatch.setattr(native._ledger, "save", fail_after_request)
    reply = native.dispatch(payload, files, "first", sizing)
    assert reply.status == "native_state_unavailable"
    assert reply.telemetry["known_micro_usd"] is None
    assert reply.telemetry["held_micro_usd"] > 0
    assert TrialNative.check_state(provider)
    assert len(calls) == 1
