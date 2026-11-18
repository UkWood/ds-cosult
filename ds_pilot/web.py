"""Loopback HTTP interface with bounded JSON input and private session cookie."""
import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

BODY_LIMIT = 8192
HOSTS = {"127.0.0.1", "localhost", "testserver"}


def create_app(pilot):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def loopback(request, call_next):
        if request.url.hostname not in HOSTS or (
            request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}
        ):
            return JSONResponse({"text": "Доступ только через loopback."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.get("/")
    async def home(request: Request):
        page = Path(__file__).with_name("chat.html").read_text(encoding="utf-8")
        response = HTMLResponse(page)
        if not request.cookies.get("pilot_session"):
            response.set_cookie("pilot_session", uuid4().hex, httponly=True, samesite="strict")
        return response

    @app.post("/api/ask")
    async def ask(request: Request):
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            return JSONResponse({"text": "Запрос с другого сайта отклонён."}, status_code=403)
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"text": "Ожидается JSON."}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > BODY_LIMIT:
                return JSONResponse({"text": "Ограничение запроса: 8 КиБ."}, status_code=413)
            body.extend(chunk)
        try:
            payload = json.loads(body)
            if not isinstance(payload, dict) or set(payload) != {"question", "request_id"}:
                raise ValueError("shape")
            request_id = str(uuid4()) if not payload["request_id"] else payload["request_id"]
            if not isinstance(request_id, str):
                raise ValueError("request_id")
        except (ValueError, UnicodeError):
            return JSONResponse({"text": "Некорректный запрос."}, status_code=400)
        session = request.cookies.get("pilot_session") or uuid4().hex
        result = await run_in_threadpool(pilot.ask, payload["question"], session, request_id)
        status_code = 429 if "retry_after" in result else 200
        response = JSONResponse(result, status_code=status_code)
        response.set_cookie("pilot_session", session, httponly=True, samesite="strict")
        if status_code == 429:
            response.headers["Retry-After"] = str(result["retry_after"])
        if "question_needs_hash" in result:
            await run_in_threadpool(pilot.delivery, request_id, "response_staged_for_asgi")
        return response

    return app
