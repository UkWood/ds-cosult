"""Bounded passive PDF structure extraction for selected physical pages."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from .pdf_policy import MAX_PAGES, MAX_SIZE

ADAPTER = "pdf-structure/1"
BACKEND = "0.11.9"
PARAMETERS = {"vertical_strategy": "lines", "horizontal_strategy": "lines",
              "snap_tolerance": 3, "join_tolerance": 3, "intersection_tolerance": 3}
OUTPUT_LIMIT = 8 * 1024 * 1024


def extract(cache: Path, sha256: str, page: int):
    if not re.fullmatch(r"[0-9a-f]{64}", sha256) or type(page) is not int or not 1 <= page <= MAX_PAGES:
        raise ValueError("invalid_pdf_identity")
    with (cache / (sha256 + ".pdf")).open("rb") as file:
        raw = file.read(MAX_SIZE + 1)
    if len(raw) > MAX_SIZE or not raw.startswith(b"%PDF-") or hashlib.sha256(raw).hexdigest() != sha256:
        raise ValueError("pdf_integrity")
    with tempfile.TemporaryFile() as output:
        subprocess.run(["prlimit", "--as=536870912", "--cpu=15", "--fsize=" + str(OUTPUT_LIMIT),
                        "--", sys.executable, "-m", "ds_dc.structural_pdf", str(page)],
                       input=raw, stdout=output, stderr=subprocess.DEVNULL, timeout=20, check=True)
        output.seek(0)
        data = json.load(output)
    return {"identity": {"sha256": sha256, "page": page, "adapter": ADAPTER,
                         "backend": "pdfplumber==" + BACKEND, "parameters": PARAMETERS.copy()}, **data}


def worker(raw, page):
    import pdfplumber

    if pdfplumber.__version__ != BACKEND:
        raise ValueError("pdf_backend_version")
    with pdfplumber.open(io.BytesIO(raw), pages=[page]) as pdf:
        physical, = pdf.pages
        if physical.page_number != page:
            raise ValueError("physical_page_mismatch")
        if len(physical.chars) > 40_000 or len(physical.edges) > 10_000:
            raise ValueError("structural_complexity_limit")
        tables = []
        for table in physical.find_tables(table_settings=PARAMETERS):
            rows = [[None if box is None else [box, text]
                     for box, text in zip(row.cells, strings, strict=True)]
                    for row, strings in zip(table.rows, table.extract(), strict=True)]
            tables.append({"bbox": table.bbox, "rows": rows})
        words = physical.extract_words()
        return {"size": [physical.width, physical.height], "tables": tables,
                "blocks": physical.extract_text_lines(return_chars=False),
                "words": [{key: word[key] for key in ("text", "x0", "x1", "top", "bottom")} for word in words]}


def row_cells(table, index):
    """Return only cells that geometrically cover this row in the header's column."""
    rows = table["rows"]
    headers = rows[0]
    tops = [min((cell[0][1] for cell in row if cell), default=None) for row in rows]
    result = []
    for column, header in enumerate(headers):
        matches = []
        bottom = tops[index + 1] if index + 1 < len(rows) else table["bbox"][3]
        if header and tops[index] is not None and bottom is not None and bottom > tops[index]:
            for origin in range(index + 1):
                cell = rows[origin][column] if column < len(rows[origin]) else None
                if not cell:
                    continue
                box, text = cell
                if (box[0] == header[0][0] and box[2] == header[0][2]
                        and box[1] <= tops[index] and box[3] >= bottom):
                    matches.append({"row": origin, "column": column, "bbox": box, "text": text})
        result.append(matches[0] if len(matches) == 1 else None)
    return result


@dataclass(frozen=True)
class PhysicalRow:
    table: int
    row: int
    headers: tuple
    cells: tuple
    context: tuple
    boxed: bool


QUALIFICATION = re.compile(
    r"примечан|ограничен|применим|исполнени|модификаци|только|режим|услови|"
    r"\b(?:notes?|only|except|unless|variant|mode|condition|applicability)\b", re.I)
_TROUBLESHOOTING_TITLE = (
    r"(?:перечень )?возможн(?:ые|ых) неисправност(?:и|ей)"
    r"(?: и (?:методы|способы|действия) (?:по )?(?:их )?устранени[яю])?")
NEUTRAL_CAPTION = re.compile(
    r"^(?:таблица\s+\d+(?:\.\d+)*|table\s+\d+)"
    r"(?:\s*[.\-–—:]\s*" + _TROUBLESHOOTING_TITLE + r")?\.?$|"
    r"^(?:\d+(?:\.\d+)*\.?\s+)?" + _TROUBLESHOOTING_TITLE + r"\.?$|"
    r"^возможные неисправности и (?:методы|способы) их устранения "
    r"приведены в таблице\s+\d+(?:\.\d+)*\.?$", re.I)


def unresolved_table_context(row):
    return any(not NEUTRAL_CAPTION.fullmatch(" ".join(block["text"].split())) for block in row.context)


def physical_rows(page):
    """Retain unknown columns and geolocated context before interpreting roles."""
    for index, table in enumerate(page["tables"]):
        if len(table["rows"]) < 2:
            continue
        left, top, right, bottom = table["bbox"]
        nearby = sorted((b for b in page.get("blocks", ())
                         if b["x0"] < right and b["x1"] > left
                         and (0 <= top - b["bottom"] <= 32 or 0 <= b["top"] - bottom <= 32)
                         and not any(b["x0"] < t["bbox"][2] and b["x1"] > t["bbox"][0]
                                     and b["top"] < t["bbox"][3] and b["bottom"] > t["bbox"][1]
                                     for t in page["tables"])),
                        key=lambda b: (b["top"], b["x0"]))
        # A closely adjoining line can qualify the table without a note prefix.
        preceding = [b for b in nearby if b["bottom"] <= top]
        following = [b for b in nearby if b["top"] >= bottom]
        has_following_context = any(b["top"] - bottom <= 12 or QUALIFICATION.search(b["text"])
                                    for b in following)
        context = preceding + following if has_following_context else preceding
        headers = tuple(table["rows"][0])
        boxed = all(h is not None for h in headers) and all(
            len(row) == len(headers) for row in table["rows"])
        for row in range(1, len(table["rows"])):
            yield PhysicalRow(index, row, headers, tuple(row_cells(table, row)), tuple(context), boxed)


if __name__ == "__main__":
    payload = sys.stdin.buffer.read(MAX_SIZE + 1)
    if len(payload) > MAX_SIZE:
        raise ValueError("pdf_size_limit")
    print(json.dumps(worker(payload, int(sys.argv[1])), ensure_ascii=False, allow_nan=False))
