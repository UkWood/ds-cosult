"""Free QA regressions. All historical-looking artifacts here are synthetic."""
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from bundle import read_bundle
from compile_d import compile_snapshot
from consult_d import questions
from consult_qa import QUESTIONS, consultation_finances, inspect_selector
from progress import Progress, reporting
from protocol import Ledger, Stop, load, save, sha
from qa_pins import QUESTION_SHA256
from qa_replay import ReplayLedger, evidence, pinned, review_row
from test_d import fake_reply


class HistoricalReplay(unittest.TestCase):
    def test_exact_replay_of_expired_upload_is_read_only(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source"
            records = {"A": {"kind": "astro", "lines": 1},
                       "P": {"kind": "pdf", "pages": 1, "sha256": sha(b"%PDF-1"), "size": 6}}
            website = dict(records=records, settings={}, boundary=[], relations=[],
                           entity=dict(type="product", id="sample"))
            save(source / "source-manifest.json", website)
            save(source / "plan/context.json", {"A": ["card"], "P": ["page"]})
            save(source / "plan/images.json", {})
            save(source / "plan/P.json", [{"page": 1}])
            (source / "pdf").mkdir()
            (source / "pdf/P.pdf").write_bytes(b"%PDF-1")
            expires = int(time.time()) + 60
            path = root / "private/ledger.json"
            base = Ledger(path, "compile", 2 * 10**9, 2 * 10**9, "synthetic")

            def mock(endpoint, body, _mime):
                if endpoint == "/files":
                    return dict(id="file-api-fixture", purpose="text_recognition", bytes=6, expires_at=expires)
                task = json.loads(json.loads(body)["messages"][1]["content"][-1]["text"])["task"]
                key = next(iter(task["scope"]))
                return fake_reply(body, json.dumps(dict(status="FACTS", facts=[
                    dict(text="mock", applicability="example", kind="source_assertion", locators=[f"{key}:1"]),
                    dict(text="rejected mock", applicability="example", kind="source_assertion",
                         locators=[f" {key} : 01 "]),
                ])))

            self.assertEqual(compile_snapshot(source, root / "kb", root / "baseline", base, "snapshot",
                                              mock, execution="live"), "PARTIAL")
            original = {p: p.read_bytes() for p in (root / "private").rglob("*") if p.is_file()}
            replay = ReplayLedger(path, website)
            with patch("time.time", return_value=expires + 1):
                status = compile_snapshot(source, root / "temp-kb", root / "temp-reports", replay,
                                          "snapshot", None, replay=replay, execution="live")
            self.assertEqual(status, "PARTIAL")
            self.assertEqual(replay.position, len(replay.ops))
            self.assertEqual(len(replay.rejected), 2)
            self.assertEqual(replay.rejected[1]["classification"], "unambiguous_normalization")
            self.assertEqual(replay.rejected[1]["proposed"]["locators"], ["P:1"])
            for filename in ("knowledge.zip", "DS-DX-02A-results.zip"):
                self.assertEqual(evidence(root / "baseline" / filename), evidence(root / "temp-reports" / filename))
            self.assertEqual({p: p.read_bytes() for p in original}, original)
            pinned(path, sha(original[path]))
            with self.assertRaises(Stop):
                pinned(path, "0" * 64)
            with self.assertRaises(Stop):
                replay.execute()

    def test_fusion_review_reports_all_codes_without_guessing(self):
        task = dict(id="fusion-1", kind="fusion", scope={"P": [2]}, images=[],
                    supporting_images=["approved.jpg"], supporting_locators=["P:2", "I:approved.jpg"])
        row = dict(text="", applicability="mock", kind="visual_observation",
                   locators=["external", "P:3", "I:file-api-secret"])
        result = review_row(task, 1, row, "row_text", "fixture", "fusion")
        self.assertIsNone(result["proposed"])
        self.assertEqual(result["violations"], sorted({"row_text", "locator_format", "locator_outside_evidence",
                                                       "fusion_kind", "image_outside_evidence", "disallowed_content"}))
        self.assertNotIn("file-api-secret", str(result))


class ConsultAndProgress(unittest.TestCase):
    def test_frozen_consult_series_and_cautious_history_accounting(self):
        from bundle import publish
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            entity = dict(type="product", id="fixture")
            consulted = dict(fact_id="d-fact", path="topics/safety.md", lines=[1, 2], entity=entity,
                             images=[], locators=["P:1"], critical=True, kind="source_assertion")
            entries = {"README.md": b"PARTIAL", "ESSENCE.md": b"### d-fact\nSynthetic limitation",
                       "topics/safety.md": b"### d-fact\nSynthetic limitation",
                       "coverage.json": b"{}", "index.json": json.dumps([consulted]).encode(),
                       "sources.json": b'{"P":{"pages":1,"edition":"mock"}}',
                       "illustrations/image-manifest.json": b"{}"}
            publish(root / "kb", entries, dict(entity=entity, status="PARTIAL"))
            self.assertEqual(sha(QUESTIONS.read_bytes()), QUESTION_SHA256)
            selector = inspect_selector(read_bundle(root / "kb")[0], questions(QUESTIONS))
            self.assertEqual([key for key, row in selector["questions"].items() if row["synthetic_history"]], ["Q11"])
            self.assertTrue(all(row["critical"] == 1 for row in selector["questions"].values()))
            folders = ("private-state", "private-r3", "private-r4-a", "private-r4-c", "private-r4-b")
            for folder in folders:
                unknown = [{"stage": "r4-a", "id": "P-D", "status": "UNKNOWN", "reserve_nd": 309_830_400}]
                save(root / folder / "ledger.json", dict(total=4_170_000_000, ops=unknown if folder == "private-r4-a" else []))
            ledger = root / "private-r4-b/ledger.json"
            with patch.dict("consult_qa.PINS", {"ledger": sha(ledger.read_bytes())}):
                budget = consultation_finances(root)
                self.assertEqual(budget["prior_accounted_nd"], 776_387_232)
                self.assertEqual(budget["max_new_total_nd"], 4_170_000_000)
                ledger.write_bytes(ledger.read_bytes() + b"\n")
                with self.assertRaises(Stop):
                    consultation_finances(root)

    def test_heartbeat_closes_and_reports_terminal_status(self):
        output = io.StringIO()
        progress = Progress("TEST", "mock.zip", interval=0.005, stream=output)
        with reporting(progress):
            time.sleep(0.035)
        progress.terminal("PARTIAL")
        text = output.getvalue()
        self.assertIn("heartbeat", text)
        self.assertIn("PARTIAL", text)
        time.sleep(0.015)
        self.assertEqual(output.getvalue(), text)
        with self.assertRaises(Stop), reporting(progress):
            raise Stop("private content")
        self.assertIn(" STOP ", output.getvalue())
        self.assertNotIn("private content", output.getvalue())

    def test_qa_cli_uses_offline_gate(self):
        import errno
        import os
        import subprocess
        import sys
        if not os.environ.get("DX02_PREFLIGHT_SOURCES"):
            self.skipTest("requires offline preflight execution")
        smoke = subprocess.run([sys.executable, "-c",
                 "import socket; socket.socket()"], capture_output=True, text=True)
        self.assertNotEqual(smoke.returncode, 0)
        self.assertIn(f"Errno {errno.EPERM}", smoke.stderr)
        cwd = Path(__file__).resolve().parent
        out = subprocess.run([sys.executable, str(cwd / "qa_replay.py"),
                             "--workspace", "/nonexistent", "--output", "/nonexistent/report.zip"],
                             capture_output=True, text=True)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("socket denied (EPERM)", out.stderr)
