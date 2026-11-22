"""Evidence context regressions with independent layouts and a safe ZIP projection."""
import json

import pytest

from ds_dc.evidence_answer import assemble
from ds_dc.technical_verifier import inspect_claim
from test_structural_evidence import candidate, grid, registry


def block(text, x0, top, x1, bottom):
    return dict(text=text, x0=x0, top=top, x1=x1, bottom=bottom)


def layout(*blocks, top=300, height=375):
    page = grid(["symptom", "possible cause", "corrective action"],
                ["No indicator", "Open circuit", "Reconnect the wiring"])
    table, = page["tables"]
    left = 60
    widths = [left, 210, 360, 510]
    table["bbox"] = [left, top, widths[-1], top + 30]
    for i, row in enumerate(table["rows"]):
        for j, cell in enumerate(row):
            cell[0] = [widths[j], top + i * 15, widths[j + 1], top + (i + 1) * 15]
    page.update(blocks=blocks, size=[575, height], identity={"page": 18})
    return page


def action(reg):
    return candidate(reg, "conditional_action", "Reconnect the wiring", "", "", "", "conditional",
                     "Open circuit", dict(cause="Open circuit", action="Reconnect the wiring"))


def test_wrapped_safety_and_table_reference_preserve_relation_and_restrict_action():
    reg = registry()
    page = layout(
        block("Работы по ремонту оборудования должны проводиться обученным", 90, 234, 500, 246),
        block("квалифицированным персоналом. Оборудование должно быть", 65, 248, 503, 260),
        block("надежно заземлено. Признаки проявления неисправности, возможные причины и", 65, 262, 503, 274),
        block("действия по устранению неисправности приведены в таблице 8.", 65, 276, 410, 288),
        block("Таблица 8", 435, 290, 500, 300),
        block("18", 280, 340, 294, 351),
    )
    packet = action(reg)
    result = inspect_claim(packet["claims"][0], reg, lambda *_: page)
    assert result["technical_status"] == "supported"
    assert {(entry["category"], entry["reason"]) for entry in result["context_evidence"]} >= {
        ("safety", "general_work_safety"), ("navigation", "table_reference"),
        ("formatting", "physical_page_number"),
    }
    packet.update(version="candidate-answer/2.1", wire_identity="wire", evidence_extracts=[])
    rendered = assemble(json.dumps(packet), reg, "wire", lambda *_: page, {})
    assert not rendered["confirmed_elements"]
    assert "Reconnect" not in rendered["answer"]
    assert "требовани" in rendered["answer"]


def test_layout_heading_and_folio_are_structural_not_lexical_exemptions():
    reg = registry()
    page = layout(
        block("ABC.628912.110RE", 360, 19, 501, 31),
        block("Таблица 8 — Возможные неисправности", 66, 34, 490, 46),
        block("и способы их устранения", 66, 48, 270, 60),
        top=61,
    )
    result = inspect_claim(action(reg)["claims"][0], reg, lambda *_: page)
    assert result["technical_status"] == "supported"
    assert {entry["reason"] for entry in result["context_evidence"]} >= {
        "running_document_id", "table_caption",
    }


@pytest.mark.parametrize(("blocks", "reason"), [
    ([block("Редакция графиков и схем", 8, 260, 72, 272)], "detached_text"),
    ([block("25", 280, 332, 294, 343)], "unresolved_linked_text"),
    ([block("Модель B", 65, 268, 250, 280)], "applicability_text"),
    ([block("230 В", 65, 268, 250, 280)], "unresolved_linked_text"),
    ([block("Температура 25 °C", 65, 268, 250, 280)], "applicability_text"),
    ([block("Только для исполнения B.", 65, 332, 250, 343)], "applicability_text"),
    ([block("Оборудование должно быть заземлено только в режиме A.", 65, 332, 405, 343)],
     "applicability_text"),
    ([block("Таблица 8 — Возможные неисправности", 65, 267, 490, 279),
      block("при температуре 25 °C", 65, 281, 250, 293)], "applicability_text"),
])
def test_context_blocks_only_a_linked_constraint_or_unresolved_text(blocks, reason):
    reg = registry()
    result = inspect_claim(action(reg)["claims"][0], reg, lambda *_: layout(*blocks))
    assert reason in {entry["reason"] for entry in result["context_evidence"]}
    assert result["technical_status"] == ("supported" if reason == "detached_text" else "semantic_pending")
    assert result["relation_verified"]


def test_q01_zip_safe_context_projects_the_specific_blocker_without_text():
    from ds_dc.validation_dc03c import q01_evidence

    reg = registry()
    page = layout(block("Только для исполнения B. private note", 65, 332, 250, 343))
    claim = inspect_claim(action(reg)["claims"][0], reg, lambda *_: page)
    matrix = q01_evidence({"v1": {"legacy": "invalid_locator"}, "coverage": "semantic_pending",
                           "confirmed_claim_ids": [], "v2_claims": [claim]})
    result, = matrix["claims"]
    assert result["context_issues"] == ["unresolved_table_context"]
    assert result["context_evidence"] == [
        {"category": "applicability", "reason": "applicability_text", "boxes": [[65, 332, 250, 343]]}]
    assert result["flags"]["relation_verified"]
    assert "private note" not in json.dumps(matrix)


def test_historical_locator_gate_rejects_nested_coordinate_drift():
    from ds_dc.validation_dc03c import Q01_CELL_BOXES, Q01_LOCATOR_ROWS, q01_locators_preserved

    claims = [dict(locators=[dict(page=60, table=1, row=row, column=column,
                                bbox=list(Q01_CELL_BOXES[row, column])) for row, column in locations])
              for locations in Q01_LOCATOR_ROWS]
    assert q01_locators_preserved(claims)
    claims[-1]["locators"][-1]["bbox"][2] += 1
    assert not q01_locators_preserved(claims)


def test_frozen_original_table_context():
    import os
    from pathlib import Path

    from ds_dc.structural_pdf import extract, physical_rows, unresolved_table_context
    from ds_dc.validation_dc03c import Q01_CELL_BOXES

    sha = "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a"
    cache = os.environ.get("DS_DC_CACHE")
    if not cache:
        pytest.skip("Pinned original PDF cache required")
    page = extract(Path(cache), sha, 60)
    rows = [row for row in physical_rows(page) if row.table == 1 and row.row in {2, 3}]
    assert len(rows) == 2
    for row in rows:
        assert not unresolved_table_context(row)
        assert {item["reason"] for item in row.context_evidence} == {
            "general_work_safety", "table_reference", "table_caption", "physical_page_number"}
        assert any("заземлен" in item["text"] for item in row.context)
        for cell in row.cells:
            key = cell["row"], cell["column"]
            assert tuple(round(value, 3) for value in cell["bbox"]) == Q01_CELL_BOXES[key]
