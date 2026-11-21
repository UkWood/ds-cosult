"""Owner-only loopback entry point for the shared Pilot runtime."""
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import time

from .corpus import encoded
from .runtime import canonical_peer

ASSETS = Path(__file__).parent
COOKIE = "ds_dc02"
ROUTES = {"/": ("owner.html", "text/html"), "/owner.css": ("owner.css", "text/css"),
          "/owner.js": ("owner.js", "text/javascript")}


def server_for(pilot, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            return

        @property
        def origin(self):
            return f"http://127.0.0.1:{self.server.server_port}"

        def local(self):
            return (canonical_peer(self.client_address[0]) == "127.0.0.1"
                    and self.headers.get_all("Host") == [self.origin.removeprefix("http://")]
                    and self.headers.get("Sec-Fetch-Site") not in {"cross-site", "same-site"})

        def token(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
            except CookieError:
                return None
            item = cookie.get(COOKIE)
            return item.value if item and re.fullmatch(r"[A-Za-z0-9_-]{32}", item.value) else None

        def output(self, status, content, mime, token=None):
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; "
                             "base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
            self.send_header("Connection", "close")
            if token:
                self.send_header("Set-Cookie", f"{COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict")
            self.end_headers()
            self.wfile.write(content)

        def json(self, status, result, token=None):
            self.output(status, encoded(result).encode(), "application/json", token)

        def do_GET(self):
            if not self.local():
                return self.json(403, {"status": "session_denied"})
            if self.path in ROUTES:
                file, mime = ROUTES[self.path]
                return self.output(200, (ASSETS / file).read_bytes(), mime)
            if self.path != "/session":
                return self.json(404, {"status": "invalid_request"})
            peer = self.client_address[0]
            with pilot.lock:
                token = pilot.open(peer, resume=self.token())
                if token is None:
                    return self.json(409, {"status": "session_denied"})
                timeline = [response for _, response, journaled in pilot.sessions[peer].receipts.values()
                            if journaled]
            return self.json(200, {"status": "ok", "timeline": timeline,
                                   "provider": "live" if pilot.provider.live else "fixture"}, token)

        def do_POST(self):
            if not self.local() or self.headers.get_all("Origin") != [self.origin]:
                return self.json(403, {"status": "session_denied"})
            if self.path not in {"/ask", "/reset"}:
                return self.json(404, {"status": "invalid_request"})
            size = self.headers.get("Content-Length", "")
            if (self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length") or []) != 1
                    or not re.fullmatch(r"[0-9]{1,4}", size) or not 0 < int(size) <= 8192):
                return self.json(413, {"status": "invalid_request"})
            if self.headers.get_content_type() != "application/json":
                return self.json(415, {"status": "invalid_request"})
            try:
                body = json.loads(self.rfile.read(int(size)))
            except (ValueError, OSError, RecursionError):
                return self.json(400, {"status": "invalid_request"})
            if not isinstance(body, dict):
                return self.json(400, {"status": "invalid_request"})
            peer = self.client_address[0]
            if self.path == "/reset":
                if body:
                    return self.json(400, {"status": "invalid_request"})
                token = pilot.reset(peer, self.token())
                return self.json(200, {"status": "ok"}, token) if token else self.json(
                    403, {"status": "session_denied"})
            if set(body) != {"request", "question", "mode"}:
                return self.json(400, {"status": "invalid_request"})
            try:
                result = pilot.ask(peer, self.token(), body["request"], body["question"], mode=body["mode"])
            except (OSError, ValueError, TypeError, RecursionError):
                result = {"status": "local_error"}
            return self.json(200, result)

        def setup(self):
            self.request.settimeout(10)
            super().setup()

    class Server(ThreadingHTTPServer):
        next_maintenance = 0

        def service_actions(self):
            now = time.time()
            if now >= self.next_maintenance and pilot.lock.acquire(blocking=False):
                try:
                    pilot.expire(now)
                    pilot.journal.purge(now)
                except OSError:
                    pass
                finally:
                    pilot.lock.release()
                    self.next_maintenance = now + 60

    return Server(("127.0.0.1", port), Handler)


def serve(pilot, port):
    with server_for(pilot, port) as server:
        print(f"http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()
