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


def extract(raw):
    pages = []
    try:
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            if not 1 <= len(pdf.pages) <= MAX_PAGES:
                raise ValueError("PDF page count outside import bounds")
            for page in pdf.pages:
                result = {"physical_page": page.page_number, "quote": "", "tables": [],
                          "exclusion": None}
                if page.images or page.curves or len(page.edges) > 600 or len(page.chars) > 12000:
                    result["exclusion"] = "image, drawing or complex layout"
                else:
                    tables = page.find_tables()
                    if tables:
                        grids = [table.extract() for table in tables]
                        # Keep row/column associations for inspection. A ruled diagram
                        # can resemble a grid, so table values need separate review.
                        result["tables"] = [grid for grid in grids if safe_grid(grid)]
                        result["exclusion"] = "table layout requires visual validation"
                    elif page.edges or any(not ch["upright"] for ch in page.chars):
                        result["exclusion"] = "drawing or ambiguous reading order"
                    else:
                        text = (page.extract_text() or "").strip()
                        # Quote selectable text only. Reject likely multi-column rows.
                        words = page.extract_words()
                        gaps = any(abs(b["top"] - a["top"]) < 2 and b["x0"] - a["x1"] > 35
                                   for a, b in zip(words, words[1:]))
                        if text and "(cid:" not in text and "\ufffd" not in text and not gaps:
                            result["quote"] = text
                        else:
                            result["exclusion"] = "missing text or ambiguous reading order"
                pages.append(result)
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
    put_once(root / f"{sha}.{pdfplumber.__version__}.json",
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


def load_pdfs(catalog, data):
    inventory = []
    indexed = {unit.url for unit in catalog.index.units if unit.url}
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
                                 "table_count": len(page["tables"])})
            if not page["quote"]:
                continue
            attr = f"pdf_page_{n}" if source.index == PRIMARY[source.entity] else f"pdf_{source.index}_page_{n}"
            label = f"{source.title}, физическая стр. {n}"
            ev = EvidenceRef(source.url, f"PDF physical page {n}", catalog.entities[source.entity].route,
                             COMMIT, "", sha, page["quote"], source.url + f"#page={n}", PARSER)
            if ev.url not in indexed:
                passage = Passage(source.entity, ev.locator, n, n, label, ev.snippet, ev.snippet, ev.url)
                catalog.index.add(passage, source.title)
                indexed.add(ev.url)
            obj = Fact(f"{source.entity}:{source.index}:{sha}:page:{n}", catalog.entities[source.entity].id, attr, page["quote"],
                       label + "\n" + page["quote"], ev)
            catalog.records[(source.entity, attr)] = [obj]
    acquired = [(d["entity"], d["index"], d["sha256"], PARSER) for d in inventory
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
