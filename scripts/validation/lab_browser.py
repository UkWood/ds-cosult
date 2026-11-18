"""Real Chromium acceptance run. All provider traffic uses an injected in-memory transport."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def serve(directory, port):
    import uvicorn
    from ds_pilot.catalog import Catalog, load_git
    from ds_pilot.engine import Pilot
    from ds_pilot.paid_budget import PaidLedger
    from ds_pilot.providers import DeepSeekRoute
    from ds_pilot.web import create_app

    def transport(_key, _body):
        with (directory / "synthetic-posts").open("a") as log:
            log.write("POST\n")
        plan = {"interpretation_status": "supported", "need_ids": ["n1"]}
        return 200, json.dumps({"model": "deepseek-flash", "id": "synthetic-1",
            "usage": {"prompt_tokens": 200, "prompt_cache_miss_tokens": 200,
                      "prompt_cache_hit_tokens": 0, "completion_tokens": 10},
            "choices": [{"message": {"content": json.dumps(plan)}, "finish_reason": "stop"}]}).encode()

    catalog = Catalog(load_git(Path(os.environ["SATURN_SOURCE"])))
    ledger = PaidLedger(directory / "synthetic.sqlite")
    live = DeepSeekRoute("offline-test-token", ledger, transport)
    pilot = Pilot(catalog, directory / "lab.sqlite", lab=True, live=live)
    try:
        uvicorn.run(create_app(pilot), host="127.0.0.1", port=port, proxy_headers=False,
                    access_log=False, log_level="error")
    finally:
        live.close()


@contextmanager
def server(directory, port, executable):
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen([executable, __file__, "--server", str(directory), "--port", str(port)])
    try:
        deadline = monotonic() + 30
        while monotonic() < deadline:
            try:
                with urlopen(url + "/api/session", timeout=.5):
                    break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("Test server exited")
                sleep(.1)
        else:
            raise RuntimeError("Test server failed to start")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


def exercise(pw, tmp, args):
    from playwright.sync_api import expect
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    browser = pw.chromium.launch(executable_path=args.chromium)
    context = browser.new_context()
    page = context.new_page()
    q = "Какая масса БКД-ПК-RF.2?"
    with server(tmp, port, args.server_python) as url:
        page.goto(url)
        expect(page.locator("#send")).to_be_enabled()
        expect(page.locator("#policy")).to_have_text("Лабораторный режим")
        tab = context.new_page()
        tab.goto(url)
        for view in (tab, page):
            view.locator("#mode").select_option("P1")
            view.locator("#question").fill(q)
        # Drop a response after the local server has completed the first ask.
        def disconnect(route):
            assert route.fetch().json()["status"] == "answered"
            route.abort()

        tab.route("**/api/ask", disconnect, times=1)
        tab.locator("#send").click()
        expect(tab.locator("#notice")).not_to_be_empty()
        expect(tab.locator("#send")).to_be_enabled()
        # Same viewed conversation head and same deliberate submission in a second tab.
        for view in (tab, page):
            with view.expect_response("**/api/ask") as r:
                view.locator("#send").click()
            assert r.value.json()["status"] == "answered", r.value.json()
            expect(view.locator("article.question")).to_have_count(1)
        for _ in range(5):
            page.reload()
            expect(page.locator("article.question")).to_have_count(1)
        expect(page.locator("article.answer")).to_contain_text("P1")
        page.locator("#question").fill("Какое питание постоянного тока у него?")
        with page.expect_response("**/api/ask") as r:
            page.locator("#send").click()
        assert r.value.json()["status"] == "answered" and "(11 – 27) В" in r.value.json()["text"]
        tab.reload()
        expect(tab.locator("article.question")).to_have_count(2)
    with server(tmp, port, args.server_python):
        page.reload()
        expect(page.locator("article.question")).to_have_count(2)
        before = context.cookies()
        context.clear_cookies()
        page.reload()
        expect(page.locator("#recovery")).to_be_visible()
        assert context.request.get(url + "/api/history").status == 403
        code = (tmp / "lab-recovery-code").read_text().strip()
        page.locator("#code").fill(code)
        page.locator("#recovery button").click()
        expect(page.locator("article.question")).to_have_count(2)
        assert context.request.post(url + "/api/recover", data={"code":code}).status == 403
        stale = browser.new_context()
        stale.add_cookies(before)
        assert stale.request.get(url + "/api/history").status == 403
        with sqlite3.connect(tmp / "lab.sqlite") as db:
            assert db.execute("SELECT COUNT(*) FROM turns").fetchone()[0] == 2
        assert (tmp / "synthetic-posts").read_text().splitlines() == ["POST"]
        # Simulate a killed process after admission, with its synthetic or real provider
        # outcome unknown. Reloading must only read that state.
        with sqlite3.connect(tmp / "lab.sqlite") as db:
            db.execute("UPDATE turns SET response=NULL WHERE rowid=(SELECT max(rowid) FROM turns)")
        page.reload()
        expect(page.locator("#notice")).to_contain_text("незавершённый")
        expect(page.locator("#send")).to_be_disabled()
        budget = context.request.get(url + "/api/session").json()["budget"]
        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("#reset").click()
        expect(page.locator("article.question")).to_have_count(0)
        expect(page.locator("#send")).to_be_enabled()
        page.locator("#new").click()
        expect(page.locator("#send")).to_be_enabled()
        assert context.request.get(url + "/api/session").json()["budget"] == budget
        assert (tmp / "synthetic-posts").read_text().splitlines() == ["POST"]
    print(f"Chromium {browser.version}: five F5s, dropped response/retry, two tabs, pronoun, process restart, cookie loss,"
          " single-use recovery, stale cookie, unfinished turn, reset and new dialog passed;"
          " 2 admissions, 1 simulated POST, 0 real POSTs.")
    browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python", default=sys.executable)
    parser.add_argument("--chromium", default=None, help="Optional system Chromium path")
    parser.add_argument("--server", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--port", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.server:
        serve(args.server, args.port)
    else:
        from playwright.sync_api import sync_playwright
        with TemporaryDirectory() as tmp, sync_playwright() as pw:
            exercise(pw, Path(tmp), args)
