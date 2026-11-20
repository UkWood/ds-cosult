"""Loopback web interface. LAB browser credentials and recovery are local to this installation."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

BODY_LIMIT = 8192
COOKIE = "pilot_session"
RECOVER = "Откройте файл lab-recovery-code в каталоге данных в локальном терминале и введите код."


def error(text, status):
    return JSONResponse({"text": text}, status_code=status)


def cookie(response, name, token):
    response.set_cookie(name, token, httponly=True, samesite="strict")
    return response


def write_code(path):
    code = secrets.token_urlsafe(24)
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temp:
        temp.write(code + "\n")
    os.replace(temp.name, path)
    return code


def create_app(pilot):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    lab = pilot.lab
    name = "pilot_lab_session" if lab else COOKIE
    if lab:
        code_path = pilot.database.parent / "lab-recovery-code"
        with pilot.tx() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS lab_browser (
                id INTEGER PRIMARY KEY CHECK(id=1), session TEXT NOT NULL, token TEXT NOT NULL)""")
            write_code(code_path)

    @app.middleware("http")
    async def loopback(request, call_next):
        peer = request.client.host if request.client else ""
        host = request.url.hostname
        test = peer == "testclient" and host == "testserver"
        forwarded = any(k == "forwarded" or k.startswith("x-forwarded-") or k == "x-real-ip"
                        for k in request.headers)
        bound = request.scope.get("server")
        wrong_port = bound and request.url.port != bound[1] and not (
            request.url.port is None and bound[1] == 80)
        origin = request.headers.get("origin")
        if (not test and (host not in {"127.0.0.1", "localhost", "::1"}
                          or peer not in {"127.0.0.1", "::1"} or wrong_port)) or forwarded:
            response = error("Доступ только через loopback.", 403)
        elif origin and origin != str(request.base_url).rstrip("/"):
            response = error("Запрос с другого сайта отклонён.", 403)
        else:
            response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        return response

    def session(request):
        token = request.cookies.get(name)
        if not lab:
            return token if token and re.fullmatch(r"[a-f0-9]{32}", token) else None
        with pilot.tx() as db:
            row = db.execute("SELECT session FROM lab_browser WHERE token=?", (token,)).fetchone()
        return row["session"] if row else None

    @app.get("/")
    async def home(request: Request):
        response = HTMLResponse(Path(__file__).with_name("chat.html").read_text(encoding="utf-8"))
        if lab:
            with pilot.tx() as db:
                token = secrets.token_urlsafe(32)
                created = db.execute("INSERT OR IGNORE INTO lab_browser VALUES (1,?,?)",
                                     (uuid4().hex, token))
                if created.rowcount:
                    cookie(response, name, token)
        elif not session(request):
            cookie(response, name, uuid4().hex)
        return response

    @app.get("/api/session")
    async def state(request: Request):
        sid = session(request)
        state = {"lab": lab, "authenticated": bool(sid)}
        if not sid:
            return {**state, "text": RECOVER if lab else "Обновите страницу."}
        with pilot.tx() as db:
            last = db.execute("SELECT request,response FROM turns WHERE session=? ORDER BY rowid DESC LIMIT 1",
                              (sid,)).fetchone()
        # Both tabs viewing the same head use the same submission id. An explicit next
        # turn after receipt gets a fresh id, including when comparing P0 with P1/P2.
        head = last["request"] if last else ""
        state["dialog"] = hashlib.sha256(sid.encode()).hexdigest()
        state["next_request"] = hashlib.sha256(f"{sid}/{head}".encode()).hexdigest()
        state["unfinished"] = bool(last and last["response"] is None)
        state["scope"] = {**pilot.catalog.public_summary(),
                          "excluded_channels": pilot.catalog.coverage["excluded_channels"]}
        live = pilot.live if lab else None
        state["live"] = bool(live)
        if live:
            state["budget"] = live.summary()
            state["live"] = state["budget"]["remaining_calls"] > 0
        return state

    @app.get("/api/history")
    async def history(request: Request):
        sid = session(request)
        if not sid:
            return error(RECOVER if lab else "Откройте страницу диалога.", 403)
        return {"turns": await run_in_threadpool(pilot.history, sid)}

    async def payload(request):
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return error("Ожидается JSON.", 415)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > BODY_LIMIT:
                return error("Ограничение запроса: 8 КиБ.", 413)
            body.extend(chunk)
        try:
            data = json.loads(body)
            if isinstance(data, dict):
                return data
        except (ValueError, UnicodeError, RecursionError):
            pass
        return error("Некорректный запрос.", 400)

    @app.post("/api/recover")
    async def recover(request: Request):
        if not lab:
            return error("Требуется лабораторный режим.", 403)
        data = await payload(request)
        if isinstance(data, JSONResponse):
            return data
        code = data.get("code")
        with pilot.tx() as db:
            row = db.execute("SELECT id FROM lab_browser").fetchone()
            if (not row or not isinstance(code, str) or not code.isascii()
                    or not secrets.compare_digest(code, code_path.read_text().strip())):
                return error("Код не принят. Проверьте файл в локальном терминале.", 403)
            token = secrets.token_urlsafe(32)
            write_code(code_path)
            db.execute("UPDATE lab_browser SET token=?", (token,))
        return cookie(JSONResponse({"ok": True}), name, token)

    @app.post("/api/dialog/{action}")
    async def dialog(action: str, request: Request):
        if not lab or action not in {"new", "reset"}:
            return error("Действие недоступно.", 403)
        data = await payload(request)
        if isinstance(data, JSONResponse):
            return data
        sid = session(request)
        if not sid:
            return error(RECOVER, 403)
        if action == "reset":
            await run_in_threadpool(pilot.reset, sid)
        token = secrets.token_urlsafe(32)
        with pilot.tx() as db:
            changed = db.execute("UPDATE lab_browser SET session=?,token=? WHERE session=? AND token=?",
                                 (uuid4().hex, token, sid, request.cookies.get(name)))
            if not changed.rowcount:
                return error("Диалог изменился. Обновите страницу.", 409)
        return cookie(JSONResponse({"ok": True}), name, token)

    @app.post("/api/ask")
    async def ask(request: Request):
        data = await payload(request)
        if isinstance(data, JSONResponse):
            return data
        if (set(data) not in ({"question", "request_id"}, {"question", "request_id", "mode"},
                              {"question", "request_id", "mode", "dialog"})
                or not isinstance(data["request_id"], str) or not data["request_id"]):
            return error("Некорректный запрос.", 400)
        sid = session(request)
        if not sid:
            return error(RECOVER if lab else "Откройте страницу диалога.", 403)
        if "dialog" in data and data["dialog"] != hashlib.sha256(sid.encode()).hexdigest():
            return error("Открыт другой диалог. Обновите страницу.", 409)
        mode = data.get("mode", "P0")
        if mode != "P0" and (not lab or not pilot.live or mode not in ("P1", "P2")):
            return error("Экспериментальный маршрут недоступен.", 403)
        request_id = data["request_id"]
        result = await run_in_threadpool(pilot.ask, data["question"], sid, request_id, mode=mode)
        status_code = 429 if "retry_after" in result else 200
        response = JSONResponse(result, status_code=status_code)
        if status_code == 429:
            response.headers["Retry-After"] = str(result["retry_after"])
        if "question_needs_hash" in result:
            await run_in_threadpool(pilot.delivery, request_id, "response_staged_for_asgi")
        return response

    return app
