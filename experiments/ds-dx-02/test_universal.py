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
        gap = {"source": "A", "locations": [2], "reason": "not passed to any task"}
        with self.assertRaises(Stop):
            validate({"tasks": [dict(task, scope={"A": [1], "B": [1]})], "gaps": [gap]}, scope, {}, 8)
        images = {"page.jpg": ("A", 2)}
        visual = dict(task, kind="vision", images=["page.jpg"])
        self.assertEqual(validate({"tasks": [visual], "gaps": []}, scope, images, 8), [visual])
        with self.assertRaises(Stop):
            validate({"tasks": [dict(visual, images=["unregistered.jpg"])], "gaps": []}, scope, images, 8)


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
        from compile_d import compile_snapshot, graph_estimate, provider_files
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
                fixed, request = map(json.loads, text_blocks)
                evidence = request["available_evidence"]
                self.assertIn("related_source_metadata", fixed)
                current = request["task"]
                kind = current["kind"]
                self.assertEqual(set(evidence["source_text"]), {fixed["source"]})
                self.assertEqual(evidence["original_locators"], current["scope"])
                self.assertEqual(set(evidence["images"]), set(current["images"]))
                self.assertNotIn("source_text", fixed)
                self.assertIn(kind, ("extract", "vision", "fusion"))
                calls.append(kind)
                if ".s" in current["id"]:
                    children.add(kind)
                if pack == 0 and kind not in truncated and ".s" not in current["id"] and (
                        (kind in {"extract", "fusion"} and any(len(v) > 1 for v in current["scope"].values()))
                        or (kind == "vision" and len(current["images"]) > 1)):
                    truncated.add(kind)
                    return fake_reply(body, '{"facts":[{', "length")
                if kind == "fusion":
                    self.assertGreaterEqual(len(current["scope"]), 2)
                    result = dict(status="NO_SUPPORTED_CONTENT", facts=[])
                else:
                    locs = (["I:" + name for name in current["images"]] or
                            [f"{source}:{n}" for source, nums in current["scope"].items() for n in nums[:2]])
                    result = dict(status="FACTS", facts=[dict(text="Mock observation " + loc,
                                  applicability="Mock result", locators=[loc],
                                  kind="visual_observation" if current["images"] else "source_assertion")
                                  for loc in locs])
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
                    self.assertEqual(truncated, {"extract", "vision", "fusion"})
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
                    self.assertNotIn(b"available_evidence", body)
                    return fake_reply(body, "Mock response uses the prepared knowledge only")

                ledger = Ledger(ledger_path, "consult", 10**12, 10**12, meta["identity"])
                conduct(entries, meta, [{"question": "What does the package contain?"}], ledger, consult, consulted)
                self.assertEqual(len(consulted), 1)
                report(stage / "consult", consulted, None, ledger)
                from collections import Counter
                from bundle import archive, sums
                graph = graph_estimate(root)
                coverage = load(knowledge / "coverage.json")
                context = load(root / "plan/context.json")
                base = [task for id_, task in coverage["task_scope"].items()
                        if id_.startswith("g") and ".s" not in id_]
                self.assertEqual({(key, n) for task in base for key, scope in task["scope"].items() for n in scope},
                                 {(key, n) for key, values in context.items() for n in range(1, len(values) + 1)})
                self.assertEqual({name for task in base for name in task["images"]},
                                 set(load(root / "plan/images.json")))
                compile_ops = [op for op in ledger.data["ops"] if op["stage"] == "compile"]
                self.assertEqual(len(compile_ops), len(uploads) + len(calls))
                self.assertTrue(all(op["status"] == "SETTLED" and 0 < op["cost_nd"] <= op["reserve_nd"]
                                    for op in compile_ops))
                call_counts = dict(Counter(calls), planner=0, upload=len(uploads), consult=1)
                summary = dict(entity=meta["entity"], snapshot=identity, status=meta["status"],
                               facts=len(load(knowledge / "index.json")), calls=call_counts, graph=graph,
                               reasons=dict(Counter(v["reason"] for v in coverage["extraction_issues"].values())),
                               runtime=before, paid_calls=0)
                print("mock " + encode(summary).decode())
                output = os.environ.get("DX02_MOCK_EVIDENCE")
                if output:
                    entries = {"summary.json": encode(summary), "coverage.json": encode(coverage),
                               "knowledge.zip": (reports / "knowledge.zip").read_bytes(),
                               "compile.zip": (reports / "DS-DX-02A-results.zip").read_bytes(),
                               "consult.zip": (stage / "consult/DS-DX-02B-results.zip").read_bytes()}
                    entries["SHA256SUMS"] = sums(entries)
                    archive(Path(output) / f"mock-package-{pack + 1}.zip", entries)
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


class RealPlannerRegression(unittest.TestCase):
    def test_live_plan_shape_and_invalid_extraction_do_not_control_execution(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from compile_d import compile_snapshot
        from protocol import Ledger, encode, load, save
        from test_d import fake_reply

        source = "A-c5c7146d49ed3f59"
        other = "A-second"
        legacy = {
            "tasks": [
                {"id": "card", "scope": {source: "1-12"}},
                {"id": "vision", "images": ["/photos/3112376640116232.jpg",
                                            "/photos/3385755126930346.jpg"], "deps": ["external"]},
                {"id": "fusion", "scope": {"A-external": [1]}, "deps": ["external"]},
            ],
            "gaps": [{"source": "A-external", "locations": [1], "reason": "not supplied"}],
        }
        for advisory, finish, reason, bare in (
            (legacy, "stop", "unsupported_shape", True),
            (legacy, "stop", "unsupported_shape", False),
            (None, "stop", "absent", False),
            ({"themes": []}, "stop", "unsupported_shape", False),
            (legacy, "length", "truncated", False),
        ):
            with self.subTest(reason=reason, bare=bare), TemporaryDirectory() as tmp:
                stage = Path(tmp)
                root = stage / "source"
                save(root / "source-manifest.json", {
                    "entity": {"id": "sample", "type": "product"}, "relations": [], "boundary": [],
                    "settings": {}, "records": {source: {"kind": "astro", "lines": 71, "relation": "entity_card"},
                                                other: {"kind": "astro", "lines": 1}},
                })
                save(root / "plan/context.json", {source: ["line"] * 71, other: ["more evidence"]})
                save(root / "plan/images.json", {})
                calls = []

                def post(endpoint, body, content_type):
                    import json
                    self.assertEqual(endpoint, "/chat/completions")
                    fixed, suffix = [json.loads(block["text"]) for block in
                                     json.loads(body)["messages"][1]["content"]]
                    task = suffix["task"]
                    calls.append(task["id"])
                    self.assertEqual(task["kind"], "extract")
                    self.assertEqual(task["images"], [])
                    self.assertNotIn("/photos/", body.decode())
                    key, = task["scope"]
                    number = task["scope"][key][0]
                    row = dict(text=key, applicability="mock", kind="source_assertion",
                               locators=[f"{key}:{number}"])
                    result = dict(status="FACTS", facts=[row], advisory={"topics": ["service"]})
                    if task["id"] == "g0001-read":
                        self.assertEqual(task["scope"], {source: list(range(1, 72))})
                        self.assertEqual(len(suffix["available_evidence"]["source_text"][source]), 71)
                        self.assertEqual(fixed["source"], source)
                        result["advisory"] = advisory
                        result["facts"].append(dict(row, locators=["A-external:90"]))
                        if bare:
                            result = legacy
                    if ".s" in task["id"]:
                        result = {"status": "NO_SUPPORTED_CONTENT", "facts": []}
                    return fake_reply(body, encode(result).decode(), finish if task["id"] == "g0001-read" else "stop")

                ledger = Ledger(stage / "private/ledger.json", "compile", 10**10, 10**10, "snapshot")
                self.assertEqual(compile_snapshot(root, stage / "kb", stage / "reports", ledger,
                                                  "snapshot", post), "PARTIAL")
                coverage = load(stage / "kb/coverage.json")
                expected = ["g0001-read", "g0002-read"]
                if finish == "length":
                    expected[1:1] = ["g0001-read.s1", "g0001-read.s2"]
                self.assertEqual(calls, expected)
                self.assertEqual(coverage["advisory"]["g0001-read"], reason)
                self.assertEqual(set(coverage["sources"][source]), {str(n) for n in range(1, 72)})
                self.assertEqual(len(load(stage / "kb/index.json")), 1 if bare else 2)
                self.assertEqual(coverage["tasks"]["g0002-read"], "COMPLETE_UNREVIEWED")
                issue = coverage["extraction_issues"]["g0001-read"]
                if bare:
                    self.assertEqual(issue["reason"], "response_shape")
                else:
                    self.assertEqual(issue["rejected_rows"], {"locator_outside_evidence": 1})
                self.assertNotIn("/photos/", (stage / "kb/coverage.json").read_text())
                original = ledger.result("g0001-read")["text"]
                if advisory == legacy:
                    self.assertIn("/photos/3112376640116232.jpg", original)
