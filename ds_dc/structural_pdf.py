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
from unicodedata import normalize

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
    context_evidence: tuple


QUALIFICATION = re.compile(
    r"примечан|ограничен|применим|исполнени|модификаци|модел[ьи]|только|режим|услови|испытан|температур|"
    r"\b(?:при|notes?|only|except|unless|variant|mode|condition|applicability|under)\b", re.I)
_TROUBLESHOOTING_TITLE = (
    r"(?:перечень )?возможн(?:ые|ых) неисправност(?:и|ей)"
    r"(?: и (?:методы|способы|действия) (?:по )?(?:их )?устранени[яю])?")
NEUTRAL_CAPTION = re.compile(
    r"^(?:таблица\s+\d+(?:\.\d+)*|table\s+\d+)"
    r"(?:\s*[.\-–—:]\s*" + _TROUBLESHOOTING_TITLE + r")?\.?$|"
    r"^(?:\d+(?:\.\d+)*\.?\s+)?" + _TROUBLESHOOTING_TITLE + r"\.?$", re.I)
TABLE_REFERENCE = re.compile(
    r"(?:признаки проявления неисправности, возможные причины и действия по устранению неисправности"
    r"|возможные неисправности и (?:методы|способы) их устранения)"
    r" приведены в таблице\s+\d+(?:\.\d+)*\.?", re.I)
DOCUMENT_ID = re.compile(r"[A-ZА-ЯЁ]{2,8}\.\d{3,8}\.\d{3,8}[A-ZА-ЯЁ]{1,4}")
PAGE_NUMBER = re.compile(r"(?:[Сс]тр\.\s*|[Pp]age\s+)?([1-9][0-9]{0,3})")
# Full sentences only. Additional wording (including a scope qualifier) must
# remain in evidence, even if it mentions one of these work-safety rules.
WORK_SAFETY = tuple(re.compile(pattern + r"\.?", re.I) for pattern in (
    r"работы по (?:текущему )?(?:ремонту|техническому обслуживанию)"
    r"(?: контроллера| изделия| оборудования| устройства)? должны проводиться"
    r" (?:обученным )?квалифицированным персоналом",
    r"перед поиском неисправности и (?:текущим )?ремонтом необходимо ознакомиться"
    r" с принципом действия и работой (?:контроллера|изделия|оборудования|устройства)",
    r"измерительные приборы и оборудование, подлежащие заземлению, должны быть над[её]жно заземлены",
    r"оборудование должно быть (?:над[её]жно )?заземлено",
))


def unresolved_table_context(row):
    return any(item["category"] in {"applicability", "unresolved"} for item in row.context_evidence)


def line_text(text):
    return " ".join(normalize("NFC", text).split())


def line_box(block):
    return [block[key] for key in ("x0", "top", "x1", "bottom")]


def margin_role(page, table_box, block):
    size = page.get("size")
    if not size:
        return None
    width, height = size
    text = line_text(block["text"])
    if 0 <= block["top"] <= block["bottom"] <= min(42, height * .10) and DOCUMENT_ID.fullmatch(text):
        return "running_document_id"
    match = PAGE_NUMBER.fullmatch(text)
    if (match and int(match[1]) == page.get("identity", {}).get("page")
            and 0 <= height - block["bottom"] <= min(48, height * .09)
            and block["top"] >= height * .9
            and abs((block["x0"] + block["x1"] - table_box[0] - table_box[2]) / 2) <= min(24, width * .06)):
        return "physical_page_number"
    return None


def lines_join(previous, line):
    old_height = previous["bottom"] - previous["top"]
    height = line["bottom"] - line["top"]
    return (old_height > 0 and .8 <= height / old_height <= 1.25
            and 0 <= line["top"] - previous["bottom"] <= min(7, .65 * old_height)
            and min(abs(line[key] - previous[key]) for key in ("x0", "x1")) <= 38
            and line["x0"] < previous["x1"] and line["x1"] > previous["x0"])


def outside_table_lines(page):
    return sorted((line for line in page.get("blocks", ())
                   if not any(line["x0"] < t["bbox"][2] and line["x1"] > t["bbox"][0]
                              and line["top"] < t["bbox"][3] and line["bottom"] > t["bbox"][1]
                              for t in page["tables"])),
                  key=lambda line: (line["top"], line["x0"]))


def context_groups(page, table, outside):
    left, top, right, bottom = table["bbox"]
    groups = []
    for line in outside:
        if line["x0"] >= right or line["x1"] <= left:
            continue
        margin = margin_role(page, table["bbox"], line)
        if groups and not (groups[-1][0] or margin) and lines_join(groups[-1][1][-1], line):
            groups[-1][1].append(line)
        else:
            groups.append((margin, [line]))

    neighbors = []
    for margin, lines in groups:
        gap = top - lines[-1]["bottom"] if lines[-1]["bottom"] <= top else lines[0]["top"] - bottom
        if 0 <= gap <= 32:
            neighbors.append((margin, lines, gap, " ".join(line_text(line["text"]) for line in lines)))
    captions = [lines[0]["top"] for margin, lines, gap, text in neighbors
                if not margin and gap <= 12 and NEUTRAL_CAPTION.fullmatch(text)]
    retained, evidence = [], []
    for margin, lines, gap, text in neighbors:
        retain = True
        if margin:
            classifications = [("formatting", margin)]
            retain = False
        elif NEUTRAL_CAPTION.fullmatch(text):
            classifications = [("navigation", "table_caption")]
            retain = False
        else:
            # White space alone does not prove a heading or note is unrelated.
            # A detached nearby line must sit mostly outside the table column.
            in_lane = any(min(right, line["x1"]) - max(left, line["x0"])
                          >= .5 * (line["x1"] - line["x0"]) for line in lines)
            attached = (gap <= 12 or in_lane or QUALIFICATION.search(text)
                        or any(0 <= start - lines[-1]["bottom"] <= 12 for start in captions))
            classifications = []
            for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ])", text):
                if TABLE_REFERENCE.fullmatch(sentence):
                    classifications.append(("navigation", "table_reference"))
                elif any(rule.fullmatch(sentence) for rule in WORK_SAFETY):
                    classifications.append(("safety", "general_work_safety"))
                elif QUALIFICATION.search(sentence):
                    classifications.append(("applicability", "applicability_text"))
                elif attached:
                    classifications.append(("unresolved", "unresolved_linked_text"))
                else:
                    classifications.append(("unlinked", "detached_text"))
            retain = any(kind in {"safety", "applicability", "unresolved"} for kind, _ in classifications)
        if retain:
            retained.extend(lines)
        boxes = [line_box(line) for line in lines]
        evidence.extend({"category": category, "reason": reason, "boxes": boxes}
                        for category, reason in dict.fromkeys(classifications))
    return tuple(retained), tuple(evidence)


def physical_rows(page):
    """Keep row context and classify adjacent document text before verifying claims."""
    outside = outside_table_lines(page)
    for index, table in enumerate(page["tables"]):
        if len(table["rows"]) < 2:
            continue
        context, evidence = context_groups(page, table, outside)
        headers = tuple(table["rows"][0])
        boxed = all(h is not None for h in headers) and all(
            len(row) == len(headers) for row in table["rows"])
        for row in range(1, len(table["rows"])):
            yield PhysicalRow(index, row, headers, tuple(row_cells(table, row)), context, boxed, evidence)


if __name__ == "__main__":
    payload = sys.stdin.buffer.read(MAX_SIZE + 1)
    if len(payload) > MAX_SIZE:
        raise ValueError("pdf_size_limit")
    print(json.dumps(worker(payload, int(sys.argv[1])), ensure_ascii=False, allow_nan=False))
