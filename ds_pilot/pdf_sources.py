"""Import only PDF references from the two immutable primary dossier roots."""
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import pdfplumber
import yaml

from .catalog import COMMIT, EXPANDED, PINS, SITE, EvidenceRef, Fact
from .material import Passage

MAX_BYTES = 32 * 1024 * 1024
MAX_PAGES = 256
PRIMARY = {"bkd": 2, "sld": 8}
SLD_PIN = "f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f"
BKD_PIN = "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a"
REGION_VERSION = "regions-v1"
PARSER = "pdfplumber/" + pdfplumber.__version__


@dataclass(frozen=True)
class Source:
    entity: str
    index: int
    title: str
    url: str
    revision: str
    pdf: bool


def sources(data):
    directory = data / EXPANDED if (data / EXPANDED).is_dir() else data
    for entity, (_, _, _, blob) in PINS.items():
        raw = (directory / f"{entity}.md").read_bytes()
        if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != blob:
            raise ValueError("Invalid pinned dossier")
        fields = yaml.safe_load(raw.decode().split("---", 2)[1])
        for i, doc in enumerate(fields["documents"]):
            path = doc["url"]
            if not path.startswith("/") or path.startswith("//"):
                raise ValueError("Invalid dossier document URL")
            url = SITE + path
            parsed = urlsplit(url)
            if (parsed.scheme != "https" or parsed.netloc != "www.mnppsaturn.ru"
                    or parsed.query or parsed.fragment or "\\" in path):
                raise ValueError("Invalid manufacturer origin")
            yield Source(entity, i, doc["title"], url, doc.get("version", "unspecified"),
                         parsed.path.lower().endswith(".pdf"))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError(f"Manufacturer PDF redirect refused (HTTP {code})")


def read_bounded(stream):
    raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or not raw.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF signature or size")
    return raw


def download(source):
    req = Request(source.url, headers={"Accept": "application/pdf", "Accept-Encoding": "identity"})
    with build_opener(NoRedirect()).open(req, timeout=20) as response:
        if response.geturl() != source.url or response.status != 200:
            raise ValueError("Unexpected PDF download response")
        if response.headers.get_content_type() != "application/pdf":
            raise ValueError("Expected application/pdf from manufacturer")
        return read_bounded(response)


def digest(raw, source, expected):
    sha = hashlib.sha256(raw).hexdigest()
    if expected is not None and (not re.fullmatch("[0-9a-fA-F]{64}", expected)
                                 or expected.lower() != sha):
        raise ValueError("PDF SHA-256 mismatch")
    if source.entity == "sld" and source.index == PRIMARY["sld"] and sha != SLD_PIN:
        raise ValueError("PDF differs from DS-LV-01 original")
    return sha


def safe_grid(rows):
    if not rows or len(rows) < 2 or len(rows[0]) < 2:
        return False
    headers = rows[0]
    return (len(set(headers)) == len(headers)
            and all(len(row) == len(headers) and all(
                isinstance(cell, str) and cell.strip() and "(cid:" not in cell for cell in row
            ) for row in rows))


def bbox(obj):
    return [obj[key] for key in ("x0", "top", "x1", "bottom")]


def intersects(left, right):
    return (left[0] <= right[2] and right[0] <= left[2]
            and left[1] <= right[3] and right[1] <= left[3])


def page_regions(page):
    if len(page.chars) > 12000 or len(page.edges) > 2000:
        return [], [], [{"reason": "layout limit exceeded", "bbox": list(page.bbox)}]
    tables = page.find_tables()
    exclusions = [{"reason": "table requires row and cell proof", "bbox": list(t.bbox)} for t in tables]
    exclusions.extend({"reason": kind, "bbox": bbox(obj)}
                      for kind, objects in (
                          ("image", page.images), ("drawing", page.curves + page.edges),
                          ("rotated glyph", [c for c in page.chars if not c["upright"]]))
                      for obj in objects)
    blocks = []
    # Inspect complete lines before excluding them so a partially covered line
    # cannot lose a qualifier or negation and become apparently safe evidence.
    text_page = page.filter(lambda obj: obj["object_type"] != "char" or obj["upright"])
    for line in text_page.extract_text_lines(return_chars=True):
        bounds = bbox(line)
        if any(intersects(bounds, region["bbox"]) for region in exclusions):
            continue
        chars = sorted(line["chars"], key=lambda char: char["x0"])
        text = line["text"].strip()
        if not text or "(cid:" in text or "\ufffd" in text or any(
            right["x0"] - left["x1"] > 25 for left, right in zip(chars, chars[1:])
        ):
            exclusions.append({"reason": "ambiguous line", "bbox": bounds})
            continue
        if blocks:
            previous = blocks[-1]
            x0, top, x1, bottom = previous["bbox"]
            gap = bounds[1] - bottom
            aligned = abs(x0 - bounds[0]) <= 22 and min(x1, bounds[2]) - max(x0, bounds[0]) > 30
            bridge = [min(x0, bounds[0]), bottom, max(x1, bounds[2]), bounds[1]]
            if (0 <= gap <= 9 and aligned
                    and not any(intersects(bridge, region["bbox"]) for region in exclusions)):
                previous["text"] += "\n" + text
                previous["bbox"] = [bridge[0], top, bridge[2], bounds[3]]
                continue
        blocks.append({"text": text, "bbox": bounds, "kind": "selectable_text"})
    return blocks, tables, exclusions


def extract(raw):
    pages = []
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            if not 1 <= len(pdf.pages) <= MAX_PAGES:
                raise ValueError("PDF page count outside import bounds")
            for page in pdf.pages:
                blocks, tables, exclusions = page_regions(page)
                grids = []
                rows = []
                for table in tables:
                    grid = table.extract()
                    if safe_grid(grid):
                        grids.append(grid)
                    for index, (cells, row) in enumerate(zip(grid, table.rows), 1):
                        if not all(box and isinstance(text, str) and text.strip()
                                   and "(cid:" not in text and "\ufffd" not in text
                                   for box, text in zip(row.cells, cells)):
                            continue
                        rows.append({"text": " | ".join(cells), "bbox": list(row.bbox),
                                     "kind": "ruled_table_row", "row": index,
                                     "cells": [{"column": n, "bbox": list(box), "text": text}
                                               for n, (box, text) in enumerate(zip(row.cells, cells), 1)]})
                pages.append({"physical_page": page.page_number, "blocks": blocks, "rows": rows,
                              "tables": grids, "excluded_regions": exclusions,
                              "exclusion": None if blocks else "no eligible selectable text block"})
                page.close()
    except Exception as exc:
        raise ValueError("Unreadable PDF or unsupported page layout") from exc
    return pages


def put_once(path, content):
    """Publish only a complete immutable object, including across concurrent imports."""
    with NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        temp_path = Path(tmp.name)
        try:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            try:
                os.link(temp_path, path)
            except FileExistsError:
                if path.read_bytes() != content:
                    raise ValueError("A different PDF revision is already pinned")
        finally:
            temp_path.unlink(missing_ok=True)


def revision_for(source):
    if source.entity == "sld" and source.index == PRIMARY["sld"]:
        return "26.05.11 (DS-LV-01)"
    return source.revision


def stage(data, source, raw, expected):
    sha = digest(raw, source, expected)
    pages = extract(raw)
    root = data / "pdf"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    put_once(root / (sha + ".pdf"), raw)
    put_once(root / f"{sha}.{pdfplumber.__version__}.{REGION_VERSION}.json",
             json.dumps(pages, ensure_ascii=False, sort_keys=True).encode())
    receipt = {**asdict(source), "revision": revision_for(source), "commit": COMMIT,
               "sha256": sha, "bytes": len(raw), "page_count": len(pages), "parser": PARSER}
    put_once(root / f"{source.entity}-{source.index}.json",
             json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode())
    return receipt


def requested_page(clause):
    from .questions import ALIASES
    match = re.fullmatch(
        r"(?:покажи|приведи|процитируй)\s+(?:текст\s+)?(?:физической\s+)?страниц[уы]\s+"
        r"(\d{1,3})\s+(?:руководства|pdf)\s+(.+)", clause.strip())
    return f"pdf_page_{int(match[1])}" if match and ALIASES.fullmatch(match[2]) else None


def bkd_claims(source, sha, page):
    """Only explicit statements in the reviewed manual revision can prove these needs."""
    if (source.entity, source.index, sha) != ("bkd", PRIMARY["bkd"], BKD_PIN):
        return
    number = page["physical_page"]
    for block in page["blocks"] + (page["rows"] if number == 12 else []):
        text = re.sub(r"\s+", " ", block["text"].casefold().replace("ё", "е"))
        if number == 14:
            if (re.search(r"s[iі]m", text) and "одновременн" in text
                    and re.search(r"одновременн[^.!?]{0,100}(?:не\s+(?:поддержива|допуска|предусмотр|могут|работа)|невозмож)"
                                  r"|не\s+(?:поддержива|допуска|предусмотр|могут|работа)[^.!?]{0,65}одновременн", text)
                    and re.search(r"переключ\w*", text) and "программ" in text):
                yield "pdf_sim_operation", "SIM-карты одновременно не работают. Переключение выполняется программно.", block
        elif number == 12 and all(re.search(pattern, text) for pattern in (
            r"4g[ -]*div", r"антенн", r"\b[xх]w2\b", r"\bsma\b",
        )) and set(re.findall(r"\b[xх]w\d+\b", text)) <= {"xw2", "хw2"}:
            typed_row = block["kind"] == "ruled_table_row" and len(block["cells"]) >= 2
            if typed_row or ("разъем" in text and "подключ" in text and not re.search(
                r"не\s+подключ|запрещ|нельзя|не\s+предназнач", text
            )):
                yield ("pdf_div_connector",
                       "Дополнительная антенна 4G Div подключается к разъёму XW2 (SMA).", block)


def region_ref(source, sha, number, block, order, route):
    locator = f"PDF physical page {number}"
    structure = {k: v for k, v in block.items() if k != "text"}
    structure.update(order=order, physical_page=number, entity=source.entity,
                     revision=revision_for(source), scope="manufacturer manual",
                     extraction=REGION_VERSION)
    return EvidenceRef(source.url, locator, route, COMMIT, "", sha,
                       block["text"], source.url + f"#page={number}", PARSER, structure)


def load_pdfs(catalog, data):
    inventory = []
    indexed = {(unit.url, unit.locator) for unit in catalog.index.units if unit.url}
    root = data / "pdf"
    for source in sources(data):
        doc = {**asdict(source), "status": "not_downloaded" if source.pdf else "metadata_only"}
        inventory.append(doc)
        path = root / f"{source.entity}-{source.index}.json"
        error = root / f"{source.entity}-{source.index}.error"
        if error.exists() and not path.exists():
            doc.update(status="failed", error=error.read_text()[:320])
        if not source.pdf or not path.exists():
            continue
        receipt = json.loads(path.read_text())
        sha = receipt["sha256"]
        if not re.fullmatch("[0-9a-f]{64}", sha):
            raise ValueError("Invalid PDF cache pin")
        with (root / (sha + ".pdf")).open("rb") as f:
            raw = read_bounded(f)
        digest(raw, source, sha)
        pages = extract(raw)
        if (receipt["parser"] != PARSER or receipt["url"] != source.url
                or receipt["commit"] != COMMIT or receipt["page_count"] != len(pages)
                or receipt["bytes"] != len(raw) or receipt["revision"] != revision_for(source)):
            raise ValueError("Invalid PDF cache receipt")
        if any(receipt.get(k) != v for k, v in asdict(source).items() if k != "revision"):
            raise ValueError("PDF receipt does not match dossier metadata")
        doc.update(receipt, status="included", pages=[])
        for page in pages:
            n = page["physical_page"]
            doc["pages"].append({"physical_page": n, "exclusion": page["exclusion"],
                                 "table_count": len(page["tables"]),
                                 "excluded_regions": page["excluded_regions"],
                                 "accepted_blocks": len(page["blocks"])})
            attr = f"pdf_page_{n}" if source.index == PRIMARY[source.entity] else f"pdf_{source.index}_page_{n}"
            label = f"{source.title}, физическая стр. {n}"
            entity = catalog.entities[source.entity]
            records = []
            for order, block in enumerate(page["blocks"], 1):
                ev = region_ref(source, sha, n, block, order, entity.route)
                locator = f"{ev.locator}, block {order}"
                if (ev.url, locator) not in indexed:
                    catalog.index.add(Passage(source.entity, locator, n, n, label,
                                              ev.snippet, ev.snippet, ev.url), source.title)
                    indexed.add((ev.url, locator))
                records.append(Fact(f"{sha}:page:{n}:block:{order}", entity.id, attr,
                                    ev.snippet, label + "\n" + ev.snippet, ev))
            if records:
                catalog.records[(source.entity, attr)] = records
            for attribute, value, block in bkd_claims(source, sha, page):
                blocks = page["blocks"] if block["kind"] == "selectable_text" else page["rows"]
                order = blocks.index(block) + 1
                ev = region_ref(source, sha, n, block, order, entity.route)
                record = Fact(f"{sha}:page:{n}:{attribute}:{order}", entity.id, attribute, value, value, ev)
                ledger = catalog.records.setdefault((source.entity, attribute), [])
                if record not in ledger:
                    ledger.append(record)
        doc["accepted_blocks"] = sum(p["accepted_blocks"] for p in doc["pages"])
    acquired = [(d["entity"], d["index"], d["sha256"], PARSER, REGION_VERSION) for d in inventory
                if d["status"] == "included"]
    if acquired:
        base = catalog.coverage["bundle"].split("+pdf.")[0]
        pin = hashlib.sha256(json.dumps(acquired).encode()).hexdigest()
        catalog.coverage["bundle"] = f"{base}+pdf.{pin}"
    catalog.coverage["candidate_units"] = len(catalog.index.units)
    catalog.coverage["pdf_documents"] = inventory
    return inventory


def add_commands(sub):
    sub.add_parser("pdf-inventory")
    for name in ("download-pdf", "import-pdf"):
        p = sub.add_parser(name)
        p.add_argument("--entity", choices=PRIMARY, required=True)
        p.add_argument("--document", type=int, help="0-based dossier documents[] index (default: primary manual)")
        if name == "import-pdf":
            p.add_argument("path", type=Path)
        p.add_argument("--expected-sha256", required=name == "import-pdf")


def run_command(args, catalog):
    if args.command == "pdf-inventory":
        return {"documents": load_pdfs(catalog, args.data)}
    index = PRIMARY[args.entity] if args.document is None else args.document
    source = next((s for s in sources(args.data) if (s.entity, s.index) == (args.entity, index)), None)
    if source is None or not source.pdf:
        raise ValueError("Select a PDF index from pdf-inventory")
    if args.command == "import-pdf":
        with args.path.open("rb") as f:
            raw = read_bounded(f)
    else:
        try:
            raw = download(source)
        except (OSError, ValueError) as exc:
            root = args.data / "pdf"
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=root, delete=False, mode="w") as tmp:
                tmp.write(str(exc)[:320])
            Path(tmp.name).replace(root / f"{source.entity}-{source.index}.error")
            raise
    return stage(args.data, source, raw, args.expected_sha256)
