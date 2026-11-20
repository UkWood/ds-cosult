from pathlib import Path
from unittest.mock import patch

import pytest

from ds_dc.pdf_policy import OWNER_EXCLUDED, inspect_pdf, dossier_availability
from ds_dc.runtime import coverage_status


@pytest.mark.parametrize(("states", "expected"), [
    (["ready", "ready"], ("ready", "complete")),
    (["ready", "origin_http_error"], ("ready", "partial")),
    (["ready", "invalid_pdf"], ("ready", "partial")),
    (["ready", "structure_check_failed"], ("ready", "partial")),
    (["ready", "EXCLUDED_BY_OWNER"], ("ready", "complete")),
])
def test_document_errors_are_local(states, expected):
    assert dossier_availability(states, has_pages=True) == expected
    assert dossier_availability(["ready"], has_pages=True) == ("ready", "complete")


@pytest.mark.parametrize(("required", "confirmed", "expected"), [
    (["mass"], ["mass"], "complete"),
    (["mass", "storage"], ["mass"], "partial"),
    (["mass"], [], "insufficient"),
])
def test_answer_coverage_independent_of_dossier(required, confirmed, expected):
    assert coverage_status(required, confirmed) == expected


def test_standard_pdf_navigation_is_passive(tmp_path):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"%PDF-1.4\n%%EOF\n")
    with patch("ds_dc.pdf_policy.pdf_tool", side_effect=[
            "Pages: 1\nJavaScript: yes\nSuspects: yes\n", "Technical text\f"]):
        result = inspect_pdf(path)
    assert result["state"] == "extractable"
    assert result["pages_processed"] == 1


def test_missing_owner_link_is_explicit():
    assert OWNER_EXCLUDED == {"https://www.mnppsaturn.ru/photos/2278872612744825.pdf"}


def test_incomplete_dossier_dispatches_and_renders_verified_parts(tmp_path):
    from ds_dc.runtime import Journal, MockD1, Pilot, ReviewedEvidence

    entries = {}
    registry = {}
    for name in ("БКД-Т1", "БКД-Т2"):
        entries[name] = dict(id=name, kind="device", title=name, draft=False, features={},
                             body="", path=f"{name}.md", sha256="p", raw=name,
                             variant=None, canonical=f"/{name}/")
        registry[name] = dict(id=name, pages=[name], state="ready", docs=[], issues=[],
                               included_docs=[], completeness="complete")
    missing = dict(url="https://www.mnppsaturn.ru/missing.pdf", state="origin_http_error")
    registry["БКД-Т1"]["issues"] = [missing]
    registry["БКД-Т1"]["completeness"] = "partial"

    def review(question, candidate, documents, diagnostics):
        if "масса" not in question:
            return ReviewedEvidence(("гарантия",), {})
        required = ("масса", "хранение") if "хранение" in question else ("масса",)
        return ReviewedEvidence(required, {"масса": "Подтверждённая масса."})

    provider = MockD1(1_000_000)
    pilot = Pilot(entries, registry, tmp_path, Journal(tmp_path / "journal"), provider, review=review)
    ip = "192.0.2.2"
    token = pilot.open(ip, 100)
    for number, (question, expectation) in enumerate([
        ("БКД-Т1 масса", "complete"),
        ("БКД-Т1 масса и хранение", "partial"),
        ("БКД-Т1 гарантия", "insufficient"),
        ("БКД-Т2 масса", "complete"),
    ]):
        result = pilot.ask(ip, token, str(number), question, now=100 + number)
        assert result["mock_posts"] == 1
        assert result["confirmed_answer"]["status"] == expectation
        assert result["document_diagnostics"] == ([missing] if number < 3 else [])
        if expectation != "complete":
            assert "Недостаточно" in result["confirmed_answer"]["text"]
    assert provider.chat_posts == 4


def test_owner_exclusion_cannot_make_a_download(tmp_path):
    from ds_dc.corpus import preflight

    url = next(iter(OWNER_EXCLUDED))
    with patch("ds_dc.corpus.subprocess.run") as run:
        assert preflight(url, {url}, tmp_path)["state"] == "EXCLUDED_BY_OWNER"
    run.assert_not_called()


def test_real_parser_distinguishes_damage_and_structural_failure(tmp_path):
    path = tmp_path / "damaged.pdf"
    path.write_bytes(b"%PDF-1.4\nbad")
    assert inspect_pdf(path)["state"] == "invalid_pdf"
    path.write_bytes(b"%PDF-1.4\nbad\n%%EOF\n")
    assert inspect_pdf(path)["state"] == "structure_check_failed"


def test_real_pdf_with_open_action_and_link_is_extracted(tmp_path):
    import io

    # Poppler is invoked as a text extractor. No renderer opens the action or URL.
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R /OpenAction [3 0 R /Fit] >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Annots [5 0 R] "
        b"/Contents 4 0 R /Resources << /Font << /F1 6 0 R >> >> >>",
        b"<< /Length 48 >>\nstream\nBT /F1 12 Tf 10 90 Td (Technical document) Tj ET\nendstream",
        b"<< /Type /Annot /Subtype /Link /Rect [0 0 20 20] "
        b"/A << /S /URI /URI (https://example.invalid/) >> >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    buffer = io.BytesIO(b"%PDF-1.4\n")
    buffer.seek(0, 2)
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(buffer.tell())
        buffer.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = buffer.tell()
    buffer.write(b"xref\n0 7\n0000000000 65535 f \n")
    for offset in offsets:
        buffer.write(f"{offset:010} 00000 n \n".encode())
    buffer.write(f"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path = tmp_path / "with-navigation.pdf"
    path.write_bytes(buffer.getvalue())
    assert inspect_pdf(path)["state"] == "extractable"


def test_redirect_cannot_request_owner_exclusion(tmp_path):
    from subprocess import CompletedProcess
    from ds_dc.corpus import preflight

    excluded = next(iter(OWNER_EXCLUDED))
    allowed = "https://www.mnppsaturn.ru/original.pdf"
    response = CompletedProcess([], 0, f"302\n200\n{excluded}\n", "")
    with patch("ds_dc.corpus.subprocess.run", return_value=response) as run:
        result = preflight(allowed, {allowed, excluded}, tmp_path)
    assert result["state"] == "EXCLUDED_BY_OWNER"
    assert run.call_count == 1


def test_reference_review_exposes_only_pinned_verified_scope():
    import os
    from ds_dc.corpus import BKD, PIN
    from ds_dc.reference_review import reference_review
    from ds_dc.runtime import render_reviewed

    cache = os.environ.get("DS_DC_CACHE")
    if not cache:
        pytest.skip("Requires the audited original cache")
    sha, pages = PIN[BKD]
    documents = [dict(scope=BKD, sha256=sha, pages=pages)]
    check = reference_review(Path(cache))
    for question, coverage in [
        ("Сколько весит БКД-ПК-RF.2?", "complete"),
        ("Какая масса БКД-ПК-RF.2 и условия хранения?", "partial"),
        ("Какова типичная масса БКД-ПК-RF.2?", "insufficient"),
        ("Масса БКД-ПК-RF.2: предельная или типичное значение?", "insufficient"),
    ]:
        assert render_reviewed(check(question, {}, documents, ()))["status"] == coverage
