import json
import os
from pathlib import Path
from threading import Thread
import time

import httpx
import pytest

from ds_dc.corpus import BKD, SLD, digest, encoded
from ds_dc.finance import Ledger, OWNER, Stopped
from ds_dc.native import NativeD1, mock_transport
from ds_dc.prep import freeze, load
from ds_dc.runtime import Journal, Pilot, verify
from ds_dc.resolver import Resolver


def test_short_followup_uses_active_scope_without_pronoun():
    row = dict(kind="device", draft=False, title="БКД-ПК-RF.2", body="",
               features={}, path="real.md", canonical="example")
    resolver = Resolver({BKD: row})
    for question in ("Какие интерфейсы?", "Резервное питание?", "Условия хранения?"):
        assert resolver.resolve(question, (BKD,))["selected"] == [BKD]
    assert resolver.resolve("А БКД-ПК-RF.99?", (BKD,))["selected"] == []


def test_native_wire_and_cost_policy():
    from ds_dc.context import wire, OUTPUT
    from ds_dc.finance import cold_cost
    payload = wire("Вопрос целиком", [], [], {}, [])
    assert payload["model"] == "deepseek-flash"
    assert payload["thinking"] == {"type": "enabled"}
    assert payload["reasoning_effort"] == "high"
    assert payload["max_tokens"] == OUTPUT == 8192
    assert "tools" not in payload
    assert cold_cost(128_000) <= 50_000
    assert cold_cost(256_000) <= 90_000


@pytest.fixture(scope="module")
def corpus():
    if not all(os.environ.get(k) for k in ("SATURN_SOURCE", "DS_DC_CACHE")):
        pytest.skip("Set SATURN_SOURCE and DS_DC_CACHE for corpus integration")
    cache = Path(os.environ["DS_DC_CACHE"])
    entries, registry, _ = load(Path(os.environ["SATURN_SOURCE"]), cache)
    return cache, entries, registry, freeze(entries, registry)


def provider(tmp_path, corpus, respond=None):
    cache, _, _, manifest = corpus
    base = mock_transport()
    requests = []

    def handler(request):
        requests.append(request)
        return respond(request, base) if respond else base.handle_request(request)

    native = NativeD1(cache, Ledger(tmp_path / "ledger"), manifest=manifest,
                      fixture=httpx.MockTransport(handler))
    return native, requests


def app(tmp_path, corpus, respond=None):
    cache, entries, registry, _ = corpus
    native, requests = provider(tmp_path, corpus, respond)
    pilot = Pilot(entries, registry, cache, Journal(tmp_path / "audit"), native,
                  cap=None, owner_dc02=True)
    return pilot, requests


def response(body, *, finish="stop", prompt=100):
    return httpx.Response(200, json=dict(model="deepseek-flash",
        choices=[dict(finish_reason=finish, message=dict(content=body, reasoning_content="must-not-leak"))],
        usage=dict(prompt_tokens=prompt, completion_tokens=10, total_tokens=prompt + 10,
                   prompt_cache_hit_tokens=60, prompt_cache_miss_tokens=prompt - 60)))


def test_real_dossiers_are_complete_scopes_with_unique_hashes(corpus):
    _, entries, registry, manifest = corpus
    assert len(entries) == 438
    counts = {entity: (len(block["pages"]), len({d["sha256"] for d in block["included_docs"]}),
                      sum({d["sha256"]: d["pages"] for d in block["included_docs"]}.values()))
              for entity, block in registry.items()}
    assert counts == {BKD: (1, 4, 80), SLD: (10, 10, 403)}
    assert len(manifest["files"]) == 14
    assert sum(doc["pages"] for doc in manifest["files"]) == 483
    assert any(len(doc["links"]) > 1 for doc in manifest["files"])
    omitted = manifest["dossiers"][SLD]["omissions"]
    assert any(row["state"] == "EXCLUDED_BY_OWNER" for row in omitted)


def test_http_fixture_reuse_across_isolated_sessions_and_redacted_diagnostics(tmp_path, corpus):
    pilot, requests = app(tmp_path, corpus)
    now = time.time()
    first = pilot.open("192.0.2.1", now)
    second = pilot.open("192.0.2.2", now)
    result = pilot.ask("192.0.2.1", first, "first", "Назначение БКД-ПК-RF.2?", now=now)
    assert result["status"] == "draft"
    assert result["chat_posts"] == 1
    assert result["context"]["unique_files"] == 4
    assert result["context"]["budget"]["page_attempts"] == 80
    assert result["context"]["verified_upper_bound"] is None
    assert result["context"]["observed_usage"]["prompt_tokens"] == 1000
    first_chat = requests[-1]
    assert first_chat.url == httpx.URL("https://api.deepseek.com/chat/completions")
    wire = json.loads(first_chat.content)
    assert wire["max_tokens"] == 8192
    assert {p["role"] for p in wire["messages"]} == {"system", "user"}
    file_parts = [part for part in wire["messages"][-1]["content"] if part["type"] == "file"]
    assert len(file_parts) == 4 and len({part["file_id"] for part in file_parts}) == 4
    assert b"192.0.2.1" not in first_chat.content
    assert b"Bearer" not in first_chat.content
    assert "file-api-" not in encoded(result)
    assert requests[0].content.index(b'name="purpose"') < requests[0].content.index(b'name="file"')
    lease = pilot.ask("192.0.2.2", second, "without", "Условия хранения?", now=now + 1)
    assert lease["status"] == "clarification"
    followup = pilot.ask("192.0.2.1", first, "followup", "Условия хранения?", now=now + 1)
    assert followup["decision"]["reason"] == "active"
    assert followup["context"]["file_cache_hits"] == 4
    assert followup["context"]["history"] > 0
    isolated = pilot.ask("192.0.2.2", second, "other", "БКД-ПК-RF.2?", now=now + 1)
    assert isolated["context"]["file_cache_hits"] == 4
    assert isolated["context"]["history"] == 0
    assert sum(r.url.path == "/files" for r in requests) == 4
    assert sum(r.url.path == "/chat/completions" for r in requests) == 3


@pytest.mark.parametrize(("finish", "body", "expected"), [
    ("length", "{", "truncated_candidate"),
    ("stop", "{", "invalid_candidate"),
])
def test_candidate_failures_settle_usage_and_do_not_retry(tmp_path, corpus, finish, body, expected):
    def respond(request, base):
        return response(body, finish=finish) if request.url.path == "/chat/completions" else base.handle_request(request)

    pilot, requests = app(tmp_path, corpus, respond)
    now = time.time()
    token = pilot.open("192.0.2.1", now)
    result = pilot.ask("192.0.2.1", token, "first", "БКД-ПК-RF.2?", now=now)
    assert result["status"] == expected
    assert result["context"]["budget"]["held_micro_usd"] == 0
    assert result["unresolved"] == ["БКД-ПК-RF.2?"]
    assert "must-not-leak" not in encoded(result)
    assert sum(r.url.path == "/chat/completions" for r in requests) == 1


@pytest.mark.parametrize("failure", ["timeout", 400, 401, 429, "partial_usage"])
def test_unknown_holds_after_restart_and_allows_p0(tmp_path, corpus, failure):
    def respond(request, base):
        if request.url.path != "/chat/completions":
            return base.handle_request(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture timeout")
        if failure == "partial_usage":
            payload = response("{}").json()
            del payload["usage"]["prompt_cache_miss_tokens"]
            return httpx.Response(200, json=payload)
        return httpx.Response(failure, json={"error": {"message": "fixture rejection"}})

    first, requests = app(tmp_path, corpus, respond)
    now = time.time()
    token = first.open("192.0.2.1", now)
    result = first.ask("192.0.2.1", token, "first", "БКД-ПК-RF.2?", now=now)
    assert result["status"] == "provider_unknown"
    assert result["context"]["budget"]["held_micro_usd"] == 50_000
    assert result["context"]["budget"]["page_attempts"] == 80
    assert requests[-1].url.path == "/chat/completions"
    restarted, retry_requests = app(tmp_path, corpus)
    token = restarted.open("192.0.2.1", now + 1)
    assert restarted.ask("192.0.2.1", token, "other", "БКД-ПК-RF.2?", now=now + 1)["status"] == "provider_unknown"
    assert restarted.ask("192.0.2.1", token, "p0", "БКД-ПК-RF.2?", now=now + 2,
                         mode="P0")["status"] == "navigation"
    assert not retry_requests


def test_ready_metadata_recheck_expiry_and_safe_cleanup(tmp_path, corpus):
    pilot, requests = app(tmp_path, corpus)
    now = time.time()
    token = pilot.open("192.0.2.1", now)
    first = pilot.ask("192.0.2.1", token, "first", "БКД-ПК-RF.2?", now=now)
    assert first["status"] == "draft"
    second = pilot.ask("192.0.2.1", token, "second", "Условия хранения?", now=now + 301)
    assert second["status"] == "draft"
    assert sum(r.method == "GET" for r in requests) == 4
    with pytest.raises(Stopped, match="binding_unavailable"):
        pilot.provider.cleanup("0" * 64, now)
    sha = first["sources"]["documents"][0]["sha256"]
    pilot.provider.cleanup(sha, now + 302)
    assert requests[-1].method == "DELETE"
    with pytest.raises(Stopped, match="binding_unavailable"):
        pilot.provider.cleanup(sha, now + 303)

    late = pilot.open("192.0.2.1", now + 3800)
    assert pilot.ask("192.0.2.1", late, "late", "БКД-ПК-RF.2?", now=now + 3800)["status"] != "draft"
    # The fixture returns epoch from wall-clock, so it cannot confirm a future timestamp.
    assert sum(r.method == "POST" and r.url.path == "/files" for r in requests) == 5


def test_document_rejection_keeps_remaining_dossier(tmp_path, corpus):
    def respond(request, base):
        if request.url.path == "/files" and not any(r.url.path == "/files" for r in seen):
            seen.append(request)
            return httpx.Response(413)
        return base.handle_request(request)

    seen = []
    pilot, requests = app(tmp_path, corpus, respond)
    now = time.time()
    token = pilot.open("192.0.2.1", now)
    result = pilot.ask("192.0.2.1", token, "first", "БКД-ПК-RF.2?", now=now)
    assert result["status"] == "draft"
    assert result["dossier_completeness"][BKD] == "partial"
    assert len(result["sources"]["documents"]) == 3
    assert result["document_diagnostics"][-1]["state"] == "provider_rejected_pdf"
    followup = pilot.ask("192.0.2.1", token, "second", "Условия хранения?", now=now + 1)
    assert followup["status"] == "draft"
    assert sum(r.url.path == "/files" for r in requests) == 4


def test_cross_process_recovery_reservation_never_auto_retries(tmp_path):
    ledger = Ledger(tmp_path / "journal")
    now = time.time()
    with ledger.transaction() as state:
        ledger.reserve(state, "run", "permit", "local", now, OWNER,
                       {"one": {"kind": "normal", "reserve": 50_000},
                        "two": {"kind": "upload", "reserve": 18_000, "pages": 80}})
        state["operations"]["one"]["state"] = "inflight"
        ledger.save(state)
    with Ledger(tmp_path / "journal").transaction() as recovered:
        assert recovered["operations"]["one"]["state"] == "unknown"
        assert recovered["operations"]["two"]["state"] == "cancelled"
        assert ledger.summary(recovered, "run", OWNER["budget"])["held_micro_usd"] == 50_000
        with pytest.raises(Stopped, match="provider_unknown"):
            ledger.reserve(recovered, "run", "permit", "local", now, OWNER,
                           {"other": {"kind": "normal", "reserve": 50_000}})


def test_parallel_budget_caps_and_cross_run_campaign(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    ledger = Ledger(tmp_path / "ledger")
    now = time.time()

    def attempt(index):
        with ledger.transaction() as state:
            try:
                key = str(index)
                ledger.reserve(state, "run", "permit", "local", now, OWNER | {"normal": 1},
                               {key: {"kind": "normal", "reserve": 50_000}})
                ledger.operate(state, key, lambda: None, lambda _: (10, {}))
                return "settled"
            except Stopped as exc:
                return str(exc)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert results.count("settled") == 1
    assert results.count("budget_exhausted") == 7
    with ledger.transaction() as state:
        ledger.reserve(state, "calib", "alpha", "owner", now, OWNER,
                       {"calib-one": {"kind": "calibration", "slot": "extended",
                                     "reserve": 400_000, "pages": 700}}, campaign="dc02-live")
        ledger.operate(state, "calib-one", lambda: None, lambda _: (321_944, {}))
        with pytest.raises(Stopped, match="campaign_budget_exhausted"):
            ledger.reserve(state, "regular", "beta", "owner", now, OWNER,
                           {"regular-one": {"kind": "upload", "reserve": 90_000, "pages": 400}},
                           campaign="dc02-live")


def test_source_locator_checks_scope_and_literal(corpus):
    cache, entries, _, _ = corpus
    row = entries[BKD]
    index, quote = next((n, line) for n, line in enumerate(row["raw"].splitlines(), 1)
                        if "информационно-измерительных систем" in line.casefold())
    source = dict(id=BKD, sha256=row["sha256"], raw=row["raw"], scope=[BKD])
    loc = dict(doc_id=BKD, field_path=f"line:{index}", sha256=row["sha256"], quote=quote)
    claim = dict(claim_id="1", scope=BKD, component="", literal="проверка",
                 value="", unit="", qualifier="", condition="", locators=[loc])
    question = "Технический вопрос?"
    candidate = dict(answer_candidate="Технический ответ.", status_hint="candidate", unresolved=[],
                     claims=[claim])
    status, diagnostics = verify(candidate, question, [], cache, pages=[source], dc02=True)
    assert status == "draft"
    assert diagnostics[0]["semantic"] == "pending_review"
    claim["qualifier"] = "добавленный квалификатор"
    assert verify(candidate, question, [], cache, pages=[source], dc02=True)[0] == "literal_mismatch"


def test_loopback_http_session_reload_and_origin(tmp_path, corpus):
    from ds_dc.owner_web import server_for

    pilot, _ = app(tmp_path, corpus)
    with server_for(pilot, 0) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            with httpx.Client(base_url=origin, trust_env=False) as browser:
                assert browser.get("/").status_code == 200
                assert browser.get("/session").status_code == 200
                question = dict(request="turn", question="БКД-ПК-RF.2?", mode="D1")
                assert browser.post("/ask", json=question).status_code == 403
                answer = browser.post("/ask", json=question, headers={"Origin": origin}).json()
                assert answer["label"] == "Черновик для сверки"
                assert browser.get("/session").json()["timeline"] == [answer]
                assert httpx.get(origin + "/session", trust_env=False).status_code == 409
                assert browser.post("/reset", json={}, headers={"Origin": origin}).json()["status"] == "ok"
                assert browser.get("/session").json()["timeline"] == []
        finally:
            server.shutdown()
            thread.join()


def test_live_key_and_local_approval_are_insufficient_without_reviewed_exact_bound(tmp_path, monkeypatch):
    from ds_dc.finance import RATES, cold_cost
    from ds_dc import native

    now = int(time.time())
    manifest = {"files": []}
    key = "inert-credential-for-offline-test"
    head = "a" * 40
    question = "Контрольный вопрос."
    wire_sha = native.wire_identity(question, [], [], [])
    url = "https://api-docs.deepseek.com/guides/document_parsing/"
    contract = dict(origin=native.ORIGIN, model="DeepSeek-V4.1-Flash-1017", rates=RATES,
        model_context_max=native.MODEL_CONTEXT, generation_max=8192, parser="text_recognition",
        reviewed_at=now, reviewer="fixture-only", rates_evidence=url,
        paid_operation_evidence=url, approved_bound_ids=[wire_sha])
    go = dict(kind="calibration", expires=now + 100, run="test-calibration", head=head,
        account="account", project="dc02", ledger_path=str(tmp_path / "ledger"), rates=RATES,
        key_sha256=digest(key.encode()), contract_sha=digest(encoded(contract).encode()),
        manifest_sha=digest(encoded(manifest).encode()),
        limits={k: 0 if k == "delete" else v for k, v in OWNER.items() if k != "reserve_disabled"})
    adapter = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest=manifest,
                       live=(go, head, key, contract))
    calls = []

    def fixture(method, route, **kwargs):
        calls.append((method, route, kwargs))
        return response('{"answer_candidate":"operator never sees this"}').json()

    monkeypatch.setattr(adapter, "send", fixture)
    status, _, diag = adapter.dispatch("a", question, [], [], [], now)
    assert status == "native_bound_unverified"
    assert diag["verified_upper_bound"] is None
    assert calls == []
    bound = native.MODEL_CONTEXT - 8192
    monkeypatch.setitem(native.REVIEWED_BOUNDS, (wire_sha, "provider_billable_maximum"), dict(kind="provider_billable_maximum",
        request_sha256=wire_sha, manifest_sha256=go["manifest_sha"], billable_input=bound,
        parsed_bytes_max=0, evidence_url=url, derivation="synthetic control only"))
    status, candidate, diag = adapter.dispatch("a", question, [], [], [], now)
    assert status == "calibration_observed"
    assert candidate is None
    assert len(calls) == 1
    assert diag["verified_upper_bound"] == bound
    with adapter.ledger.transaction() as state:
        row = next(iter(state["operations"].values()))
        assert row["reserve"] == cold_cost(bound)
        assert row["kind"] == "calibration"
    restarted = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest=manifest,
                         live=(go, head, key, contract))
    monkeypatch.setattr(restarted, "send", fixture)
    assert restarted.dispatch("new-request-id", question, [], [], [], now)[0] == "duplicate_operation"
    assert row["slot"] == "extended"
    with pytest.raises(Stopped, match="cleanup_not_authorized"):
        adapter.cleanup("0" * 64, now)
    assert adapter.dispatch("another", "Question changed.", [], [], [], now)[0] == "native_bound_unverified"
    assert len(calls) == 1


def test_extended_fixture_uses_server_sizing_and_cap(tmp_path, monkeypatch):
    from ds_dc import native

    original = native.size
    cache = tmp_path / "cache"
    cache.mkdir()
    transport = mock_transport()
    adapter = NativeD1(cache, Ledger(tmp_path / "ledger"), fixture=transport,
                       manifest={"files": []})

    def sizing(*args):
        return original(*args) | {"estimate": 140_000, "input_mode": "extended"}

    monkeypatch.setattr(native, "size", sizing)
    assert adapter.dispatch("a", "Вопрос", [], [], [], time.time(), 128_000)[0] == "over_cap"
    assert adapter.chat_posts == 0
    state, _, diagnostics = adapter.dispatch("a", "Вопрос", [], [], [], time.time())
    assert state == "candidate"
    assert diagnostics["input_mode"] == "extended"
    assert diagnostics["budget"]["operations"]["extended"] == 1


def test_memory_expires_and_journal_prunes_without_resetting_admission(tmp_path):
    journal = Journal(tmp_path / "audit")
    base = time.time()
    peer = "192.0.2.10"
    journal.record(peer, base - 30 * 86400 - 1, "historical question", {"status": "draft"})
    journal.purge(base)
    assert not list(journal.directory.glob("turn-*.md"))
    for _ in range(20):
        assert journal.admit(peer, "2026-11-20")
    reopened = Journal(journal.directory)
    assert not reopened.admit(peer, "2026-11-20")
    assert reopened.admit(peer, "2026-11-21")
    assert (journal.directory / "admission.json").stat().st_mode & 0o077 == 0
    adapter = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest={"files": []})
    pilot = Pilot({}, {}, tmp_path, journal, adapter, cap=None, owner_dc02=True)
    token = pilot.open(peer, base)
    pilot.sessions[peer].history.append({"text": "old technical memory"})
    pilot.sessions[peer].series = 6
    new = pilot.open(peer, base + 905, resume=token)
    assert new and new != token
    assert pilot.open(peer, base + 906, resume=new) == new
    assert pilot.sessions[peer].series == 6 and not pilot.sessions[peer].history
    assert pilot.open(peer, base + 1801, resume=new) == new
    assert pilot.sessions[peer].series == 0


def _reserve_process(directory, request_id, queue):
    ledger = Ledger(directory)
    try:
        with ledger.transaction() as state:
            ledger.reserve(state, "parallel", "permit", "owner", time.time(), OWNER | {"normal": 1},
                {request_id: {"kind": "normal", "reserve": 50_000}})
            ledger.operate(state, request_id, lambda: None, lambda _: (12, {}))
        queue.put("settled")
    except Stopped as exc:
        queue.put(str(exc))


def test_ledger_cap_across_processes(tmp_path):
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    directory = tmp_path / "ledger"
    workers = [context.Process(target=_reserve_process, args=(directory, str(i), queue)) for i in range(3)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        assert worker.exitcode == 0
    statuses = sorted(queue.get(timeout=2) for _ in workers)
    assert statuses == ["budget_exhausted", "budget_exhausted", "settled"]


def test_changed_binding_cannot_be_accessed_by_chat_or_cleanup(tmp_path, corpus):
    pilot, requests = app(tmp_path, corpus)
    now = time.time()
    token = pilot.open("192.0.2.1", now)
    result = pilot.ask("192.0.2.1", token, "first", "БКД-ПК-RF.2?", now=now)
    sha = result["sources"]["documents"][0]["sha256"]
    ledger = pilot.provider.ledger
    with ledger.transaction() as state:
        state["bindings"][pilot.provider.file_key(sha)]["account"] = "elsewhere"
        ledger.save(state)
    count = len(requests)
    assert pilot.ask("192.0.2.1", token, "other", "Условия хранения?", now=now + 1)[
        "status"] == "binding_unavailable"
    with pytest.raises(Stopped, match="binding_unavailable"):
        pilot.provider.cleanup(sha, now)
    assert len(requests) == count


def test_provider_usage_drift_stops_before_next_post(tmp_path, corpus):
    def respond(request, base):
        if request.url.path != "/chat/completions":
            return base.handle_request(request)
        altered = response("{}").json()
        altered["usage"]["server_tool_use"] = {"tool_search": 1}
        return httpx.Response(200, json=altered)

    pilot, requests = app(tmp_path, corpus, respond)
    now = time.time()
    token = pilot.open("192.0.2.1", now)
    first = pilot.ask("192.0.2.1", token, "one", "БКД-ПК-RF.2?", now=now)
    assert first["status"] == "provider_unknown"
    assert first["context"]["budget"]["held_micro_usd"] == 50_000
    assert pilot.ask("192.0.2.1", token, "two", "БКД-ПК-RF.2?", now=now + 1)["status"] == "provider_unknown"
    assert sum(r.url.path == "/chat/completions" for r in requests) == 1


def test_bad_cached_pdf_does_not_prevent_delivery_of_other_originals(tmp_path, corpus):
    from shutil import copyfile

    original, entries, registry, manifest = corpus
    cache = tmp_path / "isolated-cache"
    cache.mkdir()
    bkd = registry[BKD]["included_docs"]
    bad = bkd[0]["sha256"]
    for doc in bkd:
        name = doc["sha256"] + ".pdf"
        if doc["sha256"] == bad:
            (cache / name).write_bytes(b"cached content changed")
        else:
            copyfile(original / name, cache / name)
    pilot, requests = app(tmp_path, (cache, entries, registry, manifest))
    now = time.time()
    token = pilot.open("192.0.2.1", now)
    result = pilot.ask("192.0.2.1", token, "one", "БКД-ПК-RF.2?", now=now)
    assert result["chat_posts"] == 1
    assert result["dossier_completeness"][BKD] == "partial"
    assert result["document_diagnostics"][-1]["state"] == "cache_integrity_error"
    assert len(result["sources"]["documents"]) == 3
    assert sum(request.url.path == "/files" for request in requests) == 3


def test_visible_answer_cap_is_explicit_without_retry(tmp_path):
    def fixture(request):
        candidate = dict(answer_candidate="Техническое описание. " * 1400,
                         status_hint="candidate", claims=[], unresolved=[])
        return response(encoded(candidate))

    adapter = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest={"files": []},
                       fixture=httpx.MockTransport(fixture))
    state, candidate, diag = adapter.dispatch("a", "Дайте описание.", [], [], [], time.time())
    assert state == "candidate_too_long" and candidate is None
    assert diag["visible_tokens_estimate"] > 1200
    assert adapter.chat_posts == 1
    assert diag["budget"]["held_micro_usd"] == 0


def test_approved_scope_envelope_covers_followups_without_heuristic_admission(tmp_path, monkeypatch):
    from ds_dc import native

    provider = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest={"files": []})
    first = native.wire_approval("Вопрос.", [], [], [])
    next_turn = native.wire_approval("Уточнение?", [], [], [{"text": "Вопрос.", "unresolved": ["Вопрос."]}])
    assert first["wire_sha256_without_handles"] != next_turn["wire_sha256_without_handles"]
    scope = first["scope_wire_sha256_without_handles"]
    assert scope == next_turn["scope_wire_sha256_without_handles"]
    provider.live = ({"kind": "regular"}, None, None, {"approved_bound_ids": [scope]})
    monkeypatch.setitem(native.REVIEWED_BOUNDS, (scope, "complete_scope_bound"), {
        "kind": "complete_scope_bound", "scope_sha256": scope, "manifest_sha256": provider.manifest_sha,
        "wire_bytes_max": next_turn["max_wire_bytes"], "billable_input": 127_000, "parsed_bytes_max": 0,
        "evidence_url": "https://api-docs.deepseek.com/", "derivation": "synthetic control only",
    })
    assert provider.bound(first) == provider.bound(next_turn) == 127_000
    with pytest.raises(Stopped, match="native_bound_unverified"):
        provider.bound(next_turn | {"max_wire_bytes": next_turn["max_wire_bytes"] + 1})
    provider.live[0]["kind"] = "calibration"
    with pytest.raises(Stopped, match="native_bound_unverified"):
        provider.bound(first)


def test_compacted_history_is_used_for_the_next_turn(tmp_path, monkeypatch):
    from ds_dc import native

    now = time.time()
    row = dict(kind="device", draft=False, title="БКД-ПК-RF.2", canonical="https://example.org",
               body="", features={}, path="bkd.md")
    dossier = dict(id="bkd", state="ready", pages=[], docs=[], issues=[], included_docs=[],
                   completeness="complete")
    adapter = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest={"files": []},
                       fixture=mock_transport())
    pilot = Pilot({BKD: row}, {BKD: dossier}, tmp_path, Journal(tmp_path / "audit"),
                  adapter, cap=None, owner_dc02=True)
    peer = "192.0.2.1"
    token = pilot.open(peer, now)
    session = pilot.sessions[peer]
    session.active = (BKD,)
    session.history = [
        {"text": "resolved old turn", "unresolved": []},
        {"text": "open old turn", "unresolved": ["open old turn"]},
    ]
    original_size = native.size

    def sizing(question, pages, documents, history, cache):
        measured = original_size(question, pages, documents, history, cache)
        if any(turn["text"] == "resolved old turn" for turn in history):
            measured["estimate"] = 300_000
        return measured

    monkeypatch.setattr(native, "size", sizing)
    first = pilot.ask(peer, token, "first", "Какие интерфейсы?", now=now)
    assert first["chat_posts"] == 1
    assert first["context"]["compacted_turns"] == 1
    assert session.history[0]["text"] == "open old turn"
    second = pilot.ask(peer, token, "second", "Резервное питание?", now=now + 1)
    assert second["chat_posts"] == 1
    assert second["context"]["compacted_turns"] == 0


def controlled_operator(tmp_path, corpus, monkeypatch, finish="stop", fault=None):
    from ds_dc import native
    from ds_dc.finance import RATES

    cache, entries, registry, manifest = corpus
    report = json.loads(Path("docs/reports/ds-dc-02/r1-calibration-sizing.json").read_text())
    questions = report["requests"]
    now = int(time.time())
    key, head = "fixture-only-inert-credential", "a" * 40
    evidence = "https://api-docs.deepseek.com/guides/document_parsing/"
    ledger = Ledger(tmp_path / "ledger")
    contract = dict(origin=native.ORIGIN, model="DeepSeek-V4.1-Flash-1017", rates=RATES,
                    model_context_max=native.MODEL_CONTEXT, generation_max=8192,
                    parser="text_recognition", reviewed_at=now, reviewer="Fixture",
                    rates_evidence=evidence, paid_operation_evidence=evidence, approved_bound_ids=[])
    base = mock_transport()
    calls = []

    def handle(request):
        calls.append(request)
        if fault == "upload" and request.url.path == "/files":
            return httpx.Response(413)
        if request.url.path == "/chat/completions":
            if fault == "timeout":
                raise httpx.ReadTimeout("fixture")
            request_wire = json.loads(request.content)
            body = json.loads(request_wire["messages"][-1]["content"][-1]["text"])
            assert body["history"] == []
            assert request_wire["max_tokens"] == 8192
            content = encoded(dict(answer_candidate="Черновик", status_hint="partial",
                                   unresolved=[body["question"]], claims=[]))
            payload = response(content, finish=finish).json()
            payload["usage"]["completion_tokens_details"] = {"reasoning_tokens": 3}
            if fault == "partial":
                del payload["usage"]["prompt_cache_miss_tokens"]
            if fault == "overage":
                payload = response(content, prompt=1_200_000).json()
            return httpx.Response(200, json=payload)
        return base.handle_request(request)

    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(httpx, "HTTPTransport", lambda **_: transport)

    def factory(qid, risk=True, prior=None, kind="controlled_calibration", account="fixture-account",
                recovery_sha=None):
        sizing = questions[qid]
        pages, uploads = sizing["physical_pages"], sizing["unique_files"]
        go = dict(kind=kind, cal_id=qid, accepted_residual_risk=risk,
                  wire_sha256=sizing["wire_sha256_without_handles"], expires=now + 600,
                  run="cal-" + qid, head=head, account=account, project="fixture-project",
                  ledger_path=str(ledger.path.resolve()), rates=RATES, key_sha256=digest(key.encode()),
                  contract_sha=digest(encoded(contract).encode()), manifest_sha=report["manifest_sha256"],
                  limits=dict(budget=330_000 + 225 * pages, normal=0, extended=1, chats=1,
                              pages=pages, upload=uploads, status=0, delete=0, calibration=1))
        if prior:
            go["cal01_permit_sha"] = prior
        if recovery_sha:
            go["recovery_authorization_sha"] = recovery_sha
            go["run"] += "-recovery"
        if kind == "regular":
            go["limits"]["calibration"] = 0
        adapter = NativeD1(cache, ledger, manifest=manifest, live=(go, head, key, contract))
        return Pilot(entries, registry, cache, Journal(tmp_path / "audit"), adapter, owner_dc02=True)

    def ask(pilot, qid, request="attempt"):
        peer = "192.0.2.1"
        token = pilot.open(peer, now)
        return pilot.ask(peer, token, request, questions[qid]["question"], now=now)

    return factory, ask, calls, ledger


def test_controlled_calibration_exact_order_and_receipts(tmp_path, corpus, monkeypatch):
    factory, ask, calls, ledger = controlled_operator(tmp_path, corpus, monkeypatch)
    with pytest.raises(ValueError):
        factory("Q01", risk=False)
    with pytest.raises(ValueError):
        factory("Q02")
    with pytest.raises(ValueError):
        factory("Q10")
    first = factory("Q01")
    disabled = NativeD1(first.cache, ledger, manifest=first.provider.manifest)
    assert disabled.dispatch("disabled", "", [], [], [], time.time())[0] == "live_disabled"
    question = "Какое назначение у БКД-ПК-RF.2?"
    assert first.ask("127.0.0.1", first.open("127.0.0.1"), "changed", question)["status"] == "calibration_wire_mismatch"
    assert ask(factory("Q02", prior=first.provider.permit_sha), "Q02")["status"] == "cal01_not_confirmed"
    _, _, registry, _ = corpus
    changed = factory("Q01")
    changed.dossiers = {**registry, BKD: {**registry[BKD], "included_docs": registry[BKD]["included_docs"][1:]}}
    assert ask(changed, "Q01")["status"] == "calibration_wire_mismatch"
    assert ask(factory("Q01", kind="regular"), "Q01")["status"] == "native_bound_unverified"
    assert not calls
    observed = ask(first, "Q01")
    assert observed["status"] == "calibration_observed"
    assert observed["context"]["verified_upper_bound"] is None
    assert not first.sessions["192.0.2.1"].history
    assert ask(factory("Q01"), "Q01", "new-id")["status"] == "duplicate_operation"
    assert ask(factory("Q02", prior=first.provider.permit_sha, account="changed"), "Q02")["status"] == "cal01_not_confirmed"
    assert ask(factory("Q02", prior=first.provider.permit_sha), "Q02")["status"] == "calibration_observed"
    assert [r.url.path for r in calls] == ["/files"] * 4 + ["/chat/completions"] + ["/files"] * 10 + ["/chat/completions"]
    with ledger.transaction() as state:
        chats = [row for row in state["operations"].values() if row["kind"] == "calibration"]
        assert [row["reserve"] for row in chats] == [330_000, 330_000]
        assert all(row["slot"] == "extended" and row["state"] == "settled" for row in chats)
        assert [len({doc["sha256"] for doc in row["calibration_result"]["documents"]})
                for row in chats] == [4, 10]
        assert chats[0]["calibration_result"]["candidate"]["answer_candidate"] == "Черновик"
        assert chats[0]["calibration_result"]["verification_status"] == "draft"
        assert chats[0]["usage"]["reasoning_tokens"] == 3
        assert "must-not-leak" not in encoded(chats)


@pytest.mark.parametrize(("finish", "fault", "status"), [
    ("length", None, "calibration_finish_not_stop"),
    ("stop", "timeout", "provider_unknown"),
    ("stop", "upload", "provider_unknown"),
    ("stop", "partial", "provider_unknown"),
    ("stop", "overage", "provider_overage"),
])
def test_controlled_calibration_holds_and_stops(tmp_path, corpus, monkeypatch, finish, fault, status):
    factory, ask, calls, ledger = controlled_operator(tmp_path, corpus, monkeypatch, finish, fault)
    first = factory("Q01")
    result = ask(first, "Q01")
    assert result["status"] == status
    held = result["context"]["budget"]["held_micro_usd"]
    if fault == "upload":
        assert len(calls) == 1 and calls[0].url.path == "/files"
        with ledger.transaction() as state:
            row = next(row for row in state["operations"].values() if row["state"] == "unknown")
            assert held == row["pages"] * 225
    elif fault == "overage":
        assert held > 330_000
    else:
        assert held == 330_000
    count = len(calls)
    assert ask(factory("Q02", prior=first.provider.permit_sha), "Q02")["status"] == "cal01_not_confirmed"
    assert len(calls) == count


@pytest.mark.parametrize(("fault", "stage", "reason", "status", "received"), [
    ("connect", "transport", "connect_timeout", None, False),
    ("read", "transport", "read_timeout", None, False),
    ("write", "transport", "write_timeout", None, False),
    ("network", "transport", "network_error", None, False),
    ("response_read", "response_read", "read_timeout", 200, True),
    (400, "http_status", "http_error", 400, True),
    (401, "http_status", "http_error", 401, True),
    (402, "http_status", "http_error", 402, True),
    (403, "http_status", "http_error", 403, True),
    (408, "http_status", "http_error", 408, True),
    (413, "http_status", "http_error", 413, True),
    (429, "http_status", "http_error", 429, True),
    (500, "http_status", "http_error", 500, True),
    (504, "http_status", "http_error", 504, True),
    ("invalid_json", "json_decode", "invalid_json", 200, True),
    ("schema", "response_schema_validation", "expected_object", 200, True),
    ("missing_id", "file_metadata_validation", "id_missing", 200, True),
    ("wrong_type", "file_metadata_validation", "bytes_type", 200, True),
    ("wrong_ttl", "file_metadata_validation", "ttl_mismatch", 200, True),
])
def test_calr_upload_failure_is_safe_and_holds(tmp_path, corpus, monkeypatch, fault, stage, reason, status, received):
    factory, ask, _, ledger = controlled_operator(tmp_path, corpus, monkeypatch)
    base = mock_transport()
    calls = []

    class BrokenBody(httpx.SyncByteStream):
        def __iter__(self):
            raise httpx.ReadTimeout("unsafe request detail")

    def handle(request):
        calls.append(request.url.path)
        errors = {"connect": httpx.ConnectTimeout, "read": httpx.ReadTimeout,
                  "write": httpx.WriteTimeout, "network": httpx.ConnectError}
        if fault in errors:
            raise errors[fault]("unsafe request detail")
        if type(fault) is int:
            if fault == 504:
                return httpx.Response(fault, text="<html>unsafe provider data</html>")
            return httpx.Response(fault, json={"error": {"code": 402 if fault == 402 else "unsafe provider data",
                "message": "unsafe request detail", "nested": {"authorization": "private datum"}}})
        if fault == "response_read":
            return httpx.Response(200, stream=BrokenBody())
        if fault == "invalid_json":
            return httpx.Response(200, content=b'{"secret":"unsafe provider data"')
        if fault == "schema":
            return httpx.Response(200, json=["unsafe provider data"])
        payload = base.handle_request(request).json()
        if fault == "missing_id":
            del payload["id"]
        elif fault == "wrong_type":
            payload["bytes"] = True
        else:
            payload["expires_at"] += 1
        return httpx.Response(200, json=payload)

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **_: httpx.MockTransport(handle))
    answer = ask(factory("Q01"), "Q01")
    assert answer["status"] == "provider_unknown"
    failure = answer["context"]["provider_failure"]
    assert (failure["failure_stage"], failure["safe_reason_code"], failure["http_status"],
            failure["response_received"]) == (stage, reason, status, received)
    assert failure["operation_kind"] == "upload"
    assert failure["provider_error_code"] == ("402" if fault == 402 else None)
    assert failure["financial_outcome_unknown"] and failure["elapsed_ms"] >= 0
    saved = ledger.file.read_text()
    assert "unsafe" not in saved and "private datum" not in saved
    assert not json.loads(saved)["bindings"]
    assert answer["context"]["budget"]["held_micro_usd"] == 65 * 225
    assert ask(factory("Q01"), "Q01", "new-id")["status"] == "duplicate_operation"
    assert calls == ["/files"]


@pytest.mark.parametrize(("field", "wrong_value", "reason"), [
    ("id", "invalid", "id_format"),
    ("object", "wrong", "object_mismatch"),
    ("purpose", "wrong", "purpose_mismatch"),
    ("filename", "wrong", "filename_mismatch"),
    ("bytes", 2, "bytes_mismatch"),
    ("created_at", 999999, "created_at_future"),
    ("expires_at", 999, "expires_at_elapsed"),
])
def test_calr_all_metadata_fields(tmp_path, field, wrong_value, reason):
    from ds_dc.provider_failure import ProviderFailure

    adapter = NativeD1(tmp_path, Ledger(tmp_path / "ledger"), manifest={"files": []})
    sha = "a" * 64
    valid = dict(id="file-api-fixture", object="file", purpose="text_recognition",
                 filename=sha + ".pdf", bytes=1, created_at=1000, expires_at=4600)
    missing = {name: value for name, value in valid.items() if name != field}
    for payload, code in ((missing, field + "_missing"), (valid | {field: None}, field + "_type"),
                          (valid | {field: wrong_value}, reason)):
        with pytest.raises(ProviderFailure) as error:
            adapter.file_snapshot(payload, sha, 1, 1000)
        assert error.value.stage == "file_metadata_validation"
        assert error.value.reason == code


def test_calr_ledger_accounting_and_legacy_rows(tmp_path):
    from ds_dc.native import ProviderObject

    ledger = Ledger(tmp_path / "ledger")
    legacy = dict(operations={"old": dict(kind="extended", run="previous", reserve=15, cost=15, state="settled")},
                  bindings={}, runs={})
    ledger.save(legacy)
    with ledger.transaction() as state:
        assert state["operations"]["old"] == legacy["operations"]["old"]
        ledger.reserve(state, "fixture", "permit", "owner", time.time(), OWNER,
                       {"new": dict(kind="calibration", slot="extended", reserve=330000)})

        def fail(_):
            raise RuntimeError("unsafe accounting detail")

        with pytest.raises(Stopped, match="provider_unknown"):
            ledger.operate(state, "new", lambda: ProviderObject({}, 200), fail)
        failure = state["operations"]["new"]["provider_failure"]
        assert failure["failure_stage"] == "financial_accounting"
        assert failure["safe_reason_code"] == "accounting_error"
        assert failure["operation_kind"] == "chat"
        assert failure["http_status"] == 200 and failure["response_received"]
        assert failure["financial_outcome_unknown"]
        assert ledger.accounted(state["operations"]["new"]) == 330000
    assert "unsafe accounting detail" not in ledger.file.read_text()
    with ledger.transaction() as state:
        with pytest.raises(Stopped, match="provider_unknown"):
            ledger.reserve(state, "next", "permit", "owner", time.time(), OWNER,
                           {"other": dict(kind="extended", reserve=90000)})


def test_calr_file_handle_collision(tmp_path):
    from ds_dc.corpus import digest

    ledger = Ledger(tmp_path / "ledger")
    adapter = NativeD1(tmp_path, ledger, manifest={"files": []}, fixture=mock_transport())
    raw = b"fixture PDF"
    sha = digest(raw)
    with ledger.transaction() as state:
        state["bindings"]["prior"] = {"id": "file-api-" + sha, "sha256": "b" * 64, "expires": time.time() + 3600}
        ledger.reserve(state, "prep", "permit", "owner", time.time(), OWNER,
                       {"upload": dict(kind="upload", reserve=225, pages=1)})
        with pytest.raises(Stopped, match="provider_unknown"):
            adapter.upload(state, "upload", sha, raw, time.time(), 1)
        assert state["operations"]["upload"]["provider_failure"]["safe_reason_code"] == "id_collision"
        assert len(state["bindings"]) == 1
        assert ledger.accounted(state["operations"]["upload"]) == 225


def recovery_fixture(factory, ledger, corpus):
    from ds_dc import recovery

    adapter = factory("Q01").provider
    prior = adapter.live[0] | {"head": recovery.ORIGINAL_HEAD, "run": "original-q01"}
    permit_sha = recovery.fingerprint(prior)
    _, _, registry, _ = corpus
    files = {doc["sha256"]: doc["pages"] for doc in registry[BKD]["included_docs"]}
    reserved = dict(run=prior["run"], campaign=recovery.CAMPAIGN, profile="owner")
    operations = {recovery.ORIGINAL_CHAT: reserved | dict(
        kind="calibration", slot="extended", state="cancelled", reserve=330_000,
        permit_sha=permit_sha, calibration_scope=recovery.scope(prior, recovery.ORIGINAL_HEAD))}
    for sha, pages in files.items():
        key = recovery.ORIGINAL_CHAT + "/upload/" + sha
        operations[key] = reserved | dict(kind="upload", pages=pages, reserve=pages * 225,
                                          state="unknown" if key == recovery.ORIGINAL_UPLOAD else "cancelled")
    state = dict(operations=operations, runs={prior["run"]: permit_sha}, bindings={})
    ledger.save(state)
    archived = ledger.file.read_bytes()
    auth = recovery.authorization_payload(state, archived, prior, adapter.live[1], "fixture-owner")
    return auth, prior, archived, operations


def test_incident_recovery_binding_and_success(tmp_path, corpus, monkeypatch):
    from ds_dc import recovery

    factory, ask, calls, ledger = controlled_operator(tmp_path, corpus, monkeypatch)
    auth, prior, archived, original = recovery_fixture(factory, ledger, corpus)
    head = auth["head"]
    # The original operation key is occupied and the unknown still blocks all ordinary reservations.
    assert ask(factory("Q01"), "Q01")["status"] == "duplicate_operation"
    assert ask(factory("Q01", recovery_sha="f" * 64), "Q01")["status"] == "recovery_not_authorized"
    with ledger.transaction() as state:
        with pytest.raises(Stopped, match="provider_unknown"):
            ledger.reserve(state, "ordinary", "permit", "owner", time.time(), OWNER,
                           {"ordinary": dict(kind="extended", reserve=90000)}, campaign=recovery.CAMPAIGN)
    assert not calls
    for field, value in auth.items():
        with pytest.raises(ValueError):
            recovery.authorize(ledger, auth | {field: None if value is not None else "wrong"}, prior, archived, head)
    assert ledger.file.read_bytes() == archived
    auth_sha = recovery.authorize(ledger, auth, prior, archived, head)
    with pytest.raises(Stopped, match="recovery_already_authorized"):
        recovery.authorize(ledger, auth, prior, archived, head)
    assert ask(factory("Q01", recovery_sha=auth_sha, account="other"), "Q01")[
        "status"] == "recovery_authorization_mismatch"
    assert ask(factory("Q02", prior=recovery.fingerprint(prior), recovery_sha=auth_sha), "Q02")[
        "status"] == "cal01_not_confirmed"
    assert not calls
    recovered = factory("Q01", recovery_sha=auth_sha)
    result = ask(recovered, "Q01")
    assert result["status"] == "calibration_observed"
    assert result["context"]["campaign_budget"]["held_micro_usd"] == 14625
    assert result["context"]["campaign_budget"]["page_attempts"] == 145
    assert ask(factory("Q01", recovery_sha=auth_sha), "Q01", "new-id")["status"] == "duplicate_operation"
    assert ask(factory("Q02", prior=recovered.provider.permit_sha), "Q02")["status"] == "cal01_not_confirmed"
    assert ask(factory("Q02", prior=recovered.provider.permit_sha, recovery_sha=auth_sha), "Q02")[
        "status"] == "calibration_observed"
    with ledger.transaction() as state:
        assert all(state["operations"][key] == row for key, row in original.items())
        assert [event["kind"] for event in state["recovery_events"]] == ["authorized", "consumed"]
        summary = ledger.summary(state, "", OWNER["budget"], recovery.CAMPAIGN)
        assert summary["held_micro_usd"] == 14625
        assert summary["page_attempts"] == 548
        assert summary["operations"]["upload"] == 15
        assert summary["operations"]["calibration"] == 2
    assert [request.url.path for request in calls] == ["/files"] * 4 + ["/chat/completions"] + [
        "/files"] * 10 + ["/chat/completions"]


@pytest.mark.parametrize("other_unknown", [False, True])
def test_incident_recovery_concurrent_hold(tmp_path, corpus, monkeypatch, other_unknown):
    from concurrent.futures import ThreadPoolExecutor
    from ds_dc import recovery

    factory, ask, calls, ledger = controlled_operator(tmp_path, corpus, monkeypatch, fault="upload")
    auth, prior, archived, _ = recovery_fixture(factory, ledger, corpus)
    auth_sha = recovery.authorize(ledger, auth, prior, archived, auth["head"])
    if other_unknown:
        with ledger.transaction() as state:
            state["operations"]["another-failure"] = dict(state="unknown", kind="upload",
                profile="owner", campaign=recovery.CAMPAIGN, run="another", reserve=225, pages=1)
            ledger.save(state)

    def recover(index):
        operator = factory("Q01", recovery_sha=auth_sha)
        return ask(operator, "Q01", str(index))["status"]

    with ThreadPoolExecutor(max_workers=2) as workers:
        statuses = sorted(workers.map(recover, (1, 2)))
    if other_unknown:
        assert statuses == ["provider_unknown", "provider_unknown"]
        assert not calls
    else:
        assert statuses == ["duplicate_operation", "provider_unknown"]
        assert [request.url.path for request in calls] == ["/files"]
        operator = factory("Q01", recovery_sha=auth_sha)
        assert ask(factory("Q02", prior=operator.provider.permit_sha, recovery_sha=auth_sha), "Q02")[
            "status"] == "cal01_not_confirmed"
        with ledger.transaction() as state:
            assert len(state["recovery_events"]) == 2
            summary = ledger.summary(state, "", OWNER["budget"], recovery.CAMPAIGN)
            assert summary["held_micro_usd"] == 2 * 14625
