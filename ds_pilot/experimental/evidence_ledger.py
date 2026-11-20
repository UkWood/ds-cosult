"""Local PDF evidence inventory. No runtime or publication entry points."""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
import hashlib
import io
import json
import math
from pathlib import Path
import re

import pdfminer
import pdfplumber
from pdfminer.pdfexceptions import PDFException

from .evidence_trace import build_trace, counts
from .. import discovery
from ..pdf_sources import BKD_PIN, PRIMARY, SLD_PIN, page_regions, read_bounded, safe_grid

SCHEMA = "experimental/ds-int-01a/2"
EXTRACTION = "exact-regions/2"
APPROVED_SITE_MANIFEST_SHA256 = "78517ce8afca16bd4842df15f33685053261d3a49f5f5d7da6a395724e7b4ad6"
PARSER = f"pdfplumber/{pdfplumber.__version__}+pdfminer.six/{pdfminer.__version__}"
HEADERS = {
    ("параметр", "значение"),
    ("обозначение блока", "назначение"),
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
    title: str = ""

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
    evidence_policy_revision: str = "experimental/candidate-only/2"
    entity_identity_map_revision: str = "experimental/contextual-labels/2"
    attribute_dictionary_revision: str = "experimental/source-labels/2"
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
    context = source if isinstance(source, ScopeContext) else None
    if context:
        if any(field.status == "conflicting" for field in (context.entity, context.variant, context.component)):
            return "UNKNOWN"
        source = context.scope
    pairs = ((source.subject_entity_id, query.subject_entity_id),
             (source.variant_id, query.variant_id), (source.component_id, query.component_id))
    if any(actual is not None and requested is not None and actual != requested
           for actual, requested in pairs):
        return "MISMATCH"
    if context and source.component_id is None and context.component.status != "not_applicable":
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
class ContextProof:
    source_document_id: str
    physical_page: int | None
    evidence_id: str | None
    relation: str
    rule: str
    literal: str
    literal_sha256: str


def proof(ref, relation, rule):
    return ContextProof(ref.source_document_id, ref.physical_page, ref.evidence_id,
                        relation, rule, ref.quote, ref.quote_sha256)


@dataclass(frozen=True)
class ScopeField:
    value: str | None = None
    status: str = "unknown"
    provenance: tuple[ContextProof, ...] = ()


@dataclass(frozen=True)
class ScopeContext:
    entity: ScopeField = ScopeField()
    variant: ScopeField = ScopeField()
    component: ScopeField = ScopeField()

    @property
    def scope(self):
        return Scope(self.entity.value, self.variant.value, self.component.value)


@dataclass(frozen=True)
class SourceAssertionCandidate:
    evidence_id: str
    source_literal: str
    scope: Scope
    source_attribute_label: str | None = None
    context_evidence_ids: tuple[str, ...] = ()
    reason: str = "semantics_and_qualifiers_require_review"
    qualifiers_state: str = "requires_review"
    kind: str = "attribute_value"
    attribute_evidence_id: str | None = None
    scope_context: ScopeContext | None = None


@dataclass(frozen=True)
class Ledger:
    assertions: tuple[SourceAssertionCandidate, ...]
    contexts: dict[str, ScopeContext] | None = None
    table_diagnostics: tuple[dict, ...] = ()
    row_diagnostics: tuple[dict, ...] = ()

    def applicable(self, query):
        return tuple(record for record in self.assertions if scope_match(record.scope_context or record.scope, query) == "MATCH")

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
                                  metadata["original_url"], metadata["revision"], locator, metadata["title"]))
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
                headers = tuple(normalized(cell) for cell in grid[0])
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


def normalized(text):
    return " ".join(text.casefold().replace("ё", "е").split())


CAPTION = re.compile(
    r"таблица (\d+)\s*[-–—.]\s*(?:основные )?технические характеристики "
    r"(?:(арм диспетчера) )?(слдкс-[12]|бкд-пк-rf\.2)"
    r"(?: \((без компьютера|без персонального компьютера|общие характеристики)\))?\.?")
SECTION = re.compile(
    r"(?:основные )?технические характеристики (слдкс-[12]|бкд-пк-rf\.2)"
    r" приведены в таблице (\d+)\.?")
CONTINUATION = re.compile(r"(?:продолжение таблицы|таблица) (\d+)(?:\s*[-–—]\s*продолжение)?\.?")


def declared_context(ref):
    text = normalized(ref.quote)
    match = CAPTION.fullmatch(text)
    if match:
        number, arm, model, variant = match.groups()
        origin = proof(ref, "table_caption", "numbered-specification-caption/1")
        component = ScopeField("dispatcher-arm", "explicit", (origin,)) if arm else ScopeField(
            status="not_applicable", provenance=(origin,))
        return number, ScopeContext(
            ScopeField(MODELS[model], "explicit", (origin,)),
            ScopeField("no-pc" if variant and variant.startswith("без ") else "general",
                       "explicit", (origin,)), component)
    match = SECTION.fullmatch(text)
    if match:
        model, number = match.groups()
        origin = proof(ref, "section_heading", "explicit-numbered-table-introduction/1")
        # The introduction names the model but does not describe the variant or component.
        return number, ScopeContext(entity=ScopeField(MODELS[model], "explicit", (origin,)))
    return None


def inherit(field, origin=None):
    return replace(field, status="inherited_from_verified_context" if field.value else field.status,
                   provenance=field.provenance + ((origin,) if origin and field.provenance else ()))


def reconcile(parent, child):
    if parent.status == "conflicting":
        return parent
    if child.value is None:
        if parent.status == "unknown" and child.status == "not_applicable":
            return child
        return parent
    origins = (*parent.provenance, *child.provenance)
    if parent.value is not None and parent.value != child.value:
        return ScopeField(status="conflicting", provenance=origins)
    return replace(child, provenance=origins)


def row_scope(ref, scope):
    origin = proof(ref, "row_label", "explicit-same-row-scope/1")
    def field(value):
        return ScopeField(value, "explicit", (origin,)) if value else ScopeField()
    component = field(scope.component_id)
    if scope.subject_entity_id and scope.variant_id and not scope.component_id:
        component = ScopeField(status="not_applicable", provenance=(origin,))
    return ScopeContext(field(scope.subject_entity_id), field(scope.variant_id), component)


def table_contexts(refs, blocked):
    tables, blocks = defaultdict(list), defaultdict(list)
    for ref in refs:
        key = (ref.source_revision_id, ref.physical_page)
        if ref.locator.kind == "table_cell":
            tables[(*key, ref.locator.table)].append(ref)
        else:
            blocks[key].append(ref)
    # All ruled grids (even unsupported ones) are barriers to caption association.
    edges = defaultdict(dict)
    bounds = {}
    for key, cells in tables.items():
        boxes = [r.locator.bbox for r in cells]
        box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
               max(b[2] for b in boxes), max(b[3] for b in boxes))
        edges[key[:2]][key[2]] = box
        bounds[key] = box
    exclusions = defaultdict(list)
    for revision, check in blocked:
        if check.reason in {"ambiguous line", "image", "layout limit exceeded", "rotated glyph"}:
            exclusions[(revision, check.physical_page)].append(check.bbox)
        if check.reason == "ambiguous_table_grid":
            edges[(revision, check.physical_page)][check.table] = check.bbox

    def caption_zone(ref, box):
        x0, top, x1, _ = box
        left, _, right, bottom = ref.locator.bbox
        return 0 <= top - bottom <= 36 and min(x1, right) > max(x0, left)

    resolved, diagnostics = {}, []
    for key in sorted(tables, key=lambda k: (k[0], k[1], bounds[k][1], k[2])):
        revision, page, table = key
        x0, top, x1, _ = bounds[key]
        page_key = key[:2]
        above = [ref for ref in blocks[page_key]
                 if caption_zone(ref, bounds[key])
                 and sum(caption_zone(ref, box) for box in edges[page_key].values()) == 1
                 and not any(overlaps((x0, ref.locator.bbox[3], x1, top), box)
                             for box in exclusions[page_key])
                 and not any(
                     n != table and box[3] > ref.locator.bbox[3] and box[1] < top
                     and min(x1, box[2]) > max(x0, box[0])
                     for n, box in edges[page_key].items())]
        declarations = [(ref, declared_context(ref)) for ref in above]
        explicit = [(ref, item) for ref, item in declarations if item]
        continuations = [(ref, match[1]) for ref in above
                         if (match := CONTINUATION.fullmatch(normalized(ref.quote)))
                         and ("продолжение" in normalized(ref.quote))]
        headers = tuple(normalized(ref.quote) for ref in sorted(tables[key], key=lambda r: r.locator.column)
                        if ref.locator.row == 1)
        scope, number, reason = ScopeContext(), None, "table_context_unresolved"
        if len(above) == 1 and len(explicit) == 1:
            number, scope = explicit[0][1]
            reason = "source_context_linked"
        elif len(above) == len(explicit) == 2:
            _, (first_number, first_scope) = min(explicit, key=lambda item: item[0].locator.bbox[1])
            _, (number, scope) = max(explicit, key=lambda item: item[0].locator.bbox[1])
            if (first_number == number and first_scope.entity.value == scope.entity.value
                    and first_scope.entity.provenance[0].relation == "section_heading"
                    and scope.entity.provenance[0].relation == "table_caption"):
                scope = replace(scope, entity=reconcile(first_scope.entity, scope.entity))
                reason = "source_context_linked"
            else:
                origins = tuple(item[1][1].entity.provenance[0] for item in explicit)
                scope = ScopeContext(entity=ScopeField(status="conflicting", provenance=origins))
                reason = "competing_table_context"
        elif len(above) == 1 and len(continuations) == 1:
            marker, number = continuations[0]
            previous = [(old, old_scope) for old, (old_number, old_scope, old_headers, old_reason) in resolved.items()
                        if old[:2] == (revision, page - 1) and old_number == number and old_headers == headers
                        and old_reason in {"source_context_linked", "continuation_linked"}]
            reason = "continuation_unverified"
            if len(previous) == 1 and headers in HEADERS:
                old, old_scope = previous[0]
                last = max(edges[old[:2]], key=lambda n: edges[old[:2]][n][3])
                first = min(edges[page_key], key=lambda n: edges[page_key][n][1])
                if old[2] == last and table == first:
                    origin = proof(marker, "continuation", "adjacent-numbered-repeat-header/1")
                    scope = ScopeContext(*(inherit(field, origin) for field in
                                           (old_scope.entity, old_scope.variant, old_scope.component)))
                    reason = "continuation_linked"
        elif explicit or continuations:
            reason = "competing_table_context"
            origins = tuple(proof(ref, "table_caption" if CAPTION.fullmatch(normalized(ref.quote))
                                  else "section_heading" if item else "continuation",
                                  "competing-context/1")
                            for ref, item in declarations if item or "продолжение" in normalized(ref.quote))
            scope = ScopeContext(*(ScopeField(status="conflicting", provenance=origins) for _ in range(3)))
        resolved[key] = (number, scope, headers, reason)
        diagnostics.append(dict(source_revision_id=revision, physical_page=page, table=table,
                                printed_table_number=number, reason_code=reason,
                                recognized_headers=headers in HEADERS, column_count=len(headers)))
    return tables, resolved, tuple(diagnostics)


def candidates(refs, blocked=()):
    tables, resolved, diagnostics = table_contexts(refs, blocked)
    contexts = {ref.evidence_id: ScopeContext() for ref in refs}
    assertions = []
    row_issues = []
    for key, table in tables.items():
        _, parent, headers, _ = resolved[key]
        rows = defaultdict(dict)
        for ref in table:
            rows[ref.locator.row][ref.locator.column] = ref
        if headers not in HEADERS:
            continue
        for row_number, cells in sorted(rows.items()):
            if row_number == 1 or set(cells) != set(range(1, len(headers) + 1)):
                continue
            header_cells = rows[1]
            aligned = all(cells[col].locator.header_evidence_id == header_cells[col].evidence_id
                          and cells[col].locator.bbox[::2] == header_cells[col].locator.bbox[::2]
                          for col in cells)
            row_heights = {cell.locator.bbox[1::2] for cell in cells.values()}
            if not aligned or len(row_heights) != 1:
                row_issues.append(dict(source_revision_id=key[0], physical_page=key[1],
                                       table=key[2], row=row_number,
                                       reason_code="row_header_geometry_unresolved"))
                continue
            label, value = cells[len(headers) - 1], cells[len(headers)]
            component_table = headers == ("обозначение блока", "назначение")
            context = ScopeContext(*(inherit(field) for field in (parent.entity, parent.variant, parent.component)))
            row_ref = cells[1]
            explicit = (Scope(component_id=COMPONENTS.get(normalized(row_ref.quote))) if component_table
                        else explicit_scope(row_ref.quote) if len(headers) == 3 else Scope())
            local = row_scope(row_ref, explicit)
            context = ScopeContext(*(reconcile(a, b) for a, b in (
                (context.entity, local.entity), (context.variant, local.variant),
                (context.component, local.component))))
            # Mentions in the pair are not bindings. A competing model or a
            # narrower unbound variant defeats the inherited context.
            for ref in (label, value):
                text = normalized(ref.quote)
                if context.entity.value and any(
                    model != context.entity.value and re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text)
                    for name, model in MODELS.items()
                ):
                    context = replace(context, entity=ScopeField(
                        status="conflicting", provenance=(*context.entity.provenance,
                            proof(ref, "row_label", "competing-model-mention/1"))))
                if context.variant.value == "general" and re.search(r"без (?:персонального )?компьютера", text):
                    context = replace(context, variant=ScopeField(
                        status="conflicting", provenance=(*context.variant.provenance,
                            proof(ref, "row_label", "unbound-variant-mention/1"))))
                if not component_table and context.component.status == "not_applicable" and any(
                    re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text) for name in COMPONENTS
                ):
                    context = replace(context, component=ScopeField(
                        status="conflicting", provenance=(*context.component.provenance,
                            proof(ref, "row_label", "unbound-component-mention/1"))))
            if component_table and not explicit.component_id:
                context = replace(context, component=ScopeField())
            for ref in cells.values():
                contexts[ref.evidence_id] = context
            origins = (entry.evidence_id for field in (context.entity, context.variant, context.component)
                       for entry in field.provenance if entry.evidence_id)
            context_ids = tuple(dict.fromkeys((label.evidence_id, label.locator.header_evidence_id,
                                               value.locator.header_evidence_id, *origins)))
            assertions.append(SourceAssertionCandidate(
                value.evidence_id, value.quote, context.scope, label.quote, context_ids,
                kind="component_description" if component_table else "attribute_value",
                attribute_evidence_id=label.evidence_id, scope_context=context))
    return Ledger(tuple(assertions), contexts, diagnostics, tuple(row_issues))


def build(root, output):
    bundle = approved_bundle()
    receipts, refs, checks, blocked = [], [], [], []
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
        blocked.extend((doc.source_revision_id, check) for check in doc_checks)
    ledger = candidates(refs, blocked)
    control = build_trace(bundle.pdf_revisions, refs, ledger, checks, Scope, scope_match, normalized)
    table_reasons = Counter(table["reason_code"] for table in ledger.table_diagnostics)
    ref_kinds = Counter(ref.locator.kind for ref in refs)
    candidate_kinds = Counter(a.kind for a in ledger.assertions)
    metrics = dict(
        bytes_verified=sum(r["state"] == "bytes_verified" for r in receipts),
        evidence_refs_total=len(refs),
        text_block=ref_kinds["text_block"],
        table_cell=ref_kinds["table_cell"],
        attribute_value_candidates_total=candidate_kinds["attribute_value"],
        component_description_candidates_total=candidate_kinds["component_description"],
        recognized_two_column_tables=sum(t["recognized_headers"] and t["column_count"] == 2
                                         for t in ledger.table_diagnostics),
        context_provenance_coverage={
            name: {field: sum(getattr(context, field).value is not None for context in contexts)
                   for field in ("entity", "variant", "component")}
            for name, contexts in (
                ("evidence_refs", tuple(ledger.contexts.values())),
                ("candidates", tuple(a.scope_context for a in ledger.assertions)))},
        blocked_or_unresolved=dict(
            ambiguous_geometry=sum(c["reason"] == "ambiguous_table_grid" for c in checks),
            row_header_geometry_unresolved=len(ledger.row_diagnostics),
            continuation_unverified=table_reasons["continuation_unverified"],
            table_context_unresolved=table_reasons["table_context_unresolved"],
            competing_table_context=table_reasons["competing_table_context"],
            literal_footnote_markers=sum(bool(re.search(r"[*†‡⁎¹²³]", a.source_literal))
                                        for a in ledger.assertions),
            qualifiers_require_review=len(ledger.assertions)),
        published_verified_claims=0)
    for source_kind in ("evidence_ref_scope", "candidate_scope"):
        totals = Counter()
        for case in control:
            totals.update(case[source_kind])
        metrics[source_kind] = dict(totals) or counts(())
    manifest = json_bytes(dict(bundle_id=bundle.bundle_id, **bundle.manifest_fields()))
    diagnostic = json_bytes(dict(
        schema=SCHEMA, bundle_id=bundle.bundle_id, receipts=receipts,
        evidence=[dict(evidence_id=ref.evidence_id, scope_context=asdict(ledger.contexts[ref.evidence_id]),
                       **asdict(ref)) for ref in refs],
        assertions=[asdict(a) for a in ledger.assertions], checks=checks,
        tables=ledger.table_diagnostics, unresolved_rows=ledger.row_diagnostics, metrics=metrics,
        coverage_state="partial_index"))
    trace = json_bytes(dict(schema=SCHEMA, bundle_id=bundle.bundle_id,
                           coverage_state="partial_index", metrics=metrics, control_cases=control,
                           document_contexts=[dict(source_document_id=doc.source_document_id,
                               scope_context=asdict(ScopeContext(entity=ScopeField(
                                   doc.entity, "explicit", (ContextProof(
                                       doc.source_document_id, None, None, "document_title",
                                       "approved-manufacturer-dossier/1", doc.title,
                                       sha(doc.title.encode())),)))),
                               approved_manifest_id=bundle.source_inventory_manifest_id,
                               dossier_locator=doc.dossier_locator)
                               for doc in bundle.pdf_revisions if doc.title]))
    reasons = Counter(c["reason"] for c in checks)
    report = ["# PDF Evidence Ledger", "", f"- Bundle ID `{bundle.bundle_id}`",
              "- Coverage state `partial_index`", "",
              *(f"- `{name}` = {value}" for name, value in metrics.items()), "",
              "## Source status", "", *(f"- `{r['document']}` — {r['state']}"
                + (f" ({r['reason']})" if "reason" in r else f", {r['physical_pages']} pages, `{r['sha256']}`")
                for r in receipts), "", "## Blocked region counts", "",
              *(f"- {reason} = {count}" for reason, count in sorted(reasons.items())), ""]
    output.mkdir(mode=0o700)
    files = {"manifest.json": manifest, "diagnostics.json": diagnostic,
             "report.md": "\n".join(report).encode(), "context_trace.json": trace}
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
