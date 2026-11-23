import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from secrets import token_urlsafe
from threading import Event
from uuid import uuid4

import httpx
import pytest

from ds_dc.trial_journal import TrialJournal
from ds_dc import trial_web
from ds_dc.trial_web import create_app

ORIGIN = "http://127.0.0.1:8765"
PUBLIC_SOURCE = "https://www.mnppsaturn.ru/docs/test.pdf"
QUESTION = "Для чего нужен проверочный прибор?"


class ConsultantDouble:
    catalog = [{"id": "saturn:device:test", "label": "Прибор", "url": PUBLIC_SOURCE, "pages": 1,
                "pdf_count": 1, "documents": [], "limitations": []}]

    def __init__(self):
        self.calls = []
        self.resets = 0

    def accepts_text(self, text):
        return "sensitive-value" not in text

    def ask(self, question, *, hint=None, scope="full", request_id=None):
        self.calls.append((request_id, question, hint, scope))
        return {
            "public": {
                "status": "partial", "answer": "Подтверждённая часть B.",
                "citations": [{"url": PUBLIC_SOURCE, "page": 1},
                              {"url": "javascript:alert(1)", "page": 2}],
                "unresolved": ["Данные ограничены."],
                "choices": [{"id": "saturn:device:test", "label": "Прибор"}],
                "limitations": [], "A": "unconfirmed candidate",
            },
            "expert": {
                "A": {"claim": "unconfirmed candidate"},
                "B": {"answer": "Подтверждённая часть B."},
                "telemetry": {"status": "completed", "raw_reasoning": "private reasoning"},
            },
        }

    def reset(self):
        self.resets += 1


class BrowserClient(httpx.Client):
    """Run synchronous test requests against ASGI without opening a socket."""

    def __init__(self, app, peer=("127.0.0.1", 51011)):
        self.app = app

        def dispatch(request):
            async def dispatch_asgi():
                transport = httpx.ASGITransport(app=app, client=peer)
                response = await transport.handle_async_request(request)
                return httpx.Response(response.status_code, headers=response.headers, content=await response.aread())

            return asyncio.run(dispatch_asgi())

        super().__init__(base_url=ORIGIN, transport=httpx.MockTransport(dispatch))


def make_trial(tmp_path, consultant=None):
    journal = TrialJournal(tmp_path / "journal", tmp_path / "exports")
    consultant = ConsultantDouble() if consultant is None else consultant
    app = create_app(consultant, journal)
    client = BrowserClient(app)
    response = client.get("/session")
    return client, consultant, response.json()


def post(client, session, route, body):
    return client.post(route, json=body, headers={"Origin": ORIGIN, "X-CSRF-Token": session["csrf"]})


def test_public_refresh_uses_only_verified_answer_and_never_resubmits(tmp_path):
    client, consultant, session = make_trial(tmp_path)
    assert session["mode"] == "offline"
    assert client.cookies
    assert client.get("/").status_code == 200
    assert client.get("/trial.js").status_code == 200
    assert client.get("/catalog").json()["catalog"][0]["id"] == "saturn:device:test"
    request_id = str(uuid4())
    response = post(client, session, "/ask", {
        "request": request_id, "question": QUESTION, "hint": "saturn:device:test", "scope": "manual",
    })
    assert response.status_code == 200
    assert "unconfirmed candidate" not in response.text
    assert response.json()["turn"]["answer"]["citations"] == [{"url": PUBLIC_SOURCE, "page": 1}]
    assert client.get("/session").json()["timeline"] == [response.json()["turn"]]
    report = client.get(f"/expert/{request_id}").json()["report"]
    assert report["A"] == {"claim": "unconfirmed candidate"}
    assert "raw_reasoning" not in report["telemetry"]
    assert report["B"]["answer"] == "Подтверждённая часть B."
    assert consultant.calls == [(request_id, QUESTION, "saturn:device:test", "manual")]


def test_admission_requires_loopback_host_origin_cookie_and_csrf(tmp_path):
    client, consultant, session = make_trial(tmp_path)
    body = {"request": str(uuid4()), "question": QUESTION}
    assert client.get("/session", headers={"Host": "other.example"}).status_code == 403
    external = BrowserClient(client.app, ("192.0.2.4", 51011))
    assert external.get("/session", headers={"X-Forwarded-For": "127.0.0.1"}).status_code == 403
    assert client.post("/ask", json=body, headers={"Origin": ORIGIN}).status_code == 403
    assert client.post("/ask", json=body, headers={
        "Origin": "https://elsewhere.invalid", "X-CSRF-Token": session["csrf"],
    }).status_code == 403
    stranger = BrowserClient(client.app, ("127.0.0.1", 51012))
    assert stranger.get("/session").status_code == 409
    assert post(stranger, session, "/ask", body).status_code == 403
    assert post(client, session, "/ask", {**body, "question": "я" * 1201}).status_code == 400
    rejected = post(client, session, "/ask", {**body, "question": "sensitive-value"})
    assert rejected.status_code == 400
    assert "sensitive-value" not in rejected.text
    assert consultant.calls == []


def test_live_requires_launch_capability_to_open_or_renew_lease(tmp_path, monkeypatch):
    journal = TrialJournal(tmp_path / "journal", tmp_path / "exports")
    consultant = ConsultantDouble()
    with pytest.raises(ValueError):
        create_app(consultant, journal, mode="live")
    capability = token_urlsafe(32)
    app = create_app(consultant, journal, mode="live", owner_token=capability)
    client = BrowserClient(app)
    headers = {"Origin": ORIGIN}
    assert client.get("/session").status_code == 401
    assert client.post("/activate", json={"owner_token": token_urlsafe(32)}, headers=headers).status_code == 401
    assert client.post("/activate", json={"owner_token": capability}).status_code == 403
    response = client.post("/activate", json={"owner_token": capability}, headers=headers)
    assert response.status_code == 200
    assert capability not in response.text and capability not in response.headers["Set-Cookie"]
    assert response.json()["mode"] == "live"
    assert client.get("/session").status_code == 200
    assert BrowserClient(app).get("/session").status_code == 409
    future = trial_web.monotonic() + trial_web.SESSION_SECONDS + 1
    monkeypatch.setattr(trial_web, "monotonic", lambda: future)
    assert client.get("/session").status_code == 401
    assert consultant.resets == 1
    assert client.post("/activate", json={"owner_token": capability}, headers=headers).status_code == 200
    assert consultant.calls == []


def test_request_id_remains_single_use_across_refresh_reset_and_restart(tmp_path):
    client, consultant, session = make_trial(tmp_path)
    body = {"request": str(uuid4()), "question": QUESTION}
    answer = post(client, session, "/ask", body)
    assert answer.status_code == 200
    assert post(client, session, "/ask", body).json() == answer.json()
    assert post(client, session, "/ask", {**body, "question": "Другая тема"}).status_code == 409
    assert post(client, session, "/reset", {}).status_code == 200
    reset = client.get("/session").json()
    assert reset["timeline"] == []
    assert consultant.resets == 1
    assert post(client, reset, "/ask", body).status_code == 409
    restarted, second, second_session = make_trial(tmp_path)
    assert post(restarted, second_session, "/ask", body).status_code == 409
    assert len(consultant.calls) == 1
    assert second.calls == []


def test_inflight_is_visible_and_cannot_trigger_another_call(tmp_path):
    entered, release = Event(), Event()

    class BlockingConsultant(ConsultantDouble):
        def ask(self, *args, **kwargs):
            entered.set()
            if not release.wait(5):
                pytest.fail("test did not release the consultant")
            return super().ask(*args, **kwargs)

    client, consultant, session = make_trial(tmp_path, BlockingConsultant())
    body = {"request": str(uuid4()), "question": QUESTION}
    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(post, client, session, "/ask", body)
        try:
            assert entered.wait(3)
            assert client.get("/session").json()["pending"]["request"] == body["request"]
            assert post(client, session, "/ask", body).status_code == 409
            assert post(client, session, "/ask", {**body, "request": str(uuid4())}).status_code == 409
            assert post(client, session, "/reset", {}).status_code == 409
        finally:
            release.set()
        assert first.result().status_code == 200
    assert len(consultant.calls) == 1


def test_feedback_is_append_only_and_export_escapes_untrusted_markdown(tmp_path):
    client, consultant, session = make_trial(tmp_path)
    request_id = str(uuid4())
    assert post(client, session, "/ask", {"request": request_id, "question": QUESTION}).status_code == 200
    request_md = tmp_path / "journal" / f"request-{request_id}.md"
    original = request_md.read_bytes()
    assert "Подтверждённая часть B." in original.decode()
    feedback = {"request": request_id, "rating": "partial", "comment": chr(96) * 3 + '<img src="x">[]()',
                "expected": "", "reference": PUBLIC_SOURCE}
    assert post(client, session, "/feedback", feedback).status_code == 200
    assert post(client, session, "/feedback", {**feedback, "comment": "sensitive-value"}).status_code == 400
    assert post(client, session, "/feedback", {**feedback, "rating": "correct", "expected": "Данные"}).status_code == 200
    assert request_md.read_bytes() == original
    edits = list((tmp_path / "journal").glob(f"feedback-{request_id}-*.md"))
    assert len(edits) == 2
    assert client.get(f"/expert/{request_id}").json()["feedback"]["rating"] == "correct"
    export = post(client, session, "/export", {"requests": [request_id]})
    assert export.status_code == 200
    path = tmp_path / "exports" / export.json()["file"]
    content = path.read_text()
    assert "<img" not in content and "sensitive-value" not in content
    assert PUBLIC_SOURCE in content
    assert "correct" in content and "partial" in content
    assert all((file.stat().st_mode & 0o777) == 0o600 for file in [path, request_md, *edits])
    assert len(consultant.calls) == 1


def test_private_journal_refuses_symlink_or_shared_directory(tmp_path):
    client, _, _ = make_trial(tmp_path)
    journal_class = type(client.app.state.journal)
    redirect = tmp_path / "redirect"
    redirect.symlink_to(tmp_path / "journal", target_is_directory=True)
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)
    for location in (redirect, shared):
        with pytest.raises(ValueError):
            journal_class(location, tmp_path / "exports")


def test_full_length_feedback_fields_fit_in_their_own_request_budget(tmp_path):
    client, consultant, session = make_trial(tmp_path)
    request_id = str(uuid4())
    assert post(client, session, "/ask", {"request": request_id, "question": QUESTION}).status_code == 200
    feedback = post(client, session, "/feedback", {
        "request": request_id, "rating": "correct", "comment": "技" * 2000, "expected": "技" * 2000,
        "reference": PUBLIC_SOURCE,
    })
    assert feedback.status_code == 200
    assert len(consultant.calls) == 1
