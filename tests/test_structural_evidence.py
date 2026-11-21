import os
from pathlib import Path

import pytest

from ds_dc.structural_pdf import row_cells
from ds_dc.technical_registry import Entity, Source, SourceRegistry, VERSION
from ds_dc.technical_verifier import verify


def test_merged_cell_does_not_cross_group_boundary():
    table = {"bbox": [0, 0, 30, 40], "rows": [
        [[[0, 0, 10, 10], "Header"], [[10, 0, 20, 10], "Cause"]],
        [[[0, 10, 10, 30], "First symptom"], [[10, 10, 20, 20], "A"]],
        [None, [[10, 20, 20, 30], "B"]],
        [[[0, 30, 10, 40], "Other symptom"], [[10, 30, 20, 40], "C"]],
    ]}
    assert row_cells(table, 2)[0]["text"] == "First symptom"
    assert row_cells(table, 3)[0]["text"] == "Other symptom"
    table["rows"][1][0][0][3] = 19
    assert row_cells(table, 2)[0] is None


def grid(headers, *rows):
    return {"tables": [{"bbox": [0, 0, len(headers) * 10, (len(rows) + 1) * 10],
                        "rows": [[[[c * 10, r * 10, (c + 1) * 10, (r + 1) * 10], s]
                                  for c, s in enumerate(row)] for r, row in enumerate((headers, *rows))]}]}


def registry(request="request-1", applicability="reviewed cover", generation="G1"):
    return SourceRegistry(request, "a" * 64, [Entity("machine:a", "Machine A", "G1")],
                          [Source("machine:a", generation, "pdf", "b" * 64, "id", "R1", 2,
                                  "https://example.test/manual", applicability)],
                          {"P1": "quantity?", "P2": "other?"})


def candidate(reg, kind, subject, value, unit, comparator, qualifier, condition, proof):
    entity = next(iter(reg.entities))
    source = next(iter(reg.sources))
    return {"version": VERSION, "request_id": reg.request_id, "wire_identity": reg.wire_identity,
            "claims": [dict(id="C1", entity=entity, kind=kind, subject=subject, value=value,
                            unit=unit, comparator=comparator, qualifier=qualifier, condition=condition,
                            parts=["P1"], evidence=[dict(role=role, source=source, page=1, quote=quote)
                                                    for role, quote in proof.items()])],
            "answer_claim_ids": ["C1"], "unresolved": []}


@pytest.mark.parametrize(("kind", "cell", "value", "comparator"), [
    ("quantity", "-5,25", "-5.25", "eq"),
    ("quantity_limit", "не более 10", "10", "le"),
    ("quantity_range", "от -3 до +6,1", ["-3", "6.1"], "range"),
])
def test_structural_numeric_values_and_coverage(kind, cell, value, comparator):
    reg = registry()
    page = grid(["parameter", "value", "unit", "condition", "qualifier"], ["speed", cell, "m/s", "dry", "rated"])
    proof = dict(subject="speed", value=cell, unit="m/s", condition="dry", qualifier="rated")
    packet = candidate(reg, kind, "speed", value, "m/s", comparator, "rated", "dry", proof)
    result = verify(packet, reg, lambda *_: page, reviewed_parts={"C1": {"P1"}})
    assert result["confirmed_claim_ids"] == ["C1"]
    assert result["claims"][0]["covered_parts"] == ["P1"]
    assert result["unresolved_parts"] == ["P2"]
    assert result["coverage"] == "semantic_pending"


@pytest.mark.parametrize(("field", "value", "status"), [
    ("value", "11", "contradicted"),
    ("value", "-10", "contradicted"),
    ("unit", "kg", "semantic_pending"),
    ("qualifier", "", "semantic_pending"),
    ("condition", "", "semantic_pending"),
    ("comparator", "eq", "semantic_pending"),
])
def test_numeric_mutations_are_not_supported(field, value, status):
    reg = registry()
    page = grid(["parameter", "value", "unit", "condition", "qualifier"], ["speed", "≤10", "m/s", "dry", "rated"])
    proof = dict(subject="speed", value="≤10", unit="m/s", condition="dry", qualifier="rated")
    packet = candidate(reg, "quantity_limit", "speed", "10", "m/s", "le", "rated", "dry", proof)
    packet["claims"][0][field] = value
    result = verify(packet, reg, lambda *_: page)
    assert result["claims"][0]["technical_status"] == status
    assert not result["confirmed_claim_ids"]


@pytest.mark.parametrize(("case", "expected"), [
    ("correct", "supported"),
    ("cross_row", "semantic_pending"),
    ("false_condition", "semantic_pending"),
    ("unconditional", "semantic_pending"),
    ("mandatory_order", "invalid"),
    ("exhaustive", "invalid"),
    ("foreign", "invalid"),
    ("unknown", "invalid"),
    ("generation", "semantic_pending"),
    ("applicability", "semantic_pending"),
    ("ambiguous", "semantic_pending"),
    ("bad_hint", "semantic_pending"),
    ("missing_page", "semantic_pending"),
])
def test_troubleshooting_links_require_same_row(case, expected):
    reg = registry(applicability=None if case == "applicability" else "reviewed cover",
                   generation="G2" if case == "generation" else "G1")
    header = ["symptom", "possible cause", "corrective action"]
    page = grid(header, ["No signal", "Cable broken", "Check cable"], ["No light", "No power", "Check PSU"])
    if case == "ambiguous":
        page["tables"] += page["tables"]
    packet = candidate(reg, "conditional_action", "Check cable", "", "", "", "conditional",
                       "Cable broken", {"cause": "Cable broken", "action": "Check cable"})
    claim = packet["claims"][0]
    if case == "cross_row":
        claim["evidence"][0]["quote"] = claim["condition"] = "No power"
    if case == "false_condition":
        claim["condition"] = "No power"
    if case == "unconditional":
        claim["condition"] = ""
    if case in {"mandatory_order", "exhaustive"}:
        claim["kind"] = case
    if case in {"foreign", "unknown"}:
        claim["evidence"][0]["source"] = next(iter(registry("other").sources)) if case == "foreign" else "S999"
    if case == "bad_hint":
        claim["evidence"][0]["hint"] = {"table": 0, "row": 2, "column": 1}

    def load(*_):
        if case == "missing_page":
            raise OSError("fixture absent")
        return page

    assert verify(packet, reg, load)["claims"][0]["technical_status"] == expected


def test_v1_does_not_accept_wrong_revision_and_v2_packet_rejects_wrong_request():
    reg = registry()
    source = next(iter(reg.sources.values()))
    locator = dict(doc_id=source.doc_id, sha256=source.sha256, revision="R2")
    assert reg.v1_source(locator, "Machine A") is None
    locator["revision"] = source.revision
    assert reg.v1_source(locator, "Machine A")
    assert reg.v1_source(locator, "Machine B") is None
    packet = candidate(reg, "symptom", "No signal", "", "", "", "observed", "", {"symptom": "No signal"})
    assert verify(packet | {"request_id": "other"}, reg, None)["status"] == "invalid_contract"


def test_invalid_claim_does_not_stop_other_claims_or_promote_possible_cause():
    reg = registry()
    page = grid(["symptom", "possible cause", "corrective action"], ["No signal", "Cable broken", "Check cable"])
    packet = candidate(reg, "possible_cause", "Cable broken", "", "", "", "possible",
                       "No signal", {"symptom": "No signal", "cause": "Cable broken"})
    packet["claims"].insert(0, {"id": "C0"})
    packet["claims"].append(packet["claims"][1] | {"id": "C2", "qualifier": "established"})
    assert [r["technical_status"] for r in verify(packet, reg, lambda *_: page)["claims"]] == [
        "invalid", "supported", "semantic_pending"]


def test_original_pdf_and_optional_real_replay():
    from ds_dc.structural_pdf import extract
    from ds_dc.structural_shadow import replay

    cache = os.getenv("DS_DC_CACHE")
    if not cache:
        pytest.skip("Frozen originals required for actual PDF")
    sha = "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a"
    actual = extract(Path(cache), sha, 60)
    table = actual["tables"][1]
    assert actual["identity"]["backend"] == "pdfplumber==0.11.9"
    assert row_cells(table, 2)[0] == row_cells(table, 3)[0]
    assert row_cells(table, 4)[0] != row_cells(table, 3)[0]
    for index in (2, 3):
        assert row_cells(table, index)[1]["row"] == row_cells(table, index)[2]["row"] == index
    fixture = os.getenv("DS_DC_Q01_CANDIDATE")
    if fixture:
        result = replay(Path(fixture), Path(os.environ["SATURN_SOURCE"]), Path(cache))
        assert result["v1"]["legacy"] == "invalid_locator"
        assert result["confirmed_claim_ids"] == ["1", "2", "3", "4", "5"]
        assert result["coverage"] == "semantic_pending"
