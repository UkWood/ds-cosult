"""Exercise the paid fence using synthetic files and an in-memory HTTPS double."""
from concurrent.futures import ThreadPoolExecutor
import json
import stat

import pytest

from ds_pilot import providers
from ds_pilot.paid_budget import PaidLedger, RESERVE

SECRET = "test-synthetic-key"


def envelope(plan=None, **changes):
    body = dict(id="synthetic-request", model=providers.MODEL, choices=[dict(
        finish_reason="stop", message=dict(content=json.dumps(plan or {"need_ids": ["n1"],
        "interpretation_status": "supported"})))], usage=dict(
        prompt_tokens=100, prompt_cache_hit_tokens=20, prompt_cache_miss_tokens=80,
        completion_tokens=10, total_tokens=110))
    body.update(changes)
    return json.dumps(body).encode()


def route(path, transport):
    return providers.DeepSeekRoute(SECRET, PaidLedger(path), transport)


def test_real_payload_and_reconciliation(tmp_path, capsys):
    path = tmp_path / "paid.sqlite"
    def fake(key, raw):
        assert key == SECRET and SECRET.encode() not in raw
        data = json.loads(raw)
        assert data["thinking"] == {"type": "disabled"} and data["tool_choice"] == "none"
        assert data["model"] == "deepseek-flash" and data["max_tokens"] == 450
        assert data["stream"] is False and "tools" not in data
        assert live.receipt("r")["state"] == "dispatch_intent"
        return 200, envelope()
    live = route(path, fake)
    live.reserve("r")
    assert live.dispatch("r", "P1", {"question": "question"})["need_ids"] == ["n1"]
    with pytest.raises(ValueError):
        live.dispatch("r", "P2", {})
    receipt = live.receipt("r")
    assert receipt["state"] == "usage_reconciled" and receipt["usage_estimate_micro_usd"] == 37
    assert receipt["model_request_id"] == "synthetic-request" and receipt["attempts"] == 1
    assert live.summary()["at_risk_micro_usd"] == 0
    live.close()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert SECRET not in "".join(capsys.readouterr()) and SECRET.encode() not in path.read_bytes()


@pytest.mark.parametrize("status", [400,401,403,429,503,307,408])
def test_http_errors_charge_full_reserve_and_no_retry(tmp_path, status):
    calls = []
    def fake(_, raw):
        calls.append(raw)
        return status, SECRET.encode()
    live = route(tmp_path / "paid.sqlite", fake)
    live.reserve("r")
    assert live.dispatch("r", "P2", {}) is None
    assert live.receipt("r")["error"] == f"http_{status}"
    assert live.summary()["at_risk_micro_usd"] == RESERVE
    with pytest.raises(ValueError):
        live.reserve("r")
    if status in (401,403):
        with pytest.raises(ValueError):
            live.reserve("new")
    assert len(calls) == 1
    live.close()


def test_timeout_twelve_total_and_restart(tmp_path):
    path = tmp_path / "paid.sqlite"
    calls = []
    def fake(*args):
        calls.append(1)
        raise TimeoutError(SECRET)
    live = route(path, fake)
    for i in range(12):
        if i == 6:
            live.close()
            live = route(path, fake)
        live.reserve(str(i))
        assert live.dispatch(str(i), "P1", {}) is None
    with pytest.raises(ValueError):
        live.reserve("13th")
    assert len(calls) == 12
    assert live.summary()["reserved_micro_usd"] == 84960
    assert live.summary()["remaining_micro_usd"] == 15040
    live.close()
    assert SECRET.encode() not in path.read_bytes()


def test_lock_crash_and_contention(tmp_path):
    path = tmp_path / "paid.sqlite"
    live = route(path, None)
    with pytest.raises(BlockingIOError):
        route(path, None)
    def reserve(i):
        try:
            live.reserve(str(i))
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(4) as pool:
        assert sum(pool.map(reserve, range(8))) == 1
    live.close()
    live = route(path, None)
    assert live.summary()["remaining_calls"] == 11
    assert live.summary()["at_risk_micro_usd"] == RESERVE
    live.close()


@pytest.mark.parametrize("raw, state, blocked", [
    (b"malformed", "unknown", False),
    (envelope(usage={}), "unknown", False),
    (envelope(choices=[{"finish_reason":"stop", "message":{"content":"malformed"}}]), "usage_reconciled", False),
    (envelope(model="another-model"), "unknown", True),
    (envelope(usage=dict(prompt_tokens=10001,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=10001,
                         completion_tokens=0)), "usage_reconciled", True),
])
def test_bad_responses(tmp_path, raw, state, blocked):
    live = route(tmp_path / "paid.sqlite", lambda *_: (200, raw))
    live.reserve("r")
    assert live.dispatch("r", "P1", {}) is None
    assert live.receipt("r")["state"] == state and live.summary()["blocked"] is blocked
    live.close()


def test_input_guard_counts_full_unicode_json_before_transport(tmp_path):
    live = route(tmp_path / "paid.sqlite", lambda *_: pytest.fail("unexpected transport"))
    live.reserve("r")
    assert live.dispatch("r", "P2", {"question":"я" * 3000}) is None
    assert live.receipt("r")["attempts"] == 0
    live.close()


@pytest.mark.parametrize("tty,wsl,rates,key", [
    (False, True, "", None), (True, False, "", None), (True, True, "0.40 1.20 0.006", None),
    (True, True, providers.PRICE_CONFIRMATION, ""), (True, True, providers.PRICE_CONFIRMATION, "bad"),
])
def test_no_implicit_key_prompt_or_network(monkeypatch, tty, wsl, rates, key):
    monkeypatch.setattr(providers.platform, "release", lambda: "microsoft-WSL2" if wsl else "linux")
    for stream in [providers.sys.stdin, providers.sys.stderr]:
        monkeypatch.setattr(stream,"isatty", lambda: tty)
    monkeypatch.setattr("builtins.input", lambda _: rates)
    monkeypatch.setattr(providers.getpass,"getpass", lambda _: pytest.fail("unexpected prompt") if key is None else key)
    monkeypatch.setattr(providers, "_official_post", lambda *_: pytest.fail("unexpected network"))
    with pytest.raises(ValueError):
        providers.create_live()


def test_https_transport_uses_single_direct_verified_connection(monkeypatch):
    calls = []
    class Connection:
        def __init__(self, host, *, timeout, context):
            assert host == "api.deepseek.com" and timeout == 25
            assert context.check_hostname and context.verify_mode == providers.ssl.CERT_REQUIRED
        def request(self, method, path, *, body, headers):
            calls.append((method, path, body))
            assert headers == {"Authorization": "Bearer " + SECRET, "Content-Type": "application/json"}
        def getresponse(self):
            return type("Redirect", (), {"status": 307})()
        def close(self):
            pass
    monkeypatch.setattr(providers.http.client, "HTTPSConnection", Connection)
    assert providers._official_post(SECRET, b"payload") == (307, b"")
    assert calls == [("POST", "/chat/completions", b"payload")]


def test_interactive_startup_creates_only_synthetic_ledger(monkeypatch, tmp_path, capsys):
    path = tmp_path / "test.sqlite"
    monkeypatch.setattr(providers.platform, "release", lambda: "microsoft-WSL2")
    for stream in (providers.sys.stdin, providers.sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: providers.PRICE_CONFIRMATION)
    monkeypatch.setattr(providers.getpass, "getpass", lambda _: SECRET)
    monkeypatch.setattr(providers, "canonical_path", lambda: path)
    monkeypatch.setattr(providers, "_official_post", lambda *_: pytest.fail("unexpected network"))
    live = providers.create_live()
    assert live.summary()["remaining_calls"] == 12
    live.close()
    assert SECRET not in "".join(capsys.readouterr()) and SECRET.encode() not in path.read_bytes()


@pytest.mark.parametrize("mode,case,status", [
    ("P1", "omit_second", "answered"),
    ("P1", "unsupported", "clarification"),
    ("P1", "duplicate", "clarification"),
    ("P2", "valid", "answered"),
    ("P2", "invalid_id", "needs_support"),
    ("P2", "hash_mismatch", "needs_support"),
])
def test_adapter_through_normal_turn(tmp_path, mode, case, status):
    import os
    from pathlib import Path
    from ds_pilot.catalog import Catalog, load_git
    from ds_pilot.engine import Pilot

    def transport(key, raw):
        request = json.loads(json.loads(raw)["messages"][1]["content"])
        if mode == "P1":
            plan = {"interpretation_status": "unsupported" if case == "unsupported" else "supported",
                    "need_ids": ["n1","n1"] if case == "duplicate" else ["n1"]}
        else:
            plan = {"question_needs_hash": request["question_needs_hash"],
                    "selection": request["candidates"]}
            if case == "invalid_id":
                plan["selection"]["n1"] = ["invented"]
            if case == "hash_mismatch":
                plan["question_needs_hash"] = "wrong"
        return 200, envelope(plan)

    live = route(tmp_path / "test-paid.sqlite", transport)
    pilot = Pilot(Catalog(load_git(Path(os.environ["SATURN_SOURCE"]))),
                  tmp_path / "lab.sqlite", lab=True, live=live)
    question = "Укажи питание БКД-ПК-RF.2 и назначение СЛДКС-1"
    result = pilot.ask(question, "session", "request", mode=mode)
    assert result["status"] == status and len(result["question_needs"]) == 2
    assert result["paid_receipt"]["state"] == "usage_reconciled"
    assert pilot.ask(question, "session", "request", mode=mode) == result
    before = live.summary()
    pilot.reset("session")
    assert live.summary() == before and before["dispatch_intents"] == 1
    live.close()
