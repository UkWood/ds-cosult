from dataclasses import replace
import hashlib

import pytest

from ds_pilot.experimental import evidence_ledger as ledger
from test_pdf_sources import fixture_bytes


def synthetic(tmp_path):
    raw = fixture_bytes()
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(raw)
    return ledger.Document("synthetic", pdf.name, hashlib.sha256(raw).hexdigest(), 4), pdf


def test_pins_precede_parser(tmp_path, monkeypatch):
    doc, pdf = synthetic(tmp_path)
    monkeypatch.setattr(ledger.pdfplumber, "open", lambda *_: pytest.fail("opened unpinned PDF"))
    with pytest.raises(ValueError, match="SHA-256"):
        ledger.read_document(replace(doc, sha256="0" * 64), pdf.parent, "bundle")


def test_physical_grid_and_text(tmp_path):
    doc, pdf = synthetic(tmp_path)
    refs, issues = ledger.read_document(doc, pdf.parent, "bundle")
    assert refs == ledger.read_document(doc, pdf.parent, "bundle")[0]
    cell = next(r for r in refs if r.quote == "Hours")
    assert (cell.physical_page, cell.locator.table, cell.locator.row, cell.locator.column) == (2, 1, 2, 2)
    assert cell.quote_sha256 == hashlib.sha256(b"Hours").hexdigest()
    assert cell.state == "locator_verified"
    assert any(r.physical_page == 1 and r.quote == "A synthetic text page." for r in refs)
    assert any(i.reason == "header_association_unverified" for i in issues)


def test_scope_is_explicit():
    general = ledger.Scope("sldks-1", "general")
    specific = ledger.Scope("sldks-1", "no-pc")
    assert ledger.scope_match(specific, specific) == "MATCH"
    assert ledger.scope_match(specific, general) == "MISMATCH"
    assert ledger.scope_match(general, ledger.Scope("sldks-2")) == "MISMATCH"
    assert ledger.scope_match(ledger.Scope("sldks-1"), general) == "UNKNOWN"
    assert ledger.scope_match(ledger.Scope("sldks-1", "general", "usl-a"),
                              ledger.Scope("sldks-1", "general", "usl-p")) == "MISMATCH"


def test_page_count_and_bundle_invalidation(tmp_path):
    doc, pdf = synthetic(tmp_path)
    bundle = ledger.SourceBundle("site", "inventory", (doc,))
    baseline = ledger.read_document(doc, pdf.parent, bundle.bundle_id)[0][0]
    for changed in (replace(bundle, parser_version="different"),
                    replace(bundle, extraction_policy_version="next"),
                    replace(bundle, source_inventory_manifest_id="new"),
                    replace(bundle, pdf_revisions=(replace(doc, sha256="f" * 64),))):
        assert changed.bundle_id != bundle.bundle_id
        assert ledger.read_document(doc, pdf.parent, changed.bundle_id)[0][0].evidence_id != baseline.evidence_id
    with pytest.raises(ValueError, match="Parser revision"):
        ledger.read_document(doc, pdf.parent, bundle.bundle_id, parser_version="different")
    with pytest.raises(ValueError, match="Physical page"):
        ledger.read_document(replace(doc, pages=5), pdf.parent, bundle.bundle_id)


def test_scoped_literals_never_cross_rows(tmp_path, monkeypatch):
    from types import SimpleNamespace

    doc, pdf = synthetic(tmp_path)
    rows = [
        ("Область применения", "Параметр", "Значение"),
        ("СЛДКС-1 общие характеристики", "частота", "10 Гц"),
        ("СЛДКС-1 без компьютера", "частота", "10 Гц"),
        ("СЛДКС-1 без компьютера", "ИБП", "не менее 1 ч* при отказе сети"),
        ("СЛДКС-1 общие характеристики", "RAM", "не менее 512 МБ"),
        ("СЛДКС-1 общие характеристики", "HDD", "не менее 40 ГБ"),
        ("СЛДКС-1 общие характеристики", "масса", "не более 0,5 кг"),
        ("СЛДКС-1 общие характеристики", "лифты", "150–300"),
        ("СЛДКС-1 общие характеристики УСЛ-А", "питание", "встроенный источник"),
        ("СЛДКС-1 общие характеристики УСЛ-П", "питание", "не поддерживается"),
        ("СЛДКС-1 общие характеристики", "SIM", "false"),
        ("СЛДКС-1 общие характеристики", "Link", "проверить концентратор"),
        ("СЛДКС-1 общие характеристики", "Link", "проверить кабель"),
    ]
    grid = SimpleNamespace(bbox=(10, 10, 310, 150), extract=lambda: rows, rows=[
        SimpleNamespace(cells=[(10 + c * 100, 10 + r * 10, 110 + c * 100, 20 + r * 10)
                               for c in range(3)])
        for r in range(len(rows))])
    monkeypatch.setattr(ledger, "page_regions", lambda page: ([], [grid], []) if page.page_number == 2
                        else ([], [], []))
    refs, issues = ledger.read_document(doc, pdf.parent, "bundle")
    all_assertions = ledger.candidates(refs)
    general = ledger.Scope("saturn:system:sldks-1", "general")
    no_pc = replace(general, variant_id="no-pc")
    scoped = all_assertions.applicable(general)
    assert [(r.source_attribute_label, r.source_literal) for r in scoped] == [
        (label, value) for scope, label, value in rows[1:] if scope == "СЛДКС-1 общие характеристики"]
    assert [r.source_literal for r in all_assertions.applicable(no_pc)] == [
        "10 Гц", "не менее 1 ч* при отказе сети"]
    assert all_assertions.applicable(replace(general, subject_entity_id="saturn:system:sldks-2")) == ()
    assert all_assertions.applicable(replace(general, component_id="usl-p"))[0].source_literal == "не поддерживается"
    assert all_assertions.applicable(replace(general, component_id="usl-a"))[0].source_literal == "встроенный источник"
    assert all(r.qualifiers_state == "requires_review" for r in scoped)
    assert all(ref.state == "locator_verified" for ref in refs)
    by_id = {r.evidence_id: r for r in refs}
    assert [by_id[a.context_evidence_ids[0]].locator.row for a in scoped] == [
        by_id[a.evidence_id].locator.row for a in scoped]
    assert not any(i.reason == "header_association_unverified" for i in issues)


def test_shortlist_leaves_complete_inventory_intact():
    scope = ledger.Scope("entity", "general")
    all_rows = tuple(ledger.SourceAssertionCandidate(str(i), f"literal {i}", scope)
                     for i in range(15))
    inventory = ledger.Ledger(all_rows)
    assert inventory.shortlist(scope) == all_rows[:12]
    assert inventory.applicable(scope) == all_rows
    assert inventory.applicable(ledger.Scope("entity")) == ()
    with pytest.raises(ValueError, match="limit"):
        inventory.shortlist(scope, 13)


def test_cli_ignores_user_manifest_and_writes_blocked_receipts(tmp_path, monkeypatch):
    import json

    output = tmp_path / "reports"
    (tmp_path / "manifest.json").write_text(json.dumps({"interpretation_reviewed": True,
                                                       "human_attested": True,
                                                       "published_verified_claims": 999}))
    assert ledger.build(tmp_path, output) == 1
    result = json.loads((output / "diagnostics.json").read_bytes())
    assert result["metrics"]["published_verified_claims"] == 0
    assert result["coverage_state"] == "partial_index"
    assert all(r["state"] == "blocked" for r in result["receipts"])
    assert result["evidence"] == result["assertions"] == []
    for line in (output / "SHA256SUMS").read_text().splitlines():
        digest, path = line.split("  ")
        assert digest == hashlib.sha256((output / path).read_bytes()).hexdigest()


def test_overlapping_tables_are_blocked(tmp_path, monkeypatch):
    from types import SimpleNamespace

    doc, pdf = synthetic(tmp_path)
    row = SimpleNamespace(cells=[(0, 0, 10, 10), (10, 0, 20, 10)])
    row2 = SimpleNamespace(cells=[(0, 10, 10, 20), (10, 10, 20, 20)])
    tables = [SimpleNamespace(bbox=(0, 0, 20, 20), rows=[row, row2],
                              extract=lambda: [["Параметр", "Значение"], ["x", "0,5"]])
              for _ in range(2)]
    monkeypatch.setattr(ledger, "page_regions", lambda page: ([], tables, []) if page.page_number == 2
                        else ([], [], []))
    refs, issues = ledger.read_document(doc, pdf.parent, "bundle")
    assert not refs
    assert [issue.table for issue in issues if issue.reason == "ambiguous_table_grid"] == [1, 2]


def test_synthetic_receipt_success(tmp_path, monkeypatch):
    import json

    doc, pdf = synthetic(tmp_path)
    bundle = ledger.SourceBundle("SYNTHETIC_ONLY", "synthetic", (replace(doc, title="СЛДКС-1"),))
    monkeypatch.setattr(ledger, "approved_bundle", lambda: bundle)
    output = tmp_path / "receipt"
    assert ledger.build(tmp_path, output) == 0
    diagnostics = json.loads((output / "diagnostics.json").read_bytes())
    assert diagnostics["receipts"][0]["physical_pages"] == 4
    assert diagnostics["metrics"]["evidence_refs_total"] > 0
    assert diagnostics["metrics"]["published_verified_claims"] == 0
    assert diagnostics["coverage_state"] == "partial_index"
    trace = json.loads((output / "context_trace.json").read_bytes())
    assert trace["document_contexts"][0]["scope_context"]["entity"]["value"] == doc.entity
    assert trace["document_contexts"][0]["scope_context"]["entity"]["provenance"][0]["relation"] == "document_title"
    assert diagnostics["assertions"] == []
    assert all(row["scope_context"]["entity"]["status"] == "unknown" for row in diagnostics["evidence"])


def test_caption_context_and_inventory_are_separate():
    refs = structural_fixture([
        (1, 1, "Таблица 1 — Основные технические характеристики СЛДКС-1",
         ["Параметр", "Значение"], [("частота", "10 Гц"), ("масса", "не более 0,5 кг*")]),
        (1, 2, "Таблица 13 — Основные технические характеристики СЛДКС-1 (без компьютера)",
         ["Параметр", "Значение"], [("частота", "10 Гц")]),
    ])
    result = ledger.candidates(refs)
    general = ledger.Scope("saturn:system:sldks-1", "general")
    assert len(result.assertions) == 3
    assert len(result.applicable(general)) == 2
    no_pc = result.applicable(replace(general, variant_id="no-pc"))[0]
    assert no_pc.source_literal == "10 Гц"
    assert no_pc.scope_context.variant.provenance[0].relation == "table_caption"
    assert no_pc.attribute_evidence_id != no_pc.evidence_id
    assert len(result.applicable(replace(general, subject_entity_id="saturn:system:sldks-2"))) == 0


def structural_fixture(tables):
    refs = []
    for page, number, caption, headers, rows in tables:
        top = number * 100
        def ref(locator, literal):
            return ledger.EvidenceRef("bundle", "doc", "rev", "0" * 64, ledger.PARSER,
                                      "", None, page, locator, literal, ledger.sha(literal.encode()))
        if caption:
            refs.append(ref(ledger.Locator("text_block", (10, top - 16, 165, top - 4),
                                          block=number), caption))
        header_refs = []
        for row, literals in enumerate([headers, *rows], 1):
            for column, literal in enumerate(literals, 1):
                x = 10 + (column - 1) * 100
                y = top + (row - 1) * 12
                cell = ref(ledger.Locator(
                    "table_cell", (x, y, x + 100, y + 12), table=number, row=row,
                    column=column, row_bbox=(10, y, 10 + len(headers) * 100, y + 12),
                    header=headers[column - 1] if row > 1 else None,
                    header_evidence_id=header_refs[column - 1].evidence_id if row > 1 else None),
                    literal)
                refs.append(cell)
                if row == 1:
                    header_refs.append(cell)
    return tuple(refs)


def test_continuation_requires_explicit_marker_and_matching_header():
    headers = ["Параметр", "Значение"]
    refs = structural_fixture([
        (1, 1, "Таблица 13 — Основные технические характеристики СЛДКС-1 (без компьютера)",
         headers, [("частота", "10 Гц")]),
        (2, 1, "Продолжение таблицы 13", headers, [("ИБП", "не менее 1 ч* при отказе сети")]),
        (3, 1, "Таблица 13", headers, [("ИБП", "не более 1 ч")]),
        (4, 1, "Продолжение таблицы 13", ["Значение", "Параметр"], [("0,5", "X")]),
    ])
    result = ledger.candidates(refs)
    scope = ledger.Scope("saturn:system:sldks-1", "no-pc")
    matches = result.applicable(scope)
    assert len(matches) == 2
    assert matches[1].source_literal == "не менее 1 ч* при отказе сети"
    assert [proof.relation for proof in matches[1].scope_context.variant.provenance] == [
        "table_caption", "continuation"]
    assert matches[1].scope_context.variant.provenance[1].physical_page == 2
    assert result.assertions[2].source_literal == "не более 1 ч"
    assert ledger.scope_match(result.assertions[2].scope_context, scope) == "UNKNOWN"
    assert not result.table_diagnostics[-1]["recognized_headers"]


def test_arm_and_blocks_have_distinct_component_contexts():
    refs = structural_fixture([
        (1, 1, "Таблица 9 - Основные технические характеристики АРМ диспетчера СЛДКС-1",
         ["Наименование параметра", "Значение"], [("ОЗУ", "512 МБ"), ("Диск", "40 ГБ")]),
        (2, 1, "Таблица 3 - Основные технические характеристики СЛДКС-1",
         ["Обозначение блока", "Назначение"], [("УСЛ-А", "источник"), ("УСЛ-П", "не поддерживается")]),
    ])
    result = ledger.candidates(refs)
    subject = ledger.Scope("saturn:system:sldks-1", "general")
    assert result.applicable(subject) == ()
    assert len(result.applicable(replace(subject, component_id="dispatcher-arm"))) == 2
    a, b = result.assertions[2:]
    assert a.kind == b.kind == "component_description"
    assert a.scope.component_id == "usl-a"
    assert b.scope.component_id == "usl-p"
    assert b.source_literal == "не поддерживается"
    assert ledger.scope_match(b.scope_context, replace(subject, component_id="usl-a")) == "MISMATCH"


def test_unknown_and_competing_context_never_decide_model():
    refs = structural_fixture([
        (1, 1, "Таблица 1 — Основные технические характеристики СЛДКС-1",
         ["Параметр", "Значение"], [("Питание", "24 В"), ("Для СЛДКС-2", "24 В")]),
        (2, 1, "Подпись к рисунку: СЛДКС-1", ["Параметр", "Значение"], [("Питание", "24 В")]),
    ])
    other = ledger.Scope("saturn:system:sldks-2", "general")
    result = ledger.candidates(refs)
    assert [ledger.scope_match(a.scope_context, other) for a in result.assertions] == [
        "MISMATCH", "UNKNOWN", "UNKNOWN"]
    blocked = [("rev", ledger.EvidenceCheck(1, "image", (10, 96, 150, 100)))]
    result = ledger.candidates(refs, blocked)
    assert ledger.scope_match(result.assertions[0].scope_context, other) == "UNKNOWN"


def test_unrecognized_columns_and_incomplete_row_do_not_create_pairs():
    refs = structural_fixture([
        (1, 1, None, ["Параметр", "Описание"], [("A", "Big")]),
        (2, 1, None, ["Значение", "Параметр"], [("Big", "A")]),
        (3, 1, None, ["Параметр", "Значение"], [("A", "Big")]),
    ])
    result = ledger.candidates(refs[:-1])
    assert len(result.contexts) == len(refs) - 1
    assert result.assertions == ()


def test_bundle_schema_revision_invalidates_context_ids(monkeypatch):
    from dataclasses import asdict

    bundle = ledger.approved_bundle()
    assert bundle.bundle_id == ledger.approved_bundle().bundle_id
    assert asdict(bundle)["extraction_policy_version"] == "exact-regions/2"
    assert bundle.manifest_fields()["schema"] == "experimental/ds-int-01a/2"
    monkeypatch.setattr(ledger, "SCHEMA", "different/schema")
    assert bundle.bundle_id != ledger.sha(ledger.json_bytes(dict(
        bundle.manifest_fields(), schema="experimental/ds-int-01a/2")))


def test_trace_reports_separate_denominators_and_exact_caption_proof():
    from ds_pilot.experimental.evidence_trace import build_trace

    doc = ledger.Document("saturn:system:sldks-1", "sldks.pdf", "0" * 64, 83)
    refs = tuple(replace(ref, source_revision_id=doc.source_revision_id,
                         source_document_id=doc.source_document_id)
                 for ref in structural_fixture([
                     (7, 1, "Таблица 1 - Основные технические характеристики СЛДКС-1",
                      ["Параметр", "Значение"], [("частота", "10 Гц")])
                 ]))
    headers = {ref.locator.column: ref.evidence_id for ref in refs if ref.locator.row == 1}
    refs = tuple(replace(ref, locator=replace(ref.locator, header_evidence_id=headers[ref.locator.column]))
                 if ref.locator.row == 2 else ref for ref in refs)
    result = ledger.candidates(refs)
    trace = build_trace((doc,), refs, result, (), ledger.Scope, ledger.scope_match, ledger.normalized)
    case = next(case for case in trace if case["case"] == "Q15/general")
    assert case["evidence_ref_scope"] == {"MATCH": 2, "MISMATCH": 0, "UNKNOWN": 3}
    assert case["candidate_scope"] == {"MATCH": 1, "MISMATCH": 0, "UNKNOWN": 0}
    assert case["candidates"][0]["scope_context"]["entity"]["provenance"][0]["evidence_id"] == refs[0].evidence_id


def test_unaligned_row_stays_in_evidence_inventory_without_candidate():
    refs = structural_fixture([
        (1, 1, None, ["Параметр", "Значение"], [("X", "24 В")]),
    ])
    altered = replace(refs[-1], locator=replace(refs[-1].locator, bbox=(111, 112, 210, 124)))
    result = ledger.candidates((*refs[:-1], altered))
    assert altered.evidence_id in result.contexts
    assert result.assertions == ()
    assert result.row_diagnostics[0]["reason_code"] == "row_header_geometry_unresolved"
