import hashlib
import json

from ds_dc.evidence_answer import assemble
from ds_dc.technical_registry import Entity, Source, SourceRegistry
from test_structural_evidence import candidate, grid


def assembled():
    url = "https://www.mnppsaturn.ru/ftp/public/doc/manual.pdf"
    question = "Зелёный индикатор Link не горит?"
    registry = SourceRegistry(
        "private-request", "a" * 64, [Entity("machine:a", "Machine A", "G1")],
        [Source("machine:a", "G1", "pdf", "b" * 64, "c" * 64, "R1", 2, url, "reviewed cover")],
        {"P1": question},
    )
    page = grid(["symptom", "possible cause", "corrective action"],
                ["No light", "No link", "Check patch cable"])
    packet = candidate(registry, "conditional_action", "Check patch cable", "", "", "", "conditional", "No link",
                       {"cause": "No link", "action": "Check patch cable"})
    packet.update(version="candidate-answer/2.1", evidence_extracts=[
        dict(id="X1", entity=next(iter(registry.entities)), source=next(iter(registry.sources)),
             page=1, quote="No link", conditions=[], parts=["P1"])])
    raw = json.dumps(packet).encode()
    result = assemble(raw, registry, registry.wire_identity, lambda *_: page, {})
    provenance = dict(question_id="Q01-N", request_mode="mock_native", source_registry=registry.sources)
    return question, provenance, raw, result


def test_exact_assembled_answer_and_independent_disposition():
    from ds_dc.quality_report import build_report, markdown

    question, provenance, raw, result = assembled()
    report = build_report(question=question, provenance=provenance, candidate=raw, result=result, telemetry={})

    assert report["question"] == {"id": "Q01-N", "text": question}
    assert report["A"]["candidate_sha256"] == hashlib.sha256(raw).hexdigest()
    claim, = report["A"]["claims"]
    assert claim["subject"] == "Check patch cable"
    assert claim["condition"] == "No link"
    assert claim["evidence"][1]["quote"] == "Check patch cable"
    assert claim["verification"]["technical_status"] == "supported"
    assert claim["verification"]["reason_codes"] == ["verified_table_relation"]
    assert claim["publication"] == "conditional_action_restricted"
    extract, = report["A"]["evidence_extracts"]
    assert extract["quote"] == "No link"
    assert extract["verification"]["evidence_status"] == "source_verified"
    assert extract["publication"] == "reference_only"
    assert report["B"]["answer"] == result["answer"]
    assert "Check patch cable" not in report["B"]["answer"]
    assert report["B"]["citations"][0]["page"] == 1
    assert report["B"]["citations"][0]["url"].endswith("/manual.pdf")
    assert report["B"]["verified_facts"] == []
    assert report["B"]["source_verified_extracts"] == []
    assert report["B"]["unresolved"] == [question]
    assert report["expert_score"] == "NOT RUN"
    assert result["answer"] in markdown(report)
    assert "private-request" not in json.dumps(report)


def test_assembled_facts_and_literal_extracts_have_distinct_statuses():
    from ds_dc.quality_report import build_report

    url = "https://www.mnppsaturn.ru/ftp/public/doc/manual.pdf"
    question = "Какая масса прибора?"
    registry = SourceRegistry(
        "private-request", "a" * 64, [Entity("machine:a", "Machine A", "G1")],
        [Source("machine:a", "G1", "pdf", "b" * 64, "c" * 64, "R1", 2, url, "reviewed cover")],
        {"P1": question},
    )
    page = grid(["parameter", "value", "unit"], ["mass", "2", "kg"])
    page["size"] = (200, 300)
    page["blocks"] = [dict(x0=10, x1=90, top=100, bottom=110, text="Case is gray.")]
    packet = candidate(registry, "quantity", "mass", "2", "kg", "eq", "", "",
                       {"subject": "mass", "value": "2", "unit": "kg"})
    packet.update(version="candidate-answer/2.1", evidence_extracts=[
        dict(id="X1", entity=next(iter(registry.entities)), source=next(iter(registry.sources)),
             page=1, quote="Case is gray.", conditions=[], parts=["P1"])])
    raw = json.dumps(packet).encode()
    result = assemble(raw, registry, registry.wire_identity, lambda *_: page, {})
    report = build_report(question=question, provenance={"source_registry": registry.sources}, candidate=raw,
                          result=result, telemetry={})

    assert report["A"]["claims"][0]["publication"] == "published_as_verified_fact"
    assert report["A"]["evidence_extracts"][0]["publication"] == "published_as_source_verified_extract"
    fact, = report["B"]["verified_facts"]
    extract, = report["B"]["source_verified_extracts"]
    assert fact["claim_ids"] == ["C1"]
    assert fact["text"] == "Machine A. mass — 2 kg."
    assert extract["text"] == "Case is gray."
    assert extract["technical_status"] == "semantic_pending"
    assert report["B"]["answer"] == result["answer"]


def test_invalid_candidate_preserves_digest_cost_and_assembled_diagnostic():
    from ds_dc.quality_report import build_report, markdown

    question, provenance, _, _ = assembled()
    raw = b'{"reasoning_content": "private thought", invalid'
    result = dict(status="invalid_contract", answer="Документальных выводов пока нет.")
    telemetry = dict(status="invalid_candidate", tokens={"prompt": 99, "reasoning": 21},
                     cost_micro_usd={"known": 7, "held": 0, "reserved": 9},
                     estimates_micro_usd={"total": 8})
    report = build_report(question=question, provenance=provenance, candidate=raw, result=result, telemetry=telemetry)

    assert report["A"]["candidate_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["A"]["export_status"] == "unavailable"
    assert report["A"]["claims"] == []
    assert report["B"]["status"] == "invalid_contract"
    assert report["B"]["answer"] == result["answer"]
    assert report["telemetry"]["tokens"] == {"prompt": 99, "reasoning": 21}
    assert report["telemetry"]["cost_micro_usd"] == {"known": 7, "held": 0, "reserved": 9}
    assert report["telemetry"]["estimates_micro_usd"] == {"total": 8}
    assert "private thought" not in markdown(report)


def test_private_data_in_technical_fields_and_nested_diagnostics_is_omitted():
    from ds_dc.quality_report import build_report, markdown

    question, provenance, raw, result = assembled()
    packet = json.loads(raw)
    packet["claims"][0].update(subject="Check opaque-LOCAL-983", reasoning_content="private thought",
                               condition="Open /home/private/operator/ledger")
    packet["evidence_extracts"][0]["conditions"] = ["192.168.250.1", "sk-local-private-key"]
    result["answer"] += "\n\nhttps://www.mnppsaturn.ru/ftp/public/doc/not-in-registry.pdf"
    result["diagnostics"]["claims"][0].update(
        reason_codes=["verified_table_relation", "local-permit-identifier"], physical_rows=["full PDF contents"],
    )
    result["citations"][0].update(url="https://www.mnppsaturn.ru/ftp/public/doc/not-in-registry.pdf",
                                  headers=["full PDF contents"])
    report = build_report(
        question=question, provenance={**provenance, "permit": "local-permit-identifier"},
        candidate=json.dumps(packet).encode(), result=result,
        telemetry={"private_values": ["opaque-LOCAL-983"], "raw_http_envelope": "private thought",
                   "timing_ms": {"upload": 125, "host": "probe.internal"}, "tokens": {"hit": True},
                   "diagnostics": ["incomplete_usage", "local-permit-identifier"]},
    )

    assert report["A"]["export_status"] == "partial"
    assert report["A"]["evidence_extracts"][0]["quote"] == "No link"
    assert report["A"]["claims"][0]["verification"]["reason_codes"] == ["verified_table_relation"]
    assert report["B"]["answer"] is None
    assert report["B"]["export_status"] == "partial"
    assert report["telemetry"]["timing_ms"] == {"upload": 125}
    assert report["telemetry"]["diagnostics"] == ["incomplete_usage"]
    exported = json.dumps(report, ensure_ascii=False, allow_nan=False) + markdown(report)
    for secret in ("opaque-LOCAL-983", "/home/private", "192.168.250.1", "sk-local-private-key",
                   "probe.internal", "local-permit-identifier", "full PDF contents", "private thought",
                   "not-in-registry.pdf"):
        assert secret not in exported


def test_record_when_chat_produced_no_candidate():
    from ds_dc.quality_report import build_report

    report = build_report(question="Link?", provenance={"question_id": "Q01-N", "request_mode": "mock_native"},
                          candidate=None, result=None, telemetry={"status": "provider_unknown"})
    assert report["A"]["export_status"] == "unavailable"
    assert report["A"]["candidate_sha256"] is None
    assert report["B"]["export_status"] == "unavailable"
    assert report["B"]["answer"] is None
    assert report["telemetry"]["status"] == "provider_unknown"
    assert report["expert_score"] == "NOT RUN"


def test_exact_answer_is_withheld_when_it_contains_an_oversized_source_extract():
    from ds_dc.quality_report import build_report

    long_excerpt = "A sentence from a source. " * 52
    result = dict(status="reference", answer=f"В документации указано «{long_excerpt}».",
                  extracts=[dict(text=long_excerpt, source_verified=True, context=[], citations=[])])
    report = build_report(question="Link?", provenance={}, candidate=None, result=result, telemetry={})

    assert report["B"]["export_status"] == "partial"
    assert report["B"]["answer"] is None
    assert long_excerpt not in json.dumps(report)
