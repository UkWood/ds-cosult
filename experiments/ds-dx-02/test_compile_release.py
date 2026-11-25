"""INT approval and failure regressions, using synthetic owner evidence."""
import os
import tempfile
import unittest
from pathlib import Path

from bundle import archive, sums
from compile_d import compile_snapshot
from compile_release import CARD_REVISION, MODES, TRANSPORT, approved_plan, release_plan
from protocol import Ledger, Stop, encode, kernel_release, load, reserve, runtime_digest, save, sha
from r4_a import draft_card, plan, score
from test_d import fake_reply
from sse import ChatStream


class ApprovedRelease(unittest.TestCase):
    def test_two_official_scores_and_finance_are_frozen(self):
        import shutil

        available = os.environ.get("DX02_PREFLIGHT_SOURCES")
        if not available:
            self.skipTest("INT regression requires pinned pilot data")
        with tempfile.TemporaryDirectory() as name:
            workspace = Path(name)
            source = workspace / "source-pilot"
            shutil.copytree(available, source)
            experiment = plan(source)
            card = draft_card(source, experiment)
            card["revision"] = CARD_REVISION
            for row in card["entries"]:
                if not row["expected"]:
                    row["expected"] = "fixture"
            card_path = workspace / "r4-a-plan/reviewed-card.json"
            frozen_path = card_path.with_name("manifest-frozen.json")
            save(card_path, card)
            card_sha = sha(card_path.read_bytes())
            save(frozen_path, dict(experiment=experiment, card_sha256=card_sha))
            frozen_sha = sha(frozen_path.read_bytes())
            c_plan = workspace / "r4-c-plan-reuse.json"
            save(c_plan, dict(experiment=dict(snapshot=experiment["snapshot"], cases=experiment["cases"][2:]),
                              streaming=True, card_sha256=card_sha, frozen_sha256=frozen_sha))
            for name, cases in (("r4-a", experiment["cases"][:2]), ("r4-c", experiment["cases"][2:])):
                state = workspace / f"private-{name}"
                owner = dict(identity=name, manifest_sha256=frozen_sha, frozen_sha256=frozen_sha,
                             card_sha256=card_sha, plan_sha256=sha(c_plan.read_bytes()))
                save(state / "owner-go.json", owner)
                ops, rows, marks = [], {}, {}
                for case in cases:
                    id_ = case["id"]
                    result = dict(cost_nd=100, usage={"prompt_tokens": 10})
                    checkpoint = state / name / (id_ + ".json")
                    save(checkpoint, result)
                    ops.append(dict(id=id_, stage=name, status="SETTLED", reserve_nd=reserve(8192),
                                    cost_nd=100, result_sha256=sha(checkpoint.read_bytes()),
                                    parameters=dict(TRANSPORT if name == "r4-c" else {}, thinking={
                                        "type": "disabled" if case["mode"] == "disabled" else "enabled"},
                                        **({"reasoning_effort": "low"} if case["mode"] == "low" else {}))))
                    rows[id_] = dict(accepted=0, usage=result["usage"], peak_nd=100, mode=case["mode"])
                    required = [row["id"] for row in card["entries"] if row["sample"] == id_[0]
                                and row["category"] in {"mandatory", "safety"}]
                    marks[id_] = dict(matched_required_ids=required, critical_omissions=[],
                                      unsupported_claims=0, preserves_conditions_and_units=True,
                                      visual_false_positives=0, actual_billing_nd=None)
                if name == "r4-a":
                    ops.append(dict(id="P-D", stage=name, status="UNKNOWN", reserve_nd=reserve(8192)))
                save(state / "ledger.json", dict(ops=ops, stages={name: {"identity": name}}))
                summary = dict(execution="live", snapshot=experiment["snapshot"], cases=rows)
                save(state / "engineering/score.json", score(card, marks, summary))
                entries = {"summary.json": encode(summary)}
                entries["SHA256SUMS"] = sums(entries)
                archive(workspace / f"reports-{name}/{name}-summary.zip", entries)
            save(workspace / "private-state/ledger.json", {"ops": []})
            save(workspace / "private-r3/ledger.json", {"ops": []})
            preflight = workspace / "preflight-r4-b/preflight.json"
            save(preflight, dict(snapshot=experiment["snapshot"], runtime=runtime_digest(), kernel=kernel_release(),
                                 paid_calls=0, offline="seccomp: socket EPERM", package_count=3, r4_b_int=True))
            inputs = (workspace, source, card_path, preflight)
            prepared = release_plan(*inputs)
            self.assertEqual(prepared["modes"], MODES)
            self.assertEqual(prepared["transport"], TRANSPORT)
            self.assertEqual(prepared["finance"]["r4_a_counted_nd"], 309_830_600)
            self.assertEqual(prepared["finance"]["r4_c_counted_nd"], 400)
            path = workspace / "int-plan.json"
            save(path, prepared)
            digest = sha(path.read_bytes())
            self.assertEqual(approved_plan(path, digest, *inputs), prepared)
            for name in ("r4-a", "r4-c"):
                report = workspace / f"private-{name}/engineering/score.json"
                raw = report.read_bytes()
                report.unlink()
                with self.assertRaises(Stop):
                    approved_plan(path, digest, *inputs)
                report.write_bytes(raw + b"\n")
                with self.assertRaises(Stop):
                    approved_plan(path, digest, *inputs)
                report.write_bytes(raw)
            save(path, dict(prepared, modes=dict(MODES, fusion="low")))
            for check in (digest, sha(path.read_bytes())):
                with self.assertRaises(Stop):
                    approved_plan(path, check, *inputs)
            save(path, prepared)
            finance = workspace / "private-r3/ledger.json"
            finance.write_bytes(finance.read_bytes() + b"\n")
            with self.assertRaises(Stop):
                approved_plan(path, digest, *inputs)


class CompilerSSE(unittest.TestCase):
    def test_incomplete_sse_and_invalid_usage_stop_full_compile(self):
        import http.client
        from unittest.mock import Mock, patch
        from protocol import transport

        for failure in ("eof", "usage"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as name:
                stage = Path(name)
                root = stage / "sources"
                save(root / "plan/context.json", {"A": ["text"], "B": ["another"]})
                save(root / "plan/images.json", {})
                save(root / "source-manifest.json", dict(records={key: {"kind": "astro", "lines": 1} for key in "AB"},
                     relations=[], boundary=[], settings={}, entity={"id": "sample", "type": "product"}))
                journal = Ledger(stage / "private/ledger.json", "compile", 10**9, 10**9, "test")
                connection = Mock(spec=http.client.HTTPSConnection)
                response = connection.getresponse.return_value
                response.status, response.length = 200, None
                response.getheader.side_effect = {"Content-Type": "text/event-stream"}.get
                usage = fake_reply(b"", "")["usage"]
                if failure == "usage":
                    usage["prompt_tokens"] = -1
                wire = sse_wire("stop", '{"status":"NO_SUPPORTED_CONTENT","facts":[]}', usage)
                response.read1.side_effect = [wire.removesuffix(b"data: [DONE]\n\n"), b""] if failure == "eof" else [wire]
                with patch("protocol.http.client.HTTPSConnection", return_value=connection), self.assertRaises(Stop):
                    compile_snapshot(root, stage / "kb", stage / "reports", journal, "test", transport("fake-private"))
                self.assertEqual(connection.request.call_count, 1)
                self.assertEqual(load(journal.path)["ops"][0]["status"], "UNKNOWN")
                self.assertEqual(load(journal.path)["ops"][0]["reserve_nd"], reserve(8192))
                self.assertTrue((stage / "reports/knowledge.zip").is_file())


def sse_wire(finish, text, usage):
    def chunk(delta, reason, counts):
        return (b"data: " + encode(dict(id="fixture", model="deepseek-flash",
                 choices=[dict(index=0, delta=delta, finish_reason=reason)], usage=counts))
                .replace(b"\n", b"") + b"\n\n")

    return (b": keep-alive\n\n" + chunk({"content": text}, None, None)
            + chunk({}, finish, usage) + b"data: [DONE]\n\n")


def stream_fixture(response):
    """Mock the provider's wire output while exercising the real assembler."""
    choice = response["choices"][0]
    stream = ChatStream()
    stream.feed(sse_wire(choice["finish_reason"], choice["message"]["content"], response["usage"]))
    return stream.assembled()
