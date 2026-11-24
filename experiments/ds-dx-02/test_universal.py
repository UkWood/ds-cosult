import unittest

from protocol import Stop
from planning import validate


class PlanContract(unittest.TestCase):
    def test_coverage_and_invalid_locator(self):
        scope = {"A": {1, 2}, "B": {1}}
        task = {"id": "read", "topic": "operation", "kind": "extract",
                "scope": {"A": [1, 2], "B": [1]}, "images": [], "deps": [],
                "instruction": "Extract conditions", "limit": 1024}
        self.assertEqual(validate({"tasks": [task], "gaps": []}, scope, {}, 8), [task])
        for invalid in ({"A": [1, 2]}, {"A": [1, 3], "B": [1]}):
            with self.assertRaises(Stop):
                validate({"tasks": [dict(task, scope=invalid)], "gaps": []}, scope, {}, 8)
        with self.assertRaises(Stop):
            validate({"tasks": [dict(task, deps=["read"])], "gaps": []}, scope, {}, 8)
        with self.assertRaises(Stop):
            validate({"tasks": [task], "gaps": []}, scope, {}, 0)


class EndToEnd(unittest.TestCase):
    def test_U01_general_runtime(self):
        from pathlib import Path

        root = Path(__file__).parent
        for name in ("astro", "sources", "planning", "compile_d", "bundle", "consult_d", "protocol"):
            runtime = (root / (name + ".py")).read_text().lower()
            for pilot in ("bkd-pk", "бкд-пк", "newel", "030303812b4"):
                self.assertNotIn(pilot, runtime, name)

    def test_U02_U03_U07_U08_U12_U13_real_packages(self):
        import json
        import os
        import shutil
        import tempfile
        from pathlib import Path
        from bundle import read_bundle, verify_zip
        from compile_d import PLANNER, compile_snapshot, provider_files
        from consult_d import conduct, report
        from protocol import Ledger, encode, load, runtime_digest
        from sources import verify
        from test_d import fake_reply

        paths = os.environ.get("UTKC_ACCEPTANCE_PACKAGES")
        if not paths:
            self.skipTest("prepare the three real snapshots")
        observed = []
        for pack, path in enumerate(paths.split(os.pathsep)):
            root = Path(path)
            before = runtime_digest()
            identity = verify(root, Path(os.environ["DX02_PREFLIGHT_SITE"]))
            source_manifest = load(root / "source-manifest.json")
            observed.append((source_manifest["entity"]["type"], len(source_manifest["records"])))
            uploads = set()
            calls = []
            truncated = set()
            children = set()

            def post(endpoint, body, content_type):
                if endpoint == "/files":
                    boundary = content_type.partition("boundary=")[2]
                    self.assertNotIn(boundary, uploads)
                    uploads.add(boundary)
                    raw = body.split(b"Content-Type: application/pdf\r\n\r\n")[1].rsplit(b"\r\n--", 1)[0]
                    return dict(id=f"file-api-mock-{len(uploads)}", purpose="text_recognition",
                                bytes=len(raw), expires_at=4102444800)
                wire = json.loads(body)
                blocks = wire["messages"][1]["content"]
                text_blocks = [block["text"] for block in blocks if block["type"] == "text"]
                registry, request = map(json.loads, text_blocks)
                current = request["task"]
                scope = {source: [int(n) for n in locations]
                         for source, locations in registry["source_text"].items()}
                kind = current["kind"]
                if ".s" in current["id"]:
                    children.add(kind)
                if pack == 0 and kind not in truncated and ".s" not in current["id"] and (
                        (kind == "plan" and sum(map(len, scope.values())) > 1)
                        or (kind == "extract" and sum(map(len, current["scope"].values())) > 1)
                        or (kind == "vision" and len(current["images"]) > 1)
                        or (kind == "fusion" and len(current["scope"]) > 1)):
                    truncated.add(kind)
                    return fake_reply(body, '{"facts":[{', "length")
                locators = [f"{source}:{n}" for source, nums in current.get("scope", scope).items() for n in nums]
                if wire["messages"][0]["content"] == PLANNER:
                    source, = scope
                    visuals = registry["image_candidates"]
                    batch = [dict(id="read", topic="evidence", kind="extract", scope=scope,
                                  images=[], deps=[], instruction="Capture the first grounded observation", limit=512)]
                    if visuals:
                        batch.append(dict(batch[0], id="visual", topic="scene", kind="vision", images=visuals))
                    result = dict(tasks=batch, gaps=[])
                elif current["kind"] == "fusion":
                    calls.append("fusion")
                    result = dict(status="NO_SUPPORTED_CONTENT", facts=[])
                else:
                    calls.append(current["kind"])
                    locs = ["I:" + current["images"][0]] if current["images"] else locators[:1]
                    result = dict(status="FACTS", facts=[dict(text="Mock observation " + locs[0],
                                  applicability="Mock result", locators=locs,
                                  kind="visual_observation" if current["images"] else "source_assertion")])
                return fake_reply(body, encode(result).decode())

            with tempfile.TemporaryDirectory() as directory:
                stage = Path(directory)
                raw_dir = stage / "SourceArchive"
                shutil.copytree(root, raw_dir)
                (raw_dir / "raw-only.txt").write_text("ABSENT_MATERIAL_MARKER")
                knowledge, reports = stage / "kb", stage / "compile"
                ledger_path = stage / "private" / "ledger.json"
                ledger = Ledger(ledger_path, "compile", 10**12, 10**12, identity)
                compile_snapshot(raw_dir, knowledge, reports, ledger, identity, post)
                self.assertIn("fusion", calls)
                if pack == 0:
                    self.assertEqual(truncated, {"plan", "extract", "vision", "fusion"})
                    self.assertTrue(truncated <= children)
                resumed = Ledger(ledger_path, "compile", 10**12, 10**12, identity, True)
                def no_retry(*args):
                    self.fail("Completed mock operation was repeated")
                compile_snapshot(raw_dir, stage / "resumed-kb", stage / "resumed-compile",
                                 resumed, identity, no_retry)
                self.assertEqual(verify_zip(stage / "resumed-compile/knowledge.zip"),
                                 verify_zip(reports / "knowledge.zip"))
                expected_uploads = {file["sha256"] for id_, row in source_manifest["records"].items()
                                    if row["kind"] == "pdf" and row.get("status") == "PINNED"
                                    for file in provider_files(id_, row)}
                self.assertEqual(len(uploads), len(expected_uploads))
                self.assertEqual(before, runtime_digest())
                entries, meta = read_bundle(knowledge)
                self.assertEqual(verify_zip(reports / "knowledge.zip"), meta)
                self.assertEqual(meta["entity"], source_manifest["entity"])
                self.assertNotIn(b"file-api-mock", b"".join(entries.values()))
                shutil.rmtree(raw_dir)
                self.assertFalse(raw_dir.exists())
                consulted = []

                def consult(endpoint, body, _):
                    self.assertEqual(endpoint, "/chat/completions")
                    self.assertNotIn(b"ABSENT_MATERIAL_MARKER", body)
                    self.assertNotIn(b"file_id", body)
                    self.assertNotIn(b'"source_text"', body)
                    return fake_reply(body, "Mock response uses the prepared knowledge only")

                ledger = Ledger(ledger_path, "consult", 10**12, 10**12, meta["identity"])
                conduct(entries, meta, [{"question": "What does the package contain?"}], ledger, consult, consulted)
                self.assertEqual(len(consulted), 1)
                report(stage / "consult", consulted, None, ledger)
                print(f"mock {meta['entity']} {meta['status']} sources={len(source_manifest['records'])} "
                      f"facts={len(load(knowledge / 'index.json'))} uploads={len(uploads)} "
                      f"runtime={before}")
        self.assertEqual(sorted(kind for kind, _ in observed), ["product", "product", "system"])
        self.assertEqual(len({size for _, size in observed}), 3)

    def test_U14_budget_amendment_preserves_history(self):
        import tempfile
        from pathlib import Path
        from protocol import Ledger, load, save

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.json"
            first = Ledger(path, "compile", 100, 200, "plan")
            first.execute("one", "/files", b"x", 1, lambda *args: {},
                          lambda _: {"cost_nd": 1})
            original = load(path)
            approval = {"stage": "compile", "identity": "plan", "old_cap": 100, "new_cap": 150,
                        "old_total": 200, "new_total": 200, "owner_go": "approval-1"}
            with self.assertRaises(Stop):
                Ledger(path, "compile", 150, 200, "plan", True)
            resumed = Ledger(path, "compile", 150, 200, "plan", True, approval)
            self.assertEqual(resumed.data["ops"], original["ops"])
            self.assertEqual(resumed.result("one")["cost_nd"], 1)
            with self.assertRaises(Stop):
                Ledger(path, "compile", 150, 200, "plan", True, approval)
            changed = load(path)
            changed["approvals"][0]["record"]["old_cap"] = 90
            save(path, changed)
            with self.assertRaises(Stop):
                Ledger(path, "compile", 150, 200, "plan", True)

    def test_U04_nested_route_and_reference_cycle(self):
        import tempfile
        from pathlib import Path
        from astro import discover, git

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-q")
            blobs = {
                "src/content.config.ts": """export const collections = {
  products: defineCollection({
     related: z.array(reference('products')),
     systems: z.array(reference('systems')),
  }),
  systems: defineCollection({
     products: z.array(reference('products')),
  }),
  news: defineCollection({ products: z.array(reference('products')) }),
};""",
                "src/pages/products/[...slug].astro": "getCollection('products'); params: { slug: entry.id }",
                "src/pages/systems/[slug].astro": "getCollection('systems'); params: { slug: entry.id }",
                "src/content/products/sub/primary.md": "---\ntitle: Primary\nsystems: [suite]\n---\nContent\n",
                "src/content/products/peer.md": "---\ntitle: Peer\nrelated: [sub/primary]\n---\n",
                "src/content/systems/suite.md": "---\ntitle: Suite\nproducts: [sub/primary]\n---\n",
                "src/content/news/event.md": "---\ntitle: Event\nproducts: [sub/primary]\n---\n",
            }
            for name, value in blobs.items():
                file = root / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(value)
            git(root, "add", ".")
            git(root, "-c", "commit.gpgsign=false", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-qm", "Fixture")
            site = {"revision": git(root, "rev-parse", "HEAD").decode().strip(), "origin": "https://example.test"}
            record, _ = discover(root, dict(site=site, entity={"type": "product", "id": "sub/primary"},
                                           relation_depth=4))
            rows = list(record["records"].values())
            self.assertEqual(len(rows), 4)
            self.assertTrue(any(row["canonical_url"] == "https://example.test/products/sub/primary/" for row in rows))
            self.assertEqual(len(record["relations"]), 4)
            self.assertEqual({rel["type"] for rel in record["relations"]}, {"mention", "explicit_reference"})

    def test_U05_bad_manual_sources_do_not_hide_good_pdf(self):
        import os
        import shutil
        import tempfile
        from pathlib import Path
        from protocol import load, save
        from sources import prepare, verify

        preflight = os.environ.get("DX02_PREFLIGHT_SOURCES")
        if not preflight:
            self.skipTest("requires a real pinned source")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = Path(preflight)
            site = Path(os.environ["DX02_PREFLIGHT_SITE"])
            options = load(original / "configuration.json")
            manifest = load(original / "source-manifest.json")
            key, good = next((key, row) for key, row in manifest["records"].items()
                             if row.get("status") == "PINNED" and row.get("pages") == 2)
            shutil.copyfile(original / "pdf" / (key + ".pdf"), root / "manual.pdf")
            (root / "corrupt.pdf").write_bytes(b"invalid")
            options["limits"] = {"pages_per_provider_file": 1}
            options["materials"] = [{"file": "manual.pdf", "sha256": good["sha256"]},
                                    {"file": "corrupt.pdf"}, {"file": "missing.pdf"},
                                    {"url": good["url"], "file": "manual.pdf", "sha256": "0" * 64}]
            save(root / "config.json", options)
            prepare(root / "config.json", site, root / "archive")
            verify(root / "archive", site)
            imported = {row.get("origin"): row for row in load(root / "archive/source-manifest.json")["records"].values()}
            self.assertEqual(imported["manual.pdf"]["pages"], 2)
            fragments = imported["manual.pdf"]["provider_fragments"]
            self.assertEqual([(row["first"], row["last"]) for row in fragments], [(1, 1), (2, 2)])
            for fragment in fragments:
                from protocol import sha
                raw = (root / "archive" / fragment["path"]).read_bytes()
                self.assertEqual(sha(raw), fragment["sha256"])
            self.assertEqual(imported["corrupt.pdf"]["status"], "UNAVAILABLE")
            self.assertEqual(imported["missing.pdf"]["status"], "UNAVAILABLE")
            self.assertEqual(imported[good["url"]]["reason"], "Source pin mismatch")

    def test_U13_critical_records_survive_topic_selection(self):
        import json
        from unittest.mock import patch
        from consult_d import select
        from protocol import encode

        base = {"path": "topics/control.md", "lines": [1, 2], "kind": "source_assertion",
                "critical": True, "images": [], "fact_id": "critical"}
        entries = {"ESSENCE.md": b"x" * 4000, "index.json": encode([base]),
                   "sources.json": b"{}", "illustrations/image-manifest.json": b"{}",
                   "topics/control.md": b"### critical\nRelay must be isolated at terminal X.\n"}
        with patch("consult_d.CONTEXT_BYTES", 512):
            wire, report = select(entries, "How do I change the menu language?")
        self.assertEqual(report["fact_ids"], ["critical"])
        user = json.loads(wire)["messages"][1]["content"]
        self.assertIn("Relay must be isolated", user[0]["text"])
