import tempfile
import unittest
from pathlib import Path
from protocol import reply, Stop
from bundle import checked_name
from sources import plan


class Contract(unittest.TestCase):
    def test_D05_fixed_graph(self):
        tasks = plan([3, 11, 60])
        ids = [task["id"] for task in tasks]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"K00", "V011", "W04", "F01"} <= set(ids))

    def test_D09_reject_traversal(self):
        for name in ("../ESSENCE.md", "original.pdf", "visual/../README.md"):
            self.assertFalse(checked_name(name))

    def test_D12_reject_inconsistent_usage(self):
        response = {"model": "deepseek-flash", "choices": [{"finish_reason": "stop",
                    "message": {"content": "text"}}], "usage": {
             "prompt_tokens": 5, "prompt_cache_hit_tokens": 3,
             "prompt_cache_miss_tokens": 3, "completion_tokens": 1}}
        with self.assertRaises(Stop):
            reply(response, 12)


def fake_reply(body, result, finish="stop"):
    from protocol import MODEL
    return {
        "model": MODEL,
        "choices": [{"finish_reason": finish, "message": {"content": result}}],
        "usage": {"prompt_tokens": 100, "prompt_cache_hit_tokens": 70,
                  "prompt_cache_miss_tokens": 30, "completion_tokens": 9,
                  "completion_tokens_details": {"reasoning_tokens": 1}},
    }


class OfflineContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_D01_real_pinned_pdf_reject_changed_and_missing_page(self):
        import os
        from sources import read_pdf, pdf_pages, cmd

        if not os.environ.get("DX02_PREFLIGHT_SOURCES"):
            self.skipTest("real sources require preflight")
        pdf = Path(os.environ["DX02_PREFLIGHT_SOURCES"]) / "pdf/manual.pdf"
        self.assertEqual(len(read_pdf(pdf)), 65)
        text = cmd("pdftotext", "-layout", pdf, "-")
        with self.assertRaises(Stop):
            pdf_pages(b"\f".join(text.split(b"\f")[1:]))
        changed = self.root / "changed.pdf"
        changed.write_bytes(pdf.read_bytes() + b"x")
        with self.assertRaises(Stop):
            read_pdf(changed)

    def test_D02_D03_pinned_graph_and_scope(self):
        import os
        from sources import astro, PRODUCT, PRODUCT_BLOB, SITE

        if not os.environ.get("DX02_PREFLIGHT_SITE"):
            self.skipTest("real sources require preflight")
        found = astro(Path(os.environ["DX02_PREFLIGHT_SITE"]))
        self.assertEqual(found["commit"], SITE)
        self.assertGreater(found["indexed"], 400)
        record = next(row for row in found["records"].values() if row["path"] == PRODUCT)
        self.assertEqual(record["blob"], PRODUCT_BLOB)
        self.assertTrue(record["canonical_url"].endswith("/products/bkd-pk-rf-2/"))
        self.assertTrue(any(x["type"].startswith("incoming") for x in found["relations"]))
        self.assertTrue(any(x["type"].startswith("explicit") for x in found["relations"]))
        self.assertEqual({x["status"] for x in found["inventory"]}, {"PINNED", "DEFERRED"})

    def test_D04_stable_prefix_one_file_no_tools(self):
        import json
        from compile_d import payload, multipart
        topics = plan([11])
        a, p1 = payload(self.root, {"records": {}, "context": {}, "relations": []}, topics[1], "file-api-mock", {})
        b, p2 = payload(self.root, {"records": {}, "context": {}, "relations": []}, topics[2], "file-api-mock", {})
        self.assertEqual(p1, p2)
        self.assertNotEqual(a, b)
        for raw in (a, b):
            value = json.loads(raw)
            self.assertNotIn("tools", value)
            self.assertEqual(len(value["messages"]), 2)
            self.assertEqual([x["type"] for x in value["messages"][1]["content"]], ["file", "text", "text"])
        body, _ = multipart(b"mock")
        self.assertLess(body.index(b'name="purpose"'), body.index(b'name="file"'))

    def test_D05_D07_D08_validation_merge_and_conflict(self):
        import json
        from compile_d import facts, merge
        cfg = plan([11])
        task = cfg[1]
        row = {"text": "Mock: обесточить перед обслуживанием", "applicability": "исполнение 1",
               "kind": "source_assertion", "locators": ["P01:3"]}
        website = {"records": {"A001": {"ranges": [[1, 4]]}}}
        result = lambda r, f="stop": {"finish_reason": f, "text": json.dumps({"status": "FACTS", "facts": [r]})}
        self.assertEqual(facts(result(row, "length"), task, website)[0], "TRUNCATED")
        self.assertEqual(facts(result(row), task, website)[0], "COMPLETE")
        self.assertEqual(facts(result(dict(row, locators=["P01:66"])), task, website)[0], "PARTIAL")
        duplicate = dict(row, locators=["A001:2"])
        different = dict(row, applicability="исполнение 2")
        conflict = dict(row, text="Mock: разные редакции расходятся", kind="unresolved")
        merged = merge([task], {task["id"]: [row, duplicate, different, conflict]})
        self.assertEqual(len(merged), 3)
        self.assertIn(["A001:2", "P01:3"], [item["locators"] for item in merged])

    def test_D06_real_inline_crops_and_limit(self):
        import os
        from compile_d import image_block
        from protocol import load, sha

        if not os.environ.get("DX02_PREFLIGHT_SOURCES"):
            self.skipTest("real sources require preflight")
        root = Path(os.environ["DX02_PREFLIGHT_SOURCES"])
        images = load(root / "plan/images.json")
        upper, lower = [images[f"pdf-011-{kind}.png"] for kind in ("upper", "lower")]
        self.assertGreater(upper["bbox_render_pixels_top_left"][3], lower["bbox_render_pixels_top_left"][1])
        raw = (root / "raw-illustrations/pdf-011-upper.png").read_bytes()
        self.assertEqual(sha(raw), upper["sha256"])
        self.assertTrue(image_block(raw)["image_url"]["url"].startswith("data:image/png;base64,"))
        with self.assertRaises(Stop):
            image_block(b"bad picture")

    def fixture(self):
        from bundle import publish
        entries = {"README.md": b"Mock\n", "ESSENCE.md": b"Mock selected knowledge\n",
                   "coverage.json": b"{}", "sources.json": b"{}", "index.json": b"[]",
                   "illustrations/image-manifest.json": b"{}"}
        root = self.root / "knowledge"
        publish(root, entries, {"status": "PARTIAL"})
        return root

    def test_D09_zip_deterministic_and_reject_extra(self):
        from bundle import export, read_bundle, verify_zip
        import zipfile
        root = self.fixture()
        one, two = self.root / "one.zip", self.root / "two.zip"
        export(root, one)
        export(root, two)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        with zipfile.ZipFile(one, "a") as output:
            output.writestr("../oops", b"no")
        with self.assertRaises(Stop):
            verify_zip(one)
        (root / "visual").symlink_to(self.root)
        with self.assertRaises(Stop):
            read_bundle(root)

    def test_D10_D11_D15_source_free_mock_and_dialog(self):
        import json
        from bundle import read_bundle
        from consult_d import conduct
        from protocol import Ledger

        raw = self.root / "source"
        raw.write_text("MOCK_FACT_ONLY_IN_RAW")
        raw.rename(self.root / "physically-detached")
        entries, meta = read_bundle(self.fixture())
        ledger = Ledger(self.root / "private/ledger.json", "consult", 10**9, 10**9, "mock")
        seen = []
        def post(path, body, content_type):
            self.assertEqual(path, "/chat/completions")
            self.assertNotIn(b"MOCK_FACT_ONLY_IN_RAW", body)
            self.assertNotIn(b"file_id", body)
            self.assertNotIn(b"tools", body)
            self.assertNotIn(b"physically-detached", body)
            seen.append(json.loads(body))
            return fake_reply(body, "В подготовленной базе сведений нет.")
        answers = []
        conduct(entries, meta, [{"question": "Что известно?", "dialog": "one"},
                                {"question": "А о нём точнее?", "dialog": "one"}], ledger, post, answers)
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(seen[1]["messages"][1]["content"]), 3)
        self.assertEqual(answers[0]["review"], "UNREVIEWED")

    def test_D12_D14_pending_budget_duplicate_and_checkpoint(self):
        from protocol import Ledger, encode, locked, reply, reserve
        root = self.root / "state"
        file = root / "ledger.json"
        ledger = Ledger(file, "compile", 10**9, 10**9, "fixed")
        with locked(root):
            with self.assertRaises(Stop):
                with locked(root):
                    pass
        with self.assertRaises(Stop):
            ledger.check(10**9 + 1)
        parser = lambda result: reply(result, 4096)
        post = lambda *a: fake_reply(a[1], "test")
        out = ledger.execute("K01", "/chat/completions", b"{}", reserve(4096), post, parser)
        self.assertEqual(out["cost_nd"], 20_220)
        with self.assertRaises(Stop):
            ledger.execute("K01", "/chat/completions", b"{}", reserve(4096), post, parser)
        with self.assertRaises(Stop):
            Ledger(file, "compile", 10**9, 10**9, "different", True)
        with self.assertRaises(Stop):
            Ledger(file, "compile", 10**9, 10**9, "fixed")
        resumed = Ledger(file, "compile", 10**9, 10**9, "fixed", True)
        self.assertEqual(resumed.result("K01"), out)
        (root / "compile/K01.json").write_bytes(encode({"tampered": True}))
        with self.assertRaises(Stop):
            resumed.result("K01")
        def unknown(*args):
            raise TimeoutError
        with self.assertRaises(Stop):
            ledger.execute("K02", "/chat/completions", b"{}", reserve(4096), unknown, parser)
        with self.assertRaises(Stop):
            Ledger(file, "consult", 10**9, 10**9, "different")

    def test_D13_cloud_gate_and_inherited_seccomp(self):
        import errno
        import os
        import socket
        from unittest.mock import patch
        from protocol import live_gate

        with patch.dict(os.environ, {"CODEX_THREAD_ID": "mock"}), self.assertRaises(Stop):
            live_gate()
        if os.environ.get("DX02_PREFLIGHT_SOURCES"):
            with self.assertRaises(OSError) as caught:
                socket.socket()
            self.assertEqual(caught.exception.errno, errno.EPERM)

    def test_D16_cli_scope(self):
        shell = Path(__file__).resolve().parent
        self.assertEqual({x.name for x in shell.glob("*live.sh")}, {"compile-live.sh", "consult-live.sh"})
        consult = (shell / "consult_d.py").read_text()
        self.assertNotIn("from sources", consult)
        self.assertNotIn("from compile_d", consult)
        self.assertNotIn("/files", consult)

    def test_D08_D09_D14_partial_assembly_after_truncation(self):
        import os
        from bundle import read_bundle, verify_zip
        from compile_d import assemble
        from protocol import Ledger, load, reply, reserve
        from sources import verify

        if not os.environ.get("DX02_PREFLIGHT_SOURCES"):
            self.skipTest("real sources require preflight")
        source = Path(os.environ["DX02_PREFLIGHT_SOURCES"])
        identity = verify(source, reparse=False)
        tasks = load(source / "plan/tasks.json")
        website = load(source / "astro-snapshot/context.json")
        ledger = Ledger(self.root / "state/ledger.json", "compile", 10**9, 10**9, identity)
        ledger.execute("K05", "/chat/completions", b"{}", reserve(8192),
                       lambda *args: fake_reply(b"{}", "{truncated", "length"),
                       lambda r: reply(r, 8192))
        knowledge = self.root / "knowledge"
        reports = self.root / "reports"
        assemble(source, knowledge, reports, ledger, identity, tasks, website, "mock truncation")
        entries, manifest = read_bundle(knowledge)
        self.assertEqual(manifest["status"], "PARTIAL")
        self.assertNotIn(b"{truncated", entries["ESSENCE.md"])
        coverage = load(knowledge / "coverage.json")
        self.assertEqual(coverage["tasks"]["K05"], "TRUNCATED")
        self.assertEqual(len(coverage["sources"]["P01"]), 65)
        self.assertEqual(verify_zip(reports / "BKD-PK-RF2-knowledge.zip"), manifest)
