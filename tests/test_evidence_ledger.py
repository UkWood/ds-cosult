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
    bundle = ledger.SourceBundle("SYNTHETIC_ONLY", "synthetic", (doc,))
    monkeypatch.setattr(ledger, "approved_bundle", lambda: bundle)
    output = tmp_path / "receipt"
    assert ledger.build(tmp_path, output) == 0
    diagnostics = json.loads((output / "diagnostics.json").read_bytes())
    assert diagnostics["receipts"][0]["physical_pages"] == 4
    assert diagnostics["metrics"]["exact_locator_proof"] > 0
    assert diagnostics["metrics"]["published_verified_claims"] == 0
    assert diagnostics["coverage_state"] == "partial_index"
