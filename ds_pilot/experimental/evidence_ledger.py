"""Local PDF evidence inventory. No runtime or publication entry points."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import re

import pdfminer
import pdfplumber
from pdfminer.pdfexceptions import PDFException

from .. import discovery
from ..pdf_sources import BKD_PIN, PRIMARY, SLD_PIN, page_regions, read_bounded, safe_grid

SCHEMA = "experimental/ds-int-01a/1"
EXTRACTION = "exact-regions/1"
APPROVED_SITE_MANIFEST_SHA256 = "78517ce8afca16bd4842df15f33685053261d3a49f5f5d7da6a395724e7b4ad6"
PARSER = f"pdfplumber/{pdfplumber.__version__}+pdfminer.six/{pdfminer.__version__}"
HEADERS = {
    ("параметр", "значение"),
    ("наименование параметра", "значение"),
    ("область применения", "параметр", "значение"),
}
MODELS = {
    "слдкс-1": "saturn:system:sldks-1",
    "слдкс-2": "saturn:system:sldks-2",
    "бкд-пк-rf.2": "saturn:device:bkd-pk-rf-2",
}
COMPONENTS = {"усл-а": "usl-a", "усл-п": "usl-p"}


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Document:
    entity: str
    filename: str
    sha256: str
    pages: int
    url: str = ""
    edition: str | None = None
    dossier_locator: str = ""

    @property
    def source_document_id(self):
        return sha(json_bytes([self.entity, self.dossier_locator, self.url]))

    @property
    def source_revision_id(self):
        return sha(json_bytes([self.source_document_id, self.edition, self.sha256]))


@dataclass(frozen=True)
class SourceBundle:
    site_commit_sha: str
    source_inventory_manifest_id: str
    pdf_revisions: tuple[Document, ...]
    parser_version: str = PARSER
    extraction_policy_version: str = EXTRACTION
    evidence_policy_revision: str = "experimental/candidate-only/1"
    entity_identity_map_revision: str = "experimental/explicit-labels/1"
    attribute_dictionary_revision: str = "experimental/source-labels/1"
    relation_dictionary_revision: str | None = None
    publication_state: str = "draft"

    @property
    def site_snapshot_id(self):
        return f"saturn:{self.site_commit_sha}"

    @property
    def bundle_id(self):
        return sha(json_bytes(self.manifest_fields()))


    def manifest_fields(self):
        return dict(schema=SCHEMA, site_snapshot_id=self.site_snapshot_id,
                    site_route_manifest_id=self.source_inventory_manifest_id, **asdict(self))


@dataclass(frozen=True)
class Locator:
    kind: str
    bbox: tuple[float, ...]
    block: int | None = None
    table: int | None = None
    row: int | None = None
    column: int | None = None
    row_bbox: tuple[float, ...] | None = None
    header: str | None = None
    header_evidence_id: str | None = None


@dataclass(frozen=True)
class EvidenceRef:
    bundle_id: str
    source_document_id: str
    source_revision_id: str
    pdf_bytes_sha256: str
    parser_version: str
    original_url: str
    edition: str | None
    physical_page: int
    locator: Locator
    quote: str
    quote_sha256: str
    state: str = "locator_verified"
    channel: str = "pdf"
    extraction_method: str = EXTRACTION

    @property
    def evidence_id(self):
        return sha(json_bytes(asdict(self)))


@dataclass(frozen=True)
class EvidenceCheck:
    physical_page: int
    reason: str
    bbox: tuple[float, ...]
    table: int | None = None
    state: str = "blocked"


@dataclass(frozen=True)
class Scope:
    subject_entity_id: str | None = None
    variant_id: str | None = None
    component_id: str | None = None


def scope_match(source, query):
    pairs = tuple(zip(asdict(source).values(), asdict(query).values()))
    if any(actual is not None and requested is not None and actual != requested
           for actual, requested in pairs):
        return "MISMATCH"
    if source.subject_entity_id is None or query.subject_entity_id is None:
        return "UNKNOWN"
    explicit_subject_variant = all(a == b and a is not None for a, b in pairs[:2])
    return "MATCH" if explicit_subject_variant and pairs[2][0] == pairs[2][1] else "UNKNOWN"


def explicit_scope(label):
    # A standalone source label can name a model and optional explicit variant
    # and component. Mentions inside prose or filenames confer no scope.
    match = re.fullmatch(
        r"(слдкс-[12]|бкд-пк-rf\.2)(?: (без компьютера|без персонального компьютера|общие характеристики))?"
        r"(?: (усл-[ап]))?", label.casefold())
    if not match:
        return Scope()
    entity, variant, component = match.groups()
    return Scope(MODELS[entity], ("general" if variant == "общие характеристики" else "no-pc")
                 if variant else None, COMPONENTS.get(component))


@dataclass(frozen=True)
class SourceAssertionCandidate:
    evidence_id: str
    source_literal: str
    scope: Scope
    source_attribute_label: str | None = None
    context_evidence_ids: tuple[str, ...] = ()
    reason: str = "semantics_and_qualifiers_require_review"
    qualifiers_state: str = "requires_review"


@dataclass(frozen=True)
class Ledger:
    assertions: tuple[SourceAssertionCandidate, ...]

    def applicable(self, query):
        return tuple(record for record in self.assertions if scope_match(record.scope, query) == "MATCH")

    def shortlist(self, query, limit=12):
        if not 0 <= limit <= 12:
            raise ValueError("Shortlist limit must be between 0 and 12")
        return self.applicable(query)[:limit]


def approved_bundle():
    raw = discovery.MANIFEST.read_bytes()
    if sha(raw) != APPROVED_SITE_MANIFEST_SHA256:
        raise ValueError("Unapproved site manifest")
    manifest = json.loads(raw)
    if manifest["commit"] != discovery.COMMIT:
        raise ValueError("Site manifest commit mismatch")
    pins = (("bkd", "bkd.pdf", BKD_PIN, 65), ("sld", "sldks.pdf", SLD_PIN, 83))
    documents = []
    for key, filename, digest, pages in pins:
        source = next(s for s in manifest["sources"] if s["key"] == key)
        locator = f"documents[{PRIMARY[key]}]"
        metadata = next(d for d in manifest["documents"]
                        if d["entity"] == source["entity"] and d["path"] == source["path"]
                        and d["locator"] == locator)
        documents.append(Document(source["entity"], filename, digest, pages,
                                  metadata["original_url"], metadata["revision"], locator))
    return SourceBundle(discovery.COMMIT, sha(raw), tuple(documents))


def overlaps(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def sound_table(table, grid, tables):
    if not safe_grid(grid) or len(grid) != len(table.rows):
        return False
    if any(other is not table and overlaps(table.bbox, other.bbox) for other in tables):
        return False
    for row, line in zip(table.rows, grid):
        if len(row.cells) != len(line) or any("\ufffd" in text for text in line):
            return False
        for box in row.cells:
            if box is None or not all(math.isfinite(value) for value in box):
                return False
            x0, top, x1, bottom = box
            if not (table.bbox[0] <= x0 < x1 <= table.bbox[2]
                    and table.bbox[1] <= top < bottom <= table.bbox[3]):
                return False
    # The only supported extraction geometry is a monotonically ordered rectilinear grid.
    matrix = [row.cells for row in table.rows]
    if any(left[2] > right[0] for row in matrix for left, right in zip(row, row[1:])):
        return False
    return all(upper[3] <= lower[1] for column in zip(*matrix)
               for upper, lower in zip(column, column[1:]))


def read_document(doc, root, bundle_id, *, parser_version=PARSER):
    if parser_version != PARSER:
        raise ValueError("Parser revision mismatch")
    with (root / doc.filename).open("rb") as stream:
        raw = read_bounded(stream)
    if sha(raw) != doc.sha256:
        raise ValueError("PDF SHA-256 mismatch")
    refs, issues = [], []

    def add(page, locator, text):
        ref = EvidenceRef(bundle_id, doc.source_document_id, doc.source_revision_id, doc.sha256,
                          parser_version, doc.url, doc.edition, page, locator, text, sha(text.encode()))
        refs.append(ref)
        return ref.evidence_id

    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if len(pdf.pages) != doc.pages:
            raise ValueError("Physical page count mismatch")
        for page in pdf.pages:
            number = page.page_number
            blocks, tables, exclusions = page_regions(page)
            for index, block in enumerate(blocks, 1):
                add(number, Locator("text_block", tuple(block["bbox"]), block=index), block["text"])
            for index, table in enumerate(tables, 1):
                grid = table.extract()
                if not sound_table(table, grid, tables):
                    issues.append(EvidenceCheck(number, "ambiguous_table_grid", tuple(table.bbox), index))
                    continue
                headers = tuple(cell.casefold().strip() for cell in grid[0])
                associated = headers in HEADERS
                if not associated:
                    issues.append(EvidenceCheck(number, "header_association_unverified", tuple(table.bbox), index))
                header_ids = []
                for row_index, (row, texts) in enumerate(zip(table.rows, grid), 1):
                    columns = tuple(zip(*row.cells))
                    row_bbox = (min(columns[0]), min(columns[1]), max(columns[2]), max(columns[3]))
                    for col, (bounds, literal) in enumerate(zip(row.cells, texts), 1):
                        has_header = associated and row_index > 1
                        ref_id = add(number, Locator(
                            "table_cell", tuple(bounds), table=index, row=row_index, column=col, row_bbox=row_bbox,
                            header=grid[0][col - 1] if has_header else None,
                            header_evidence_id=header_ids[col - 1] if has_header else None), literal)
                        if row_index == 1:
                            header_ids.append(ref_id)
            issues.extend(EvidenceCheck(number, region["reason"], tuple(region["bbox"]))
                          for region in exclusions if region["reason"] != "table requires row and cell proof")
            if not blocks and not tables and not exclusions:
                issues.append(EvidenceCheck(number, "no_localizable_text", tuple(page.bbox)))
            page.close()
    return tuple(refs), tuple(issues)


def candidates(refs):
    cells = {(r.source_revision_id, r.physical_page, r.locator.table, r.locator.row, r.locator.column): r
             for r in refs if r.locator.kind == "table_cell"}
    result = []
    for ref in refs:
        loc = ref.locator
        scope, attribute, context = Scope(), None, ()
        if loc.kind == "table_cell" and loc.header and loc.header.casefold().strip() == "значение":
            key = (ref.source_revision_id, ref.physical_page, loc.table, loc.row)
            label = cells[(*key, loc.column - 1)]
            attribute = label.quote
            context = (label.evidence_id, loc.header_evidence_id)
            if loc.column == 3:
                scope_cell = cells[(*key, 1)]
                scope = explicit_scope(scope_cell.quote)
                context += (scope_cell.evidence_id, scope_cell.locator.header_evidence_id)
        result.append(SourceAssertionCandidate(ref.evidence_id, ref.quote, scope, attribute, context))
    return Ledger(tuple(result))


def build(root, output):
    bundle = approved_bundle()
    receipts, refs, checks = [], [], []
    for doc in bundle.pdf_revisions:
        try:
            doc_refs, doc_checks = read_document(doc, root, bundle.bundle_id, parser_version=bundle.parser_version)
        except (OSError, ValueError, PDFException) as exc:
            reason = "source_unavailable" if isinstance(exc, OSError) else "source_integrity_error"
            receipts.append(dict(document=doc.filename, state="blocked", reason=reason, detail=str(exc)))
            continue
        receipts.append(dict(document=doc.filename, state="bytes_verified", sha256=doc.sha256,
                             physical_pages=doc.pages))
        refs.extend(doc_refs)
        checks.extend(dict(document=doc.filename, **asdict(check)) for check in doc_checks)
    ledger = candidates(refs)
    metrics = dict(bytes_verified=sum(r["state"] == "bytes_verified" for r in receipts),
                   exact_locator_proof=len(refs),
                   scoped_assertion_candidates=sum(a.scope.variant_id is not None for a in ledger.assertions),
                   scope_unknown=sum(a.scope.variant_id is None for a in ledger.assertions),
                   needs_human_review=len(ledger.assertions), published_verified_claims=0)
    manifest = json_bytes(dict(bundle_id=bundle.bundle_id, **bundle.manifest_fields()))
    diagnostic = json_bytes(dict(
        schema=SCHEMA, bundle_id=bundle.bundle_id, receipts=receipts,
        evidence=[dict(evidence_id=ref.evidence_id, **asdict(ref)) for ref in refs],
        assertions=[asdict(a) for a in ledger.assertions], checks=checks, metrics=metrics,
        coverage_state="partial_index"))
    counts = Counter(c["reason"] for c in checks)
    report = ["# PDF Evidence Ledger", "", f"- Bundle ID `{bundle.bundle_id}`",
              "- Coverage state `partial_index`", "",
              *(f"- `{name}` = {value}" for name, value in metrics.items()), "",
              "## Source status", "", *(f"- `{r['document']}` — {r['state']}"
                + (f" ({r['reason']})" if "reason" in r else f", {r['physical_pages']} pages, `{r['sha256']}`")
                for r in receipts), "", "## Blocked region counts", "",
              *(f"- {reason} = {count}" for reason, count in sorted(counts.items())), ""]
    output.mkdir(mode=0o700)
    files = {"manifest.json": manifest, "diagnostics.json": diagnostic,
             "report.md": "\n".join(report).encode()}
    for name, content in files.items():
        (output / name).write_bytes(content)
    (output / "SHA256SUMS").write_text("".join(f"{sha(data)}  {name}\n" for name, data in files.items()))
    return 0 if all(r["state"] == "bytes_verified" for r in receipts) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory for local reports")
    args = parser.parse_args()
    return build(args.pdf_dir, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
