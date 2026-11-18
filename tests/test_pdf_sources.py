"""Synthetic selectable-text, ruled-table and drawing pages, without vendor binaries."""
from email.message import Message
import hashlib
import io
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from ds_pilot import pdf_sources as pdf
from ds_pilot.catalog import import_checkout, load_local
from ds_pilot.engine import Pilot


def fixture_bytes():
    def text_at(x, y, text):
        return f"BT /F1 12 Tf {x} {y} Td ({text}) Tj ET\n"

    grid = "20 620 200 100 re S 120 620 m 120 720 l S 20 670 m 220 670 l S\n"
    grid += text_at(32, 700, "Name") + text_at(132, 700, "Unit")
    grid += text_at(32, 650, "Reading") + text_at(132, 650, "Hours")
    streams = [text_at(50, 700, "A synthetic text page."), grid, "20 20 m 80 80 l S"]
    objects = ["<< /Type /Catalog /Pages 2 0 R >>",
               "<< /Type /Pages /Kids [4 0 R 6 0 R 8 0 R] /Count 3 >>",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    for i, content in enumerate(streams):
        objects.extend([
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2*i} 0 R >>",
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream"])
    raw = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(raw))
        raw.extend(f"{n} 0 obj\n{obj}\nendobj\n".encode())
    start = len(raw)
    raw.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        raw.extend(f"{offset:010} 00000 n \n".encode())
    raw.extend(f"trailer\n<< /Root 1 0 R /Size {len(offsets)} >>\nstartxref\n{start}\n%%EOF\n".encode())
    return bytes(raw)


def test_verified_offline_physical_pages(tmp_path):
    catalog = import_checkout(Path(os.environ["SATURN_SOURCE"]), tmp_path)
    raw = fixture_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    f = tmp_path / "test.pdf"
    f.write_bytes(raw)
    args = SimpleNamespace(command="import-pdf", path=f, data=tmp_path, entity="bkd",
                           document=None, expected_sha256=digest)
    receipt = pdf.run_command(args, catalog)
    assert receipt["page_count"] == 3 and receipt["sha256"] == digest
    assert pdf.run_command(args, catalog) == receipt
    catalog = load_local(tmp_path)
    docs = pdf.load_pdfs(catalog, tmp_path)
    assert len(docs) == 15
    page = catalog.records["bkd", "pdf_page_1"][0]
    assert page.evidence.url == receipt["url"] + "#page=1"
    assert catalog.search("synthetic", "bkd", 1)[0]["url"] == page.evidence.url
    assert page.evidence.locator == "PDF physical page 1"
    assert page.evidence.sha256 == digest and page.value == "A synthetic text page."
    assert ("bkd", "pdf_page_2") not in catalog.records
    assert ("bkd", "pdf_page_3") not in catalog.records
    pilot = Pilot(catalog, tmp_path / "pilot.sqlite", lab=True)
    response = pilot.ask("Покажи текст страницы 1 руководства БКД-ПК-RF.2?", "session", "one")
    assert response["status"] == "answered"
    assert response["verified_claims"][0]["citation"]["url"].endswith("#page=1")
    assert pilot.ask("Покажи текст страницы 3 руководства БКД-ПК-RF.2?",
                     "session", "three")["status"] == "needs_support"
    pages = pdf.extract(raw)
    assert pages[1]["tables"] == [[["Name", "Unit"], ["Reading", "Hours"]]]
    assert pages[2]["exclusion"]
    (tmp_path / "pdf" / (digest + ".pdf")).write_bytes(raw + b"tamper")
    with pytest.raises(ValueError, match="SHA-256"):
        pdf.load_pdfs(load_local(tmp_path), tmp_path)
    args.expected_sha256 = "0"*64
    with pytest.raises(ValueError, match="SHA-256"):
        pdf.run_command(args, catalog)
    args.entity, args.expected_sha256 = "sld", digest
    with pytest.raises(ValueError, match="DS-LV-01"):
        pdf.run_command(args, catalog)


def test_bounded_mime_redirect_and_signature(monkeypatch):
    source = pdf.Source("bkd", 2, "doc", "https://www.mnppsaturn.ru/test.pdf", "test", True)
    class Response(io.BytesIO):
        status = 200
        def geturl(self):
            return source.url

    response = Response(b"%PDF-1.4")
    response.headers = Message()
    response.headers["Content-Type"] = "text/html"
    monkeypatch.setattr(pdf, "build_opener", lambda _: SimpleNamespace(open=lambda *a, **kw: response))
    with pytest.raises(ValueError, match="application/pdf"):
        pdf.download(source)
    with pytest.raises(ValueError, match="redirect"):
        pdf.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other/")
    with pytest.raises(ValueError, match="signature"):
        pdf.read_bounded(io.BytesIO(b"not a PDF"))
    monkeypatch.setattr(pdf, "MAX_BYTES", 8)
    with pytest.raises(ValueError, match="size"):
        pdf.read_bounded(io.BytesIO(b"%PDF-123456"))
    monkeypatch.setattr(pdf, "MAX_PAGES", 2)
    with pytest.raises(ValueError):
        pdf.extract(fixture_bytes())
