"""Closed experiment, pinned V2.1 wire, and independently checked accounting."""
import json
from dataclasses import replace

import httpx
import pytest

from ds_dc import quality_lab as lab
from ds_dc.corpus import BKD, digest
from ds_dc.finance import Stopped
from test_dc03c import synthetic_corpus


@pytest.fixture
def experiment(synthetic_corpus, monkeypatch):
    entries, dossiers, cache = synthetic_corpus
    entries[BKD].update(canonical="https://www.mnppsaturn.ru/products/mock-dc04a/",
                        production_url="https://www.mnppsaturn.ru/products/mock-dc04a/")
    first, = dossiers[BKD]["included_docs"]
    raw = (cache / (first["sha256"] + ".pdf")).read_bytes()
    docs = []
    for index in range(4):
        pdf = raw.replace(b"The device", f"The devic{index}".encode())
        sha = digest(pdf)
        (cache / (sha + ".pdf")).write_bytes(pdf)
        docs.append(first | {"sha256": sha, "pages": 20, "id": f"manual-{index}",
                             "field": f"documents[{index}]", "bytes": len(pdf),
                             "url": f"https://www.mnppsaturn.ru/ftp/public/doc/mock-dc04a-{index}.pdf"})
    dossiers[BKD].update(included_docs=docs, docs=docs)
    monkeypatch.setattr(lab, "MANIFEST", lab.freeze_digest(lab.freeze(entries, dossiers)))
    return lab.prepare_materials(entries, dossiers, cache, "a" * 40), cache


def test_wire_fixed_question_and_neutral_history(experiment):
    prepared, _ = experiment
    payload = json.loads(prepared.logical_payload)
    assert [part["file_id"] for part in payload["messages"][-1]["content"][:-2]] == [
        f"OFFLINE_SLOT_{i}" for i in range(1, 5)]
    query = json.loads(payload["messages"][-1]["content"][-1]["text"])
    assert query == {"question": "Что проверить, если на БКД-ПК-RF.2 не горит зелёный индикатор Link?",
                     "history": []}
    assert "Q01" not in prepared.logical_payload and "GT01" not in prepared.logical_payload
    assert "обрыв кабеля" not in prepared.logical_payload and all(sha not in prepared.logical_payload
                                                                  for sha, _ in prepared.files)
    assert "tools" not in payload and payload["stream"] is False


def test_live_entry_has_no_activation_path():
    with pytest.raises(Stopped, match="live_not_authorized"):
        lab.run_live()


NOW = 1_800_000_000
REVIEW = lab.MockContract(NOW, "b" * 64, ("https://api-docs.deepseek.com/mock/models",
                                        "https://api-docs.deepseek.com/mock/billing"))


def fake_boundary(experiment, mode="ok", *, mutate=None):
    import email
    from email import policy

    prepared, _ = experiment
    requests = []

    def receive(request):
        assert request.method == "POST" and str(request.url).startswith(lab.ORIGIN + "/")
        body = request.read()
        requests.append((request.url.path, body))
        if request.url.path == "/files":
            n = len(requests)
            sha, _ = prepared.files[n - 1]
            mime = email.message_from_bytes(b"Content-Type: " + request.headers["content-type"].encode()
                                             + b"\r\n\r\n" + body, policy=policy.default)
            fields = {part.get_param("name", header="content-disposition"): part for part in mime.iter_parts()}
            assert fields["file"].get_filename() == sha + ".pdf"
            assert digest(fields["file"].get_payload(decode=True)) == sha
            assert fields["purpose"].get_content() == lab.PURPOSE
            assert fields["expires_after[seconds]"].get_content() == str(lab.PARSE_TTL)
            assert fields["expires_after[anchor]"].get_content() == "created_at"
            if mode == "upload_rejected" and n == 2:
                return httpx.Response(413, json={"error": {"code": 413}})
            if mutate:
                mutate(n)
            return httpx.Response(200, json={
                "id": f"file-api-mock-{n if mode != 'duplicate_binding' else 1}",
                "object": "file", "purpose": lab.PURPOSE, "filename": sha + ".pdf",
                "bytes": len(fields["file"].get_payload(decode=True)), "created_at": NOW,
                "expires_at": NOW + (0 if mode == "ttl" else lab.PARSE_TTL),
            })
        assert request.url.path == "/chat/completions"
        packet = json.loads(body)
        parts = packet["messages"][-1]["content"]
        assert [part["file_id"] for part in parts[:-2]] == [f"file-api-mock-{i}" for i in range(1, 5)]
        assert packet["thinking"] == {"type": "enabled"} and packet["reasoning_effort"] == "high"
        assert packet["response_format"] == {"type": "json_object"} and packet["max_tokens"] == 8192
        assert not {"tool_calls", "tools", "web_search"} & packet.keys()
        meta = json.loads(parts[-2]["text"])
        assert meta["wire_identity"] == prepared.wire and meta["request_id"] == lab.REQUEST_ID
        if mode == "timeout":
            raise httpx.ReadTimeout("synthetic", request=request)
        entity = next(iter(meta["entities"]))
        source = next(key for key, obj in meta["sources"].items() if obj["kind"] == "site")
        candidate = dict(version="candidate-answer/2.1", request_id=meta["request_id"],
                         wire_identity=meta["wire_identity"], claims=[], answer_claim_ids=[],
                         unresolved=["P1"], evidence_extracts=[dict(id="mock-extract",
                             entity=entity, source=source, field="summary",
                             quote="Устройство хранит записи локально.", conditions=[], parts=["P1"])])
        if mode == "structural_only":
            candidate["evidence_extracts"] = []
        result = {
            "model": lab.ALIAS if mode != "drift" else "unreviewed-alias",
            "usage": {"prompt_tokens": 1000, "prompt_cache_hit_tokens": 100,
                      "prompt_cache_miss_tokens": 900, "completion_tokens": 40, "total_tokens": 1040,
                      "completion_tokens_details": {"reasoning_tokens": 10}},
            "choices": [{"message": {"content": json.dumps(candidate) if mode != "invalid" else "not JSON",
                                     "reasoning_content": "private-mock-reasoning"},
                         "finish_reason": "length" if mode in {"incomplete", "streamed_incomplete"} else "stop"}],
        }
        if mode == "unknown":
            result.pop("usage")
        if mode == "malformed_reasoning":
            result["usage"]["completion_tokens_details"]["reasoning_tokens"] = -1
        if mode == "overage":
            result["usage"].update(completion_tokens=9000, total_tokens=10000)
        if mode in {"compressed", "streamed_incomplete"}:
            import gzip

            zipped = gzip.compress(json.dumps(result).encode())
            if mode == "streamed_incomplete":
                return httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=httpx.ByteStream(zipped))
            return httpx.Response(200, headers={"Content-Encoding": "gzip"}, content=zipped)
        return httpx.Response(200, json=result)

    return httpx.MockTransport(receive), requests


def run_experiment(experiment, synthetic_corpus, mode="ok", *, mutate=None):
    entries, dossiers, cache = synthetic_corpus
    prepared, _ = experiment
    transport, requests = fake_boundary(experiment, mode, mutate=mutate)
    with lab.MockLab(entries, dossiers, cache, transport, clock=lambda: NOW) as native:
        permit = lab.proposed_mock_permit(prepared, REVIEW, native.ledger, NOW + 60)
        outcome = native.run(prepared, permit, REVIEW, head=prepared.commit)
        if requests[-1][0] == "/chat/completions" and mode != "timeout":
            assert b"private-mock-reasoning" in (native.private / "native-response.bin").read_bytes()
        with native.ledger.transaction(maintain=False) as state:
            rows = list(state["operations"].values())
        with pytest.raises(Stopped, match="duplicate_operation|provider_unknown|manifest_mismatch|dossier_drift"):
            native.run(prepared, permit, REVIEW, head=prepared.commit)
    return outcome, requests, rows


def test_native_cycle_preserves_exact_wire_and_reports(experiment, synthetic_corpus):
    import os
    from pathlib import Path

    from ds_dc.quality_report import build_report, markdown

    (candidate, result, telemetry, actual), requests, rows = run_experiment(experiment, synthetic_corpus)
    assert [route for route, _ in requests] == ["/files"] * 4 + ["/chat/completions"]
    assert actual == digest(requests[-1][1])
    assert telemetry["status"] == "completed" and result["status"] == "reference"
    assert telemetry["cost_micro_usd"] == {"known": 18319, "held": 0, "reserved": 348000}
    assert [r["state"] for r in rows] == ["settled"] * 5
    assert telemetry["tokens"]["reasoning"] == 10
    plan, _ = experiment
    report = build_report(question=lab.QUESTION, provenance={
        "question_id": lab.QUESTION_ID, "site_commit": lab.COMMIT, "corpus_sha256": plan.manifest,
        "commit": plan.commit, "prompt_version": lab.PROMPT_VERSION, "request_mode": "mock_native",
        "logical_wire_sha256": plan.wire, "logical_payload_sha256": plan.payload_digest,
        "actual_payload_sha256": actual, "provider_model": lab.ALIAS, "dossier": {"pdf_count": 4, "page_count": 80},
        "source_registry": plan.registry.sources,
    }, candidate=candidate, result=result, telemetry=telemetry)
    serialized = json.dumps(report, ensure_ascii=False)
    assert "private-mock-reasoning" not in serialized and "file-api-mock" not in serialized
    assert "Устройство хранит записи локально." in serialized
    assert report["B"]["answer"] == result["answer"]
    output = os.getenv("DC04A_REPORT_DIRECTORY")
    if output:
        (Path(output) / "dc04a-ab.json").write_text(serialized + "\n", encoding="utf-8")
        (Path(output) / "dc04a-ab.md").write_text(markdown(report), encoding="utf-8")


@pytest.mark.parametrize(("mode", "status", "calls", "tail_state", "held"), [
    ("upload_rejected", "provider_unknown", 2, "cancelled", True),
    ("duplicate_binding", "provider_unknown", 2, "cancelled", True),
    ("ttl", "provider_unknown", 1, "cancelled", True),
    ("unknown", "provider_unknown", 5, "unknown", True),
    ("timeout", "provider_unknown", 5, "unknown", True),
    ("overage", "provider_overage", 5, "unknown", True),
    ("drift", "provider_contract_drift", 5, "unknown", True),
    ("malformed_reasoning", "provider_contract_drift", 5, "unknown", True),
    ("incomplete", "incomplete_finish", 5, "unknown", True),
    ("streamed_incomplete", "incomplete_finish", 5, "unknown", True),
    ("invalid", "invalid_candidate", 5, "settled", False),
])
def test_fail_closed_without_retry(experiment, synthetic_corpus, mode, status, calls, tail_state, held):
    (candidate, result, telemetry, actual), requests, rows = run_experiment(experiment, synthetic_corpus, mode)
    assert len(requests) == calls
    assert sum(route == "/chat/completions" for route, _ in requests) == (calls == 5)
    assert telemetry["status"] == status
    assert rows[-1]["state"] == tail_state
    assert (telemetry["cost_micro_usd"]["held"] > 0) == held
    if mode == "invalid":
        assert candidate == b"not JSON" and result["status"] == "invalid_contract"
        assert rows[-1]["cost"] == 319 and telemetry["tokens"]["total"] == 1040
    if mode in {"incomplete", "streamed_incomplete", "malformed_reasoning"}:
        assert candidate and result is None and rows[-1]["cost"] == 319
        assert telemetry["tokens"]["total"] == 1040
    if mode == "malformed_reasoning":
        assert telemetry["tokens"]["reasoning"] is None
        assert "invalid_reasoning_usage" in telemetry["diagnostics"]


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("commit", "c" * 40, "permit_mismatch"),
    ("manifest", "b" * 64, "permit_mismatch"),
    ("wire", "c" * 64, "permit_mismatch"),
    ("payload_digest", "c" * 64, "permit_mismatch"),
    ("key_digest", "d" * 64, "permit_mismatch"),
    ("expires", NOW, "go_expired"),
    ("accepted_residual_risk", False, "permit_mismatch"),
])
def test_permit_rejection_before_network_or_reserve(experiment, synthetic_corpus, field, value, reason):
    plan, _ = experiment
    transport, requests = fake_boundary(experiment)
    with lab.MockLab(*synthetic_corpus, transport, clock=lambda: NOW) as native:
        permit = lab.proposed_mock_permit(plan, REVIEW, native.ledger, NOW + 60)
        with pytest.raises(Stopped, match=reason):
            native.run(plan, replace(permit, **{field: value}), REVIEW, head=plan.commit)
        with native.ledger.transaction(maintain=False) as state:
            assert state["operations"] == {}
    assert not requests


def test_no_permit_contract_freshness_ledger_guard_and_readonly(experiment, synthetic_corpus):
    plan, _ = experiment
    transport, requests = fake_boundary(experiment)
    with lab.MockLab(*synthetic_corpus, transport, clock=lambda: NOW) as native:
        old = replace(REVIEW, reviewed_at=NOW - 86401)
        old_permit = lab.proposed_mock_permit(plan, old, native.ledger, NOW + 60)
        with pytest.raises(Stopped, match="permit_required"):
            native.run(plan, None, REVIEW, head=plan.commit)
        with pytest.raises(Stopped, match="contract_unreviewed"):
            native.run(plan, old_permit, old, head=plan.commit)
        permit = lab.proposed_mock_permit(plan, REVIEW, native.ledger, NOW + 60)
        with native.ledger.transaction(maintain=False) as state:
            native.ledger.save(state)
        assert lab.inspect_ledger(native.ledger.path)["status"] == "original_operation_missing"
        with native.ledger.transaction(maintain=False) as state:
            state["operations"][lab.ORIGINAL_UPLOAD] = dict(state="unknown", kind="upload", reserve=14625,
                                                             pages=65, profile="owner", campaign=lab.CAMPAIGN)
            native.ledger.save(state)
        initial = native.ledger.file.read_bytes()
        old = lab.inspect_ledger(native.ledger.path)
        assert old["status"] == "blocked_unknown_or_pending" and old["original_accounted_micro_usd"] == 14625
        assert native.ledger.file.read_bytes() == initial
        with pytest.raises(Stopped, match="provider_unknown"):
            native.run(plan, permit, REVIEW, head=plan.commit)
        assert native.ledger.file.read_bytes() == initial
    assert not requests


def test_preserved_campaign_reserve_and_dossier_drift(experiment, synthetic_corpus):
    plan, cache = experiment
    transport, requests = fake_boundary(experiment)
    with lab.MockLab(*synthetic_corpus, transport, clock=lambda: NOW) as native:
        permit = lab.proposed_mock_permit(plan, REVIEW, native.ledger, NOW + 60)
        with native.ledger.transaction(maintain=False) as state:
            state["operations"]["previous"] = dict(state="settled", kind="upload", cost=1_700_000,
                                                   pages=65, profile="owner", campaign=lab.CAMPAIGN)
            native.ledger.save(state)
        with pytest.raises(Stopped, match="campaign_budget_exhausted"):
            native.run(plan, permit, REVIEW, head=plan.commit)
    assert requests == []
    sha, _ = plan.files[0]

    def change_after_upload(n):
        if n == 4:
            (cache / (sha + ".pdf")).write_bytes(b"modified during the mock upload")

    (candidate, result, telemetry, _), sent, rows = run_experiment(
        experiment, synthetic_corpus, mutate=change_after_upload)
    assert len(sent) == 4 and candidate is result is None
    assert telemetry["status"] == "dossier_drift" and rows[-1]["state"] == "cancelled"


def test_export_zip_allows_pinned_https_citations_and_rejects_private_paths(tmp_path):
    import importlib.util
    from argparse import Namespace
    from pathlib import Path
    from zipfile import ZipFile

    script = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc03c.py"
    spec = importlib.util.spec_from_file_location("dc04a_runner", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    run = runner.Run(Namespace(commit="a" * 40, site=None, cache=None, output=tmp_path), preparing=True)
    with pytest.raises(ValueError, match="screening_forbidden_pattern"):
        runner.screen("Receipt C:/private/ledger.json")
    report = {"A": {}, "B": {}, "expert_score": "NOT RUN", "provenance": {"request_mode": "mock_native"}}
    (run.private / runner.AB_REPORTS[0]).write_text(json.dumps(report), encoding="utf-8")
    (run.private / runner.AB_REPORTS[1]).write_text("https://www.mnppsaturn.ru/products/mock-dc04a/", encoding="utf-8")
    assert run.inspect("dc04a_ab_export", run.ab_report_evidence)
    (run.private / runner.AB_REPORTS[1]).write_text("raw reasoning substituted after screening", encoding="utf-8")
    archive = run.package(False)
    runner.verify_archive(archive)
    with ZipFile(archive) as zipped:
        assert set(runner.AB_REPORTS) <= set(zipped.namelist())
        assert zipped.read(runner.AB_REPORTS[1]).startswith(b"https://")



def test_already_decoded_http_body_is_not_decoded_twice(experiment, synthetic_corpus):
    (candidate, result, telemetry, _), requests, rows = run_experiment(experiment, synthetic_corpus, "compressed")
    assert len(requests) == 5 and rows[-1]["state"] == "settled"
    assert candidate and result["status"] == "reference" and telemetry["status"] == "completed"



def test_pinned_material_exact_http_wire_without_fabricated_claims():
    import os
    from pathlib import Path

    site, cache = (os.getenv(name) for name in ("SATURN_SOURCE", "DS_DC_CACHE"))
    if not site or not cache:
        pytest.skip("Pinned site and corpus required")
    entries, dossiers, _ = lab.load(Path(site), Path(cache))
    if lab.freeze_digest(lab.freeze(entries, dossiers)) != lab.MANIFEST:
        pytest.skip("Full pinned corpus required")
    plan = lab.prepare_materials(entries, dossiers, Path(cache), "a" * 40)
    assert plan.wire == "ef96558d67deda9a090471a2d6947a12e11a7cce81f77fec4cbe983eaf3f9735"
    assert plan.payload_digest == "bdc21ea15355867a2a26ea85ae6c4326a08650676e2f692b0624c31ea9025e60"
    outcome, requests, rows = run_experiment((plan, Path(cache)), (entries, dossiers, Path(cache)), "structural_only")
    candidate, result, telemetry, actual = outcome
    assert [route for route, _ in requests] == ["/files"] * 4 + ["/chat/completions"]
    assert not json.loads(candidate)["claims"] and not json.loads(candidate)["evidence_extracts"]
    assert not result["confirmed_elements"] and not result["extracts"]
    assert actual == digest(requests[-1][1])
    assert all(row["state"] == "settled" for row in rows)
    assert telemetry["status"] == "completed"


def test_runner_keeps_preflight_status_separate_from_acceptance_status(tmp_path):
    import importlib.util
    from argparse import Namespace
    from pathlib import Path
    import sys

    script = Path(__file__).resolve().parents[1] / "scripts/validation/validate_dc03c.py"
    spec = importlib.util.spec_from_file_location("dc04a_runner_child_status", script)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    run = runner.Run(Namespace(commit="a" * 40, site=tmp_path, cache=tmp_path,
                               fixture=tmp_path / "fixture", output=tmp_path))
    assert run.command("dc04a_preflight", [sys.executable, "-c",
                       'print(\'{"passed": true, "status": "ready_for_offline_acceptance"}\')'],
                       details=runner.child_evidence)
    assert run.steps["dc04a_preflight"]["status"] == "PASS"
    assert run.steps["dc04a_preflight"]["child_status"] == "ready_for_offline_acceptance"
