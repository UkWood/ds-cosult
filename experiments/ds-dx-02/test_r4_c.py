"""Offline SSE and owner continuation regression fixtures."""
import http.client
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from protocol import Ledger, Stop, chat, encode, load, reply, reserve, transport
from test_d import fake_reply


def event(value):
    return b"data: " + (value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()) + b"\r\n\r\n"


def chunks():
    initial = dict(id="fixture", model="deepseek-flash")
    usage = fake_reply(b"", "")["usage"]

    def part(delta, finish=None, counts=None):
        return dict(initial, choices=[dict(index=0, delta=delta, finish_reason=finish)], usage=counts)

    return [b": keep-alive\r\n\r\n", event(part({"role": "assistant", "reasoning_content": "private-thought"})),
            event(part({"content": "инженерный факт"})), event(part({"content": ""}, "stop", usage)),
            event(b"[DONE]")]


class Streaming(unittest.TestCase):
    def operation(self, ledger, body, read, *, headers_fault=False):
        connection = Mock(spec=http.client.HTTPSConnection)
        if headers_fault:
            connection.getresponse.side_effect = http.client.RemoteDisconnected("fixture")
        response = connection.getresponse.return_value
        response.status, response.length = 200, None
        response.getheader.side_effect = {"Content-Type": "text/event-stream; charset=utf-8"}.get
        response.read1.side_effect = read
        with patch("protocol.http.client.HTTPSConnection", return_value=connection):
            try:
                return ledger.execute("P-D", "/chat/completions", body, reserve(8192),
                                      transport("fixture-secret"), lambda v: reply(v, 8192))
            finally:
                self.assertEqual(connection.request.call_count, 1)

    def test_documented_usage_on_last_content_chunk_and_done(self):
        raw = b"".join(chunks()).replace(b"\r\n", b"\n")
        body = encode(chat("s", [], 8192, compile_task=True, streaming=True))
        self.assertEqual(json.loads(body)["stream_options"], {"include_usage": True})
        with tempfile.TemporaryDirectory() as name:
            state = Path(name)
            journal = Ledger(state / "ledger.json", "r4-c", 10**9, 10**9, "id")
            result = self.operation(journal, body, [raw[i:i+7] for i in range(0, len(raw), 7)])
            self.assertEqual(result["text"], "инженерный факт")
            self.assertNotIn("private-thought", json.dumps(result))
            diag = load(state / "diagnostics/r4-c/P-D.json")
            self.assertTrue(diag["sse_done"] and diag["sse_usage_seen"] and diag["response_complete"])
            self.assertEqual(diag["sse_keepalives"], 1)
            self.assertEqual(result["cost_nd"], 20220)

    def test_unknown_preserves_reserve_and_blocks(self):
        parts = chunks()
        invalid = json.loads(parts[-2][6:])
        invalid["usage"]["prompt_tokens"] = -1
        for read, headers, stage in (
                ([], True, "headers"), (parts[:-1] + [b""], False, "read"),
                (parts[:2] + [TimeoutError("private")], False, "read"),
                ([http.client.IncompleteRead(b"partial", 20)], False, "read"),
                (parts[:2] + [event(b"not-json")], False, "parse"),
                (parts[:3] + [event(b"[DONE]")], False, "parse"),
                (parts[:-2] + [event({**invalid, "usage": None}), parts[-1]], False, "usage"),
                (parts[:-2] + [event(invalid), parts[-1]], False, "usage")):
            with self.subTest(stage=stage, headers=headers), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                ledger = Ledger(root / "ledger.json", "r4-c", 10**9, 10**9, "test")
                body = encode(chat("s", [], 8192, compile_task=True, streaming=True))
                with self.assertRaises(Stop):
                    self.operation(ledger, body, read, headers_fault=headers)
                entry, = load(ledger.path)["ops"]
                diag = load(root / "diagnostics/r4-c/P-D.json")
                self.assertEqual(entry["status"], "UNKNOWN")
                self.assertEqual(entry["reserve_nd"], reserve(8192))
                self.assertEqual(diag["stage"], stage)
                if not headers:
                    self.assertGreater(diag["response_bytes"], 0)
                self.assertNotIn("private-thought", json.dumps(diag))
                with self.assertRaises(Stop):
                    ledger.check(1)
                with self.assertRaises(Stop):
                    Ledger(ledger.path, "r4-c", 10**9, 10**9, "test", resume=True)


class Continuation(unittest.TestCase):
    def setUp(self):
        import os
        import shutil

        from compile_d import multipart, payload
        from protocol import save, sha
        from r4_a import draft_card, plan

        sources = os.environ.get("DX02_PREFLIGHT_SOURCES")
        if not sources:
            self.skipTest("Continuation regression requires pinned pilot data")
        destination = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(destination)
        self.pilot = self.root / "source-pilot"
        shutil.copytree(sources, self.pilot)
        self.experiment = experiment = plan(self.pilot)
        experiment["runtime"] = "frozen-old-runtime"
        card = draft_card(self.pilot, experiment)
        card["revision"] = "fixture-reviewed"
        for item in card["entries"]:
            if item["sample"] == "V":
                item["expected"] = "fixture"
        self.card = self.root / "r4-a-plan/reviewed-card.json"
        save(self.card, card)
        self.frozen = self.card.with_name("manifest-frozen.json")
        save(self.frozen, dict(experiment=experiment, card_sha256=sha(self.card.read_bytes())))
        self.frozen_sha = sha(self.frozen.read_bytes())
        self.old = self.root / "private-r4-a"
        save(self.old / "owner-go.json", dict(identity="prior-id", manifest_sha256=self.frozen_sha, owner_go="prior-go"))
        save(self.old / "engineering/score.json", {"fixture": "original score"})
        pdf = (self.pilot / "pdf" / (experiment["upload"]["source"] + ".pdf")).read_bytes()
        ops = []
        self.file = dict(handle="file-api-old-fixture", expires_at=4102444800, cost_nd=1_800_000)
        for id_, cost, hold in (("A-D", 21_000, reserve(8192)), ("A-L", 25_000, reserve(8192)),
                                ("pdf-upload", self.file["cost_nd"], self.file["cost_nd"])):
            path = self.old / "r4-a" / (id_ + ".json")
            save(path, self.file if id_ == "pdf-upload" else {"cost_nd": cost})
            ops.append(dict(id=id_, stage="r4-a", status="SETTLED", cost_nd=cost, reserve_nd=hold,
                            result_sha256=sha(path.read_bytes()), request_sha256=sha(multipart(pdf)[0])))
        task = experiment["cases"][2]["task"]
        source, = task["scope"]
        lines = load(self.pilot / "plan/context.json")[source]
        body, prefix = payload(self.pilot, load(self.pilot / "source-manifest.json"), task,
                              {source: dict(self.file, first=1, last=8)},
                              {}, (source, {n: lines[n - 1] for n in task["scope"][source]}))
        ops.append(dict(id="P-D", stage="r4-a", status="UNKNOWN", reserve_nd=reserve(8192),
                        request_sha256=sha(body), prefix_sha256=prefix))
        self.a_ledger = self.old / "ledger.json"
        save(self.a_ledger, dict(ops=ops, stages={"r4-a": {"identity": "prior-id"}}))
        save(self.root / "private-state/ledger.json", {"ops": []})
        save(self.root / "private-r3/ledger.json", {"ops": []})
        self.before = self.prior_bytes()

    def prior_bytes(self):
        return {path: path.read_bytes() for root in (self.old, self.frozen.parent,
                                                     self.root / "private-state", self.root / "private-r3")
                for path in root.rglob("*") if path.is_file()}

    def continuation(self, mode):
        from r4_c import continuation

        return continuation(self.root, self.card, self.frozen_sha, mode)

    def test_reuse_and_upload_matrix_with_financial_blocking(self):
        from r4_a import finances, run_matrix
        from r4_c import continuation
        from reconcile import summarize
        from zipfile import ZipFile

        for file_mode, failure in (("reuse", None), ("reuse", 1), ("upload", None), ("reuse", "budget")):
            with self.subTest(file_mode=file_mode, failure=failure):
                with tempfile.TemporaryDirectory() as name:
                    stage = Path(name)
                    pins, reused = self.continuation(file_mode)
                    experiment = pins["experiment"]
                    self.assertEqual([case["id"] for case in experiment["cases"]], ["P-D", "P-L", "V-D", "V-L"])
                    self.assertEqual(experiment["cases"], self.experiment["cases"][2:])
                    self.assertEqual(experiment["graph_bound_nd"],
                                     1_229_491_200 if file_mode == "reuse" else 1_231_291_200)
                    self.assertEqual(pins["prior_financial_exposure"]["r4_a_counted_nd"], 311_676_400)
                    calls = []

                    def post(endpoint, body, content_type):
                        calls.append((endpoint, body))
                        if len(calls) == failure:
                            raise http.client.RemoteDisconnected("fixture")
                        if endpoint == "/files":
                            return dict(id="file-api-new-fixture", purpose="text_recognition",
                                        bytes=experiment["upload"]["size"], expires_at=4102444800)
                        return fake_reply(body, '{"status":"NO_SUPPORTED_CONTENT","facts":[]}')

                    cap = reserve(8192) if failure == "budget" else 1_500_000_000
                    state = stage / "private-r4-c"
                    journal = Ledger(state / "ledger.json", "r4-c", cap, 2 * 10**9, "case")
                    report = run_matrix(self.pilot, experiment, journal, post, stage / "reports",
                                        streaming=True, reused_file=reused)
                    with ZipFile(stage / "reports/r4-c-summary.zip") as archive:
                        self.assertNotIn(b"file-api", archive.read("summary.json"))
                    if failure == 1:
                        self.assertEqual(report["stop_reason"], "UNKNOWN")
                        self.assertEqual(report["retained_nd"], reserve(8192))
                        self.assertEqual(len(calls), 1)
                        with self.assertRaises(Stop):
                            journal.check(1)
                    elif failure == "budget":
                        self.assertEqual(report["stop_reason"], "DEFERRED_BUDGET")
                        self.assertEqual(len(calls), 1)
                    else:
                        expected = int(file_mode == "upload")
                        self.assertEqual(report["upload_attempts"], expected)
                        self.assertEqual(report["chat_attempts"], 4)
                        first, second, vision_one, vision_two = [
                            json.loads(body) for endpoint, body in calls if endpoint == "/chat/completions"]
                        for request in (first, second, vision_one, vision_two):
                            self.assertTrue(request["stream"])
                            self.assertTrue(request["stream_options"]["include_usage"])
                        handle = "file-api-new-fixture" if expected else self.file["handle"]
                        for request in (first, second):
                            self.assertEqual(request["messages"][1]["content"][0]["file_id"], handle)
                        for request in (vision_one, vision_two):
                            self.assertNotIn("file_id", json.dumps(request))
                    # R4-B subtracts the continuation's actual SETTLED and retained reserve.
                    with patch("r4_a.summarize", side_effect=lambda path: summarize(
                            state / "ledger.json" if path.parent.name == "private-r4-c" else path)):
                        later = finances(self.root, include_r4_a=True, include_r4_c=True)
                    self.assertEqual(later["r4_c_counted_nd"], report["settled_peak_nd"] + report["retained_nd"])
        self.assertEqual(self.prior_bytes(), self.before)
        with self.assertRaisesRegex(Stop, "expired"):
            continuation(self.root, self.card, self.frozen_sha, "reuse", now=self.file["expires_at"])

    def test_go_and_original_tamper_guards(self):
        from dataclasses import dataclass
        from protocol import save
        from r4_c import validate_go

        @dataclass
        class Go:
            owner_go_usd: str = "0.50"
            total_go_usd: str = "4.00"
            owner_go: str = "new-p-d"
            upload_owner_go: str | None = None
            acknowledge_prior_p_d_unknown: bool = True
            confirm_provider_contract: bool = True

        reuse, _ = self.continuation("reuse")
        upload, _ = self.continuation("upload")
        self.assertEqual(validate_go(Go(), reuse), (500_000_000, 4_000_000_000))
        for denied in (Go(acknowledge_prior_p_d_unknown=False), Go(total_go_usd="4.53"), Go(owner_go_usd="0.30")):
            with self.assertRaises(Stop):
                validate_go(denied, reuse)
        for denied in (Go(), Go(upload_owner_go="new-p-d"), Go(owner_go_usd="0.31", upload_owner_go="upload")):
            with self.assertRaises(Stop):
                validate_go(denied, upload)
        self.assertEqual(validate_go(Go(upload_owner_go="upload"), upload)[0], 500_000_000)
        save(self.old / "r4-a/pdf-upload.json", dict(self.file, handle="file-api-tampered"))
        with self.assertRaisesRegex(Stop, "checkpoint"):
            self.continuation("reuse")
