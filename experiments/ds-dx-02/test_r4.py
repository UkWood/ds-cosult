"""Offline fixtures derived from the owner's R3 observations, never paid responses."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from compile_d import facts
from protocol import Ledger, Stop, chat, encode, load, reply, reserve
from test_d import fake_reply


class Inference(unittest.TestCase):
    def test_explicit_modes_independent_of_json(self):
        for mode in ("disabled", "low", "high"):
            body = chat("s", [], 8192, compile_task=True, mode=mode)
            self.assertEqual(body["thinking"]["type"], "disabled" if mode == "disabled" else "enabled")
            self.assertEqual(body.get("reasoning_effort"), None if mode == "disabled" else mode)
            self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertNotIn("reasoning_effort", chat("s", [], 8192, compile_task=True))
        self.assertNotIn("response_format", chat("s", [], 4096))

    def test_reasoning_only_and_invalid_rubric(self):
        task = dict(id="g0001-read", kind="extract", topic="technical-evidence", scope={"A": [1]},
                    images=[], limit=8192)
        row = dict(text="synthetic", applicability="sample", kind="source_assertion",
                   topic="../private/Некорректная рубрика", locators=["A:1"])
        for limit in (8192, 4096):
            for content, reasoning, state in (("", limit, "PARTIAL"), ("", None, "TRUNCATED"),
                                             (encode(dict(status="FACTS", facts=[row])).decode(), limit - 1, "TRUNCATED")):
                issue = {}
                result = dict(finish_reason="length", text=content, usage={"completion_tokens": limit,
                              "reasoning_tokens": reasoning})
                actual, rows = facts(result, dict(task, limit=limit), issue=issue)
                self.assertEqual(actual, state)
                if state == "PARTIAL":
                    self.assertEqual(issue["reason"], "reasoning_only_exhaustion")
                if content:
                    self.assertEqual(rows[0]["topic"], "technical-evidence")
                    self.assertEqual(issue["topic_normalized"], 1)


class Transport(unittest.TestCase):
    def test_usage_unknown_has_private_diagnostic_and_blocks(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            ledger = Ledger(root / "ledger.json", "compile", 10**9, 10**9, "test")
            response = fake_reply(b"", "bad")
            response["usage"]["prompt_tokens"] = -1
            body = encode(chat("s", [], 8192, compile_task=True))
            with self.assertRaises(Stop):
                ledger.execute("sample", "/chat/completions", body, reserve(8192),
                               lambda *args: response, lambda raw: reply(raw, 8192))
            op, = load(ledger.path)["ops"]
            self.assertEqual(op["status"], "UNKNOWN")
            diagnostic = load(root / "diagnostics/compile/sample.json")
            self.assertEqual(diagnostic["stage"], "usage")
            self.assertEqual(diagnostic["request_bytes"], len(body))
            self.assertEqual(diagnostic["mode"], "disabled")
            self.assertIsNotNone(diagnostic["ended_utc"])
            with self.assertRaises(Stop):
                Ledger(ledger.path, "compile", 10**9, 10**9, "test", resume=True)


class Recovery(unittest.TestCase):
    def test_http_timeout_invalid_json_and_persist_failures(self):
        import http.client
        from unittest.mock import Mock
        from protocol import transport

        for failure, value, stage in (("http", 429, "headers"), ("timeout", 200, "read"),
                                       ("decode", 200, "parse"), ("result", 200, "persist_result"),
                                       ("ledger", 200, "persist_ledger"), ("pending", None, "persist_pending")):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as name:
                from protocol import save
                root = Path(name)
                ledger = Ledger(root / "ledger.json", "compile", 10**9, 10**9, "test")
                conn = Mock(spec=http.client.HTTPSConnection)
                response = conn.getresponse.return_value
                response.status, response.length = value, 0
                response.getheader.return_value = "request-fixture"
                private_key = "fake-private-test-key"
                valid = encode(fake_reply(b"", "sample"))
                error_body = encode({"error": {"code": "rate_limit_error",
                                              "message": f"rate limit {private_key}"}})
                raw = {"http": error_body, "decode": b"invalid JSON"}.get(failure, valid)
                response.read1.side_effect = ([b"partial", TimeoutError("do not export detail")] if
                                              failure == "timeout" else [raw, b""])

                def persist(path, data):
                    if failure == "result" and path.parent.name == "compile" and "diagnostics" not in path.parts:
                        raise PermissionError("private path")
                    if failure == "ledger" and path == ledger.path and path.exists():
                        raise PermissionError("ledger fault")
                    if failure == "pending" and path == ledger.path and not path.exists():
                        raise PermissionError("pending write fault")
                    save(path, data)

                body = encode(chat("s", [], 8192, compile_task=True))
                with (patch("protocol.http.client.HTTPSConnection", return_value=conn),
                      patch("protocol.save", side_effect=persist), self.assertRaises(Stop)):
                    ledger.execute("sample", "/chat/completions", body, reserve(8192),
                                   transport(private_key), lambda raw: reply(raw, 8192))
                diag = load(root / "diagnostics/compile/sample.json")
                self.assertEqual(diag["stage"], stage)
                self.assertNotIn(private_key, json.dumps(diag))
                self.assertNotIn("private path", json.dumps(diag))
                self.assertEqual(conn.request.call_count, 0 if failure == "pending" else 1)
                if failure != "pending":
                    status = load(ledger.path)["ops"][0]["status"]
                    self.assertEqual(status, "PENDING" if failure == "ledger" else "UNKNOWN")
                    with self.assertRaises(Stop):
                        Ledger(ledger.path, "compile", 10**9, 10**9, "test", resume=True)
                if failure == "http":
                    self.assertEqual(diag["http_status"], 429)
                    self.assertEqual(diag["provider_error"]["code"], "rate_limit_error")
                    self.assertFalse(diag["raw_saved"])
                if failure == "ledger":
                    self.assertTrue(diag["result_saved"])
                if failure == "timeout":
                    self.assertEqual(diag["response_bytes"], 7)
                    self.assertFalse(diag["response_complete"])

    def test_read_only_aggregate_does_not_release_unknown(self):
        from reconcile import aggregate_csv, summarize
        from protocol import save, sha
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            ledger = root / "ledger.json"
            reserve_nd = reserve(4096)
            save(ledger, {"ops": [dict(id="g0002-visual-002", stage="compile",
                                      status="UNKNOWN", reserve_nd=reserve_nd)]})
            digest = sha(ledger.read_bytes())
            result = summarize(ledger)
            self.assertEqual(result["operations"][0]["checkpoint"], "absent")
            self.assertIsNone(result["operations"][0]["diagnostic"])
            self.assertEqual(result["retained_nd"], 304_915_200)
            self.assertTrue(result["blocked"])
            csv = root / "billing.csv"
            csv.write_text("time,model,usage_type,quantity,cost_usd,key\n"
                           "2026-11-25T10:00:00+03:00,deepseek-flash,request,17,0.079086966,private-key-id\n")
            self.assertEqual(aggregate_csv(csv)[0]["cost_nd"], 79_086_966)
            self.assertNotIn("private-key-id", json.dumps(aggregate_csv(csv)))
            self.assertEqual(sha(ledger.read_bytes()), digest)


class Matrix(unittest.TestCase):
    def pilot(self):
        import os
        path = os.environ.get("DX02_PREFLIGHT_SOURCES")
        if not path:
            self.skipTest("R4-A requires the pinned pilot snapshot")
        return Path(path)

    def test_matrix_same_evidence_and_fixed_caps(self):
        import os
        from bundle import archive as write_archive, sums
        from r4_a import draft_card, plan, run_matrix, score, validate_card
        from protocol import sha
        from zipfile import ZipFile
        root = self.pilot()
        snapshot_before = sha((root / "snapshot.json").read_bytes())
        experiment = plan(root)
        self.assertEqual(experiment["graph_bound_nd"], 1_850_952_000)
        draft = draft_card(root, experiment)
        self.assertEqual({row["sample"] for row in draft["entries"]}, {"A", "P", "V"})
        with self.assertRaises(Stop):
            validate_card(draft, experiment)
        draft["revision"] = "fixture-approved"
        for item in draft["entries"]:
            if item["sample"] == "V":
                item["expected"] = "fixture"
        validate_card(draft, experiment)
        mock_evidence = {}
        for failure in (None, 0, 1, 2, 3, 4, 5, 6, "budget"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as name:
                stage = Path(name)
                calls = []

                def post(endpoint, body, content_type):
                    calls.append((endpoint, body))
                    if len(calls) - 1 == failure:
                        raise TimeoutError("private-marker")
                    if endpoint == "/files":
                        self.assertEqual(sha(body.split(b"application/pdf\r\n\r\n")[1].rsplit(b"\r\n--", 1)[0]),
                                         experiment["upload"]["sha256"])
                        return dict(id="file-api-fixture", purpose="text_recognition",
                                    bytes=experiment["upload"]["size"], expires_at=4102444800)
                    result = fake_reply(body, "", "length")
                    limit = json.loads(body)["max_tokens"]
                    result["usage"].update(completion_tokens=limit,
                                           completion_tokens_details={"reasoning_tokens": limit})
                    return result

                cap = experiment["first_reserve_nd"] if failure == "budget" else 2 * 10**9
                ledger = Ledger(stage / "private/ledger.json", "r4-a", cap, 2 * 10**9, "matrix")
                report = run_matrix(root, experiment, ledger, post, stage / "reports")
                self.assertEqual(report["status"], "PARTIAL")
                with ZipFile(stage / "reports/r4-a-summary.zip") as archive:
                    public = archive.read("summary.json")
                    self.assertNotIn(b"file-api-fixture", public)
                    self.assertNotIn(b"private-marker", public)
                mock_evidence[f"matrix-{failure}.json"] = public
                if failure is None:
                    self.assertEqual(len(calls), 7)
                    self.assertEqual([op["id"] for op in ledger.data["ops"]],
                                     ["A-D", "A-L", "pdf-upload", "P-D", "P-L", "V-D", "V-L"])
                    chat_payloads = [json.loads(body) for endpoint, body in calls if endpoint == "/chat/completions"]
                    for disabled, low in zip(chat_payloads[::2], chat_payloads[1::2]):
                        self.assertEqual(disabled.pop("thinking"), {"type": "disabled"})
                        self.assertEqual(low.pop("thinking"), {"type": "enabled"})
                        self.assertEqual(low.pop("reasoning_effort"), "low")
                        self.assertEqual(disabled, low)
                    self.assertEqual(report["cases"]["V-L"]["issue"]["reason"], "reasoning_only_exhaustion")
                    review = load(stage / "private/engineering/review-template.json")
                    for id_, row in review.items():
                        row.update(unsupported_claims=0, preserves_conditions_and_units=False,
                                   visual_false_positives=0 if id_.startswith("V") else None,
                                   critical_omissions=[entry["id"] for entry in draft["entries"]
                                                       if entry["sample"] == id_[0] and entry["category"] == "safety"])
                    self.assertEqual(score(draft, review, report)["cases"]["A-D"]["required_fraction"], 0)
                elif failure == "budget":
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(report["stop_reason"], "DEFERRED_BUDGET")
                else:
                    self.assertEqual(len(calls), failure + 1)
                    self.assertEqual(report["stop_reason"], "UNKNOWN")
                    self.assertGreater(report["retained_nd"], 0)
                    with self.assertRaises(Stop):
                        Ledger(ledger.path, "r4-a", cap, 2 * 10**9, "matrix", resume=True)
        self.assertEqual(sha((root / "snapshot.json").read_bytes()), snapshot_before)
        output = os.environ.get("DX02_MOCK_EVIDENCE")
        if output:
            mock_evidence["SHA256SUMS"] = sums(mock_evidence)
            write_archive(Path(output) / "r4-a-mock.zip", mock_evidence)

    def test_scoped_unresolved_and_exact_dedup(self):
        from compile_d import merge
        tasks = [dict(id="one", scope={"A": [1]}, kind="extract", topic="technical-evidence"),
                 dict(id="two", scope={"B": [2]}, kind="extract", topic="technical-evidence")]
        row = dict(text="same", applicability="revision 1", kind="source_assertion", locators=["A:1"])
        other = dict(row, locators=["B:2"])
        result = merge(tasks, {"one": [row, dict(row, kind="unresolved")],
                               "two": [other, dict(other, applicability="revision 2"),
                                       dict(other, kind="unresolved")]})
        self.assertEqual(len(result), 4)
        scoped = [r for r in result if r["kind"] == "unresolved"]
        self.assertCountEqual([r["scope"] for r in scoped], [{"A": [1]}, {"B": [2]}])
        self.assertIn(["A:1", "B:2"], [r["locators"] for r in result])


class CompilerRecovery(unittest.TestCase):
    def test_reasoning_only_continues_without_child_requests(self):
        from compile_d import compile_snapshot
        from protocol import save
        import struct

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source = root / "source"
            records = {"A": {"kind": "astro", "lines": 71, "relation": "entity_card"},
                       "I-photo": {"kind": "image", "lines": 1}, "B": {"kind": "astro", "lines": 1}}
            save(source / "source-manifest.json", dict(records=records, settings={},
                 entity=dict(type="product", id="sample"), relations=[], boundary=[]))
            save(source / "plan/context.json", {"A": ["text"] * 71, "I-photo": ["image"], "B": ["text"]})
            save(source / "plan/images.json", {name: {"source": "I-photo", "line": 1}
                                              for name in ("one.png", "two.png")})
            image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + struct.pack(">II", 1, 1) + b"\0" * 9
            for image_name in ("one.png", "two.png"):
                path = source / "raw-illustrations" / image_name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(image)
            calls = []

            def post(endpoint, body, mime):
                sent = json.loads(body)
                task = json.loads(sent["messages"][1]["content"][1]["text"])["task"]
                calls.append(task["id"])
                limit = sent["max_tokens"]
                if set(task["scope"]) == {"B"}:
                    return fake_reply(body, '{"status":"NO_SUPPORTED_CONTENT","facts":[]}')
                reply = fake_reply(body, "", "length")
                reply["usage"].update(completion_tokens=limit, completion_tokens_details={"reasoning_tokens": limit})
                return reply

            ledger = Ledger(root / "private/ledger.json", "compile", 2 * 10**9, 2 * 10**9, "pins")
            self.assertEqual(compile_snapshot(source, root / "knowledge", root / "reports",
                                              ledger, "pins", post), "PARTIAL")
            self.assertEqual(calls, ["g0001-read", "g0002-visual-001", "g0003-read"])
            issues = load(root / "knowledge/coverage.json")["extraction_issues"]
            self.assertEqual({item["reason"] for item in issues.values()}, {"reasoning_only_exhaustion"})

    def test_finance_floor_and_independent_proof_are_nonmutating(self):
        from protocol import save, sha
        from reconcile import independent_proof, summarize, reviewed_links
        from r4_a import finances

        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            save(root / "private-state/ledger.json", {"ops": []})
            old = root / "private-r3/ledger.json"
            operation = dict(id="g0002-visual-002", stage="compile", status="UNKNOWN",
                             reserve_nd=304_915_200, request_sha256="a" * 64)
            save(old, {"ops": [operation]})
            before = old.read_bytes()
            financial = finances(root)
            self.assertEqual(financial["max_compile_nd"], 1_533_443_168)
            self.assertEqual(financial["max_total_nd"], 4_533_443_168)
            proof = root / "independent.json"
            save(proof, dict(request_sha256="a" * 64, disposition="provider_confirmed_no_charge"))
            approval = dict(operation=operation["id"], stage="compile", owner_go="fixture-decision",
                            disposition="provider_confirmed_no_charge", evidence_sha256=sha(proof.read_bytes()))
            decision = independent_proof(old, summarize(old), approval, proof)
            self.assertEqual(decision["provider_disposition"], "provider_confirmed_no_charge")
            self.assertTrue(summarize(old)["blocked"])
            self.assertEqual(old.read_bytes(), before)
            index = [{"fact_id": "a", "kind": "unresolved"}, {"fact_id": "b", "kind": "source_assertion"}]
            attestation = dict(knowledge_identity="pins", reviewer="engineering",
                links=[dict(unresolved="a", assertion="b", applicability_verified=True, evidence="verified")])
            self.assertEqual(reviewed_links(index, "pins", attestation)[0]["status"], "engineer_attested")
            self.assertEqual(index[0]["kind"], "unresolved")
