"""Loopback-only HTTP interface for the document-centric owner trial."""

from dataclasses import dataclass, field
from hmac import compare_digest
import json
import math
from pathlib import Path
import re
from secrets import token_urlsafe
from threading import RLock
from time import monotonic
import unicodedata
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from .runtime import canonical_peer
from .trial_journal import REQUEST_ID, SENSITIVE_TEXT, normalized, safe_source_url, utc


ASSETS = Path(__file__).parent
COOKIE = "ds_dc05a"
SESSION_SECONDS = 900
BODY_LIMIT = 8192
FEEDBACK_BODY_LIMIT = 17000
PUBLIC_FIELDS = {
    "status", "answer", "message", "citations", "unresolved", "choices", "scope_options", "limitations",
}
EXPERT_FIELDS = {
    "schema", "derivative_copy", "redaction_rules", "mode", "question", "provenance", "telemetry",
    "documents", "diagnostics", "verdict", "reason", "A", "B", "status", "limitations",
}
PRIVATE_KEYS = {
    "api_key", "apikey", "key", "authorization", "headers", "header", "request_headers", "response_headers",
    "file_id", "handle", "handles", "file_handle", "file_handles", "private_values", "secret", "public_answer",
    "provider_body", "request_body", "response_body", "cookie", "token", "raw", "raw_http",
    "raw_reasoning", "reasoning_content", "reasoning_text", "chain_of_thought",
}
RATINGS = {"correct", "partial", "incorrect", "not_found"}
ASSET_ROUTES = {
    "/": ("trial.html", "text/html"),
    "/owner.css": ("owner.css", "text/css"),
    "/trial.css": ("trial.css", "text/css"),
    "/trial.js": ("trial.js", "text/javascript"),
}
SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'self'; object-src 'none'; base-uri 'none'; "
                               "frame-ancestors 'none'; form-action 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}
HINT = re.compile(r"[a-zA-Z0-9_:-]{1,100}")
OWNER_CAPABILITY = re.compile(r"[A-Za-z0-9_-]{43}")


@dataclass
class Session:
    token: str = field(default_factory=lambda: token_urlsafe(24))
    csrf: str = field(default_factory=lambda: token_urlsafe(24))
    id: str = field(default_factory=lambda: str(uuid4()))
    touched: float = field(default_factory=lambda: monotonic())
    turns: dict = field(default_factory=dict)
    pending: dict | None = None


def _error(status, code):
    return JSONResponse({"status": code}, status_code=status, headers=SECURITY_HEADERS)


def _request_id(value):
    return isinstance(value, str) and REQUEST_ID.fullmatch(value) is not None


def _matches(value, expected):
    return isinstance(value, str) and value.isascii() and compare_digest(value, expected)


def _text_safe(consultant, value, limit):
    if not isinstance(value, str) or len(value) > limit:
        return False
    if any(unicodedata.category(char).startswith("C") and char not in "\n\r\t" for char in value):
        return False
    return not SENSITIVE_TEXT.search(normalized(value)) and consultant.accepts_text(value)


def _project(consultant, data):
    """Keep typed presentation data and discard private or unsafe fields defensively."""
    if isinstance(data, dict):
        result = {}
        for key, item in data.items():
            if not _text_safe(consultant, key, 120) or key.casefold().replace("-", "_") in PRIVATE_KEYS:
                continue
            if key in {"url", "canonical", "production_url", "source_url", "reference"}:
                if safe_source_url(item) and _text_safe(consultant, item, 512):
                    result[key] = item
            else:
                result[key] = _project(consultant, item)
        return result
    if isinstance(data, (list, tuple)):
        return [_project(consultant, item) for item in data]
    if isinstance(data, str):
        return data if _text_safe(consultant, data, 32000) else None
    if isinstance(data, float):
        return data if math.isfinite(data) else None
    return data if data is None or isinstance(data, (int, bool)) else None


def _public(consultant, data):
    answer = _project(consultant, {key: data[key] for key in PUBLIC_FIELDS if key in data})
    if isinstance(answer.get("citations"), list):
        answer["citations"] = [source for source in answer["citations"]
                               if isinstance(source, dict) and "url" in source]
    return answer


def create_app(consultant, journal, *, mode="offline", host="127.0.0.1", port=8765, owner_token=None):
    if host != "127.0.0.1" or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("trial_requires_ipv4_loopback")
    if mode not in {"offline", "mock", "live"}:
        raise ValueError("invalid_trial_mode")
    if mode == "live" and (not isinstance(owner_token, str) or not OWNER_CAPABILITY.fullmatch(owner_token)):
        raise ValueError("trial_live_owner_capability_required")
    authority = f"{host}:{port}"
    origin = f"http://{authority}"
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None, redirect_slashes=False)
    app.state.journal = journal
    lock = RLock()
    session = None

    @app.middleware("http")
    async def restrict_access(request, call_next):
        try:
            local = request.client is not None and canonical_peer(request.client.host) == host
        except ValueError:
            local = False
        if (not local or request.headers.getlist("host") != [authority]
                or any(value not in {"none", "same-origin"} for value in request.headers.getlist("sec-fetch-site"))
                or (request.method == "POST" and request.headers.getlist("origin") != [origin])):
            return _error(403, "session_denied")
        response = await call_next(request)
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value
        return response

    def expire():
        nonlocal session
        if session and session.pending is None and monotonic() - session.touched >= SESSION_SECONDS:
            consultant.reset()
            session = None

    def authenticated(request):
        expire()
        if session is None or not _matches(request.cookies.get(COOKIE), session.token):
            return False
        if request.method == "POST":
            supplied = request.headers.getlist("x-csrf-token")
            return len(supplied) == 1 and _matches(supplied[0], session.csrf)
        return True

    def session_payload():
        return {
            "status": "ok", "mode": mode, "csrf": session.csrf, "session": session.id,
            "timeline": [entry["turn"] for entry in session.turns.values()], "pending": session.pending,
        }

    def session_response():
        response = JSONResponse(session_payload())
        response.set_cookie(COOKIE, session.token, httponly=True, samesite="strict", path="/")
        return response

    @app.get("/")
    @app.get("/owner.css")
    @app.get("/trial.css")
    @app.get("/trial.js")
    def asset(request: Request):
        name, mime = ASSET_ROUTES[request.url.path]
        return Response((ASSETS / name).read_bytes(), media_type=mime)

    @app.get("/session")
    def open_session(request: Request):
        nonlocal session
        with lock:
            expire()
            if session is None and mode == "live":
                return _error(401, "activation_required")
            if session is not None and not authenticated(request):
                return _error(409, "session_denied")
            try:
                journal.purge()
            except (OSError, ValueError):
                return _error(503, "journal_unavailable")
            if session is None:
                session = Session()
                return session_response()
            return session_payload()

    @app.get("/catalog")
    def catalog(request: Request):
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
            return {"status": "ok", "catalog": _project(consultant, consultant.catalog)}

    @app.get("/expert/{request_id}")
    def expert(request: Request, request_id: str):
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
            entry = session.turns.get(request_id)
            if entry is None:
                return _error(404, "request_unavailable")
            try:
                revisions = journal.feedback_history(request_id)
            except (OSError, ValueError):
                return _error(503, "journal_unavailable")
            return {"status": "ok", "session": session.id, "request": request_id,
                    "report": entry["expert"], "feedback": revisions[-1] if revisions else None}

    async def payload(request, limit=BODY_LIMIT):
        if request.headers.getlist("content-type") not in (["application/json"], ["application/json; charset=utf-8"]):
            return _error(415, "invalid_request")
        lengths = request.headers.getlist("content-length")
        if (request.headers.getlist("transfer-encoding") or len(lengths) != 1
                or re.fullmatch(r"[0-9]{1,5}", lengths[0]) is None or not 0 < int(lengths[0]) <= limit):
            return _error(413, "invalid_request")
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > limit:
                return _error(413, "invalid_request")
            data.extend(chunk)
        if len(data) != int(lengths[0]):
            return _error(400, "invalid_request")
        try:
            parsed = json.loads(data)
        except (ValueError, RecursionError):
            return _error(400, "invalid_request")
        return parsed if isinstance(parsed, dict) else _error(400, "invalid_request")

    @app.post("/activate")
    async def activate(request: Request):
        nonlocal session
        if mode != "live":
            return _error(404, "invalid_request")
        body = await payload(request)
        if isinstance(body, Response):
            return body
        if body.keys() != {"owner_token"} or not _matches(body["owner_token"], owner_token):
            return _error(401, "activation_required")
        with lock:
            expire()
            if session is not None and not authenticated(request):
                return _error(409, "session_denied")
            try:
                journal.purge()
            except (OSError, ValueError):
                return _error(503, "journal_unavailable")
            if session is None:
                session = Session()
            return session_response()

    def perform_ask(request, body):
        request_id, question, hint = (body.get(key) for key in ("request", "question", "hint"))
        scope = body.get("scope", "full")
        if (body.keys() - {"request", "question", "hint", "scope"} or not _request_id(request_id)
                or not _text_safe(consultant, question, 1200) or not question.strip()
                or (hint is not None and (not _text_safe(consultant, hint, 100) or not HINT.fullmatch(hint)
                                          or not any(item["id"] == hint for item in consultant.catalog)))
                or scope not in ("full", "manual")):
            return _error(400, "invalid_request")
        fingerprint = question, hint, scope
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
            if prior := session.turns.get(request_id):
                if prior["fingerprint"] == fingerprint:
                    return {"status": prior["status"], "turn": prior["turn"]}
                return _error(409, "request_conflict")
            if session.pending is not None:
                return _error(409, "in_flight")
            try:
                if not journal.reserve(request_id):
                    return _error(409, "request_conflict")
            except (OSError, ValueError):
                return _error(503, "journal_unavailable")
            started = utc()
            session.touched = monotonic()
            session.pending = {"request": request_id, "question": question, "started_utc": started}
            session_id = session.id

        status = "ok"
        turn = {"request": request_id, "question": question}
        report = {}
        try:
            result = consultant.ask(question, hint=hint, scope=scope, request_id=request_id)
            turn["answer"] = _public(consultant, result["public"])
            safe_report = {key: result["expert"][key] for key in EXPERT_FIELDS if key in result["expert"]}
            report = _project(consultant, safe_report)
        except Exception:
            # This call has a durable receipt and may have crossed the provider boundary.
            # Never leak exception detail or allow this request ID to be sent again.
            turn["answer"] = {"status": "local_error"}
            report = {"status": "local_error", "telemetry": {"cost_state": "unknown"}}
        try:
            journal.record(turn, report, session_id, started)
        except (OSError, ValueError, TypeError):
            status = "journal_unavailable"
        finally:
            with lock:
                session.turns[request_id] = {"fingerprint": fingerprint, "status": status,
                                             "turn": turn, "expert": report}
                session.pending = None
                session.touched = monotonic()
        return {"status": status, "turn": turn}

    def perform_reset(request, body):
        nonlocal session
        if body:
            return _error(400, "invalid_request")
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
            if session.pending is not None:
                return _error(409, "in_flight")
            consultant.reset()
            # Keep the lease cookie for other tabs, but drop completed turns and
            # rotate the CSRF value so a semantically stale form cannot submit.
            session = Session(token=session.token)
            return session_response()

    def perform_feedback(request, body):
        request_id, rating = body.get("request"), body.get("rating")
        comment, expected, reference = (body.get(key, "") for key in ("comment", "expected", "reference"))
        if (body.keys() - {"request", "rating", "comment", "expected", "reference"}
                or not _request_id(request_id)
                or (rating is not None and (not isinstance(rating, str) or rating not in RATINGS))
                or not all(_text_safe(consultant, value, 2000) for value in (comment, expected))
                or (reference and (not safe_source_url(reference) or not _text_safe(consultant, reference, 512)))
                or not isinstance(reference, str)):
            return _error(400, "invalid_request")
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
            if request_id not in session.turns:
                return _error(404, "request_unavailable")
            try:
                revision = journal.feedback(request_id, {"rating": rating, "comment": comment,
                                                          "expected": expected, "reference": reference})
            except FileNotFoundError:
                return _error(404, "request_unavailable")
            except (OSError, ValueError):
                return _error(503, "journal_unavailable")
            return {"status": "ok", "feedback": revision}

    def perform_export(request, body):
        selected = body.get("requests")
        if (body.keys() - {"requests"}
                or ("requests" in body and (not isinstance(selected, list) or not selected or len(selected) > 100
                                             or not all(map(_request_id, selected))))):
            return _error(400, "invalid_request")
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
            try:
                name = journal.export(selected)
            except FileNotFoundError:
                return _error(404, "request_unavailable")
            except (OSError, ValueError):
                return _error(503, "journal_unavailable")
            return {"status": "ok", "file": name}

    async def mutate(request, handler, limit=BODY_LIMIT):
        # Reject unauthenticated traffic before parsing its body. Handlers
        # recheck the lease after body receipt to cover concurrent resets.
        with lock:
            if not authenticated(request):
                return _error(403, "session_denied")
        body = await payload(request, limit)
        if isinstance(body, Response):
            return body
        return await run_in_threadpool(handler, request, body)

    @app.post("/ask")
    async def ask(request: Request):
        return await mutate(request, perform_ask)

    @app.post("/reset")
    async def reset(request: Request):
        return await mutate(request, perform_reset)

    @app.post("/feedback")
    async def feedback(request: Request):
        return await mutate(request, perform_feedback, FEEDBACK_BODY_LIMIT)

    @app.post("/export")
    async def export(request: Request):
        return await mutate(request, perform_export)

    return app
