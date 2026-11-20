"""Explicit R0 control queries for offline, human-reviewed diagnostics."""
from collections import Counter
from dataclasses import asdict


SLD = "saturn:system:sldks-1"
BKD = "saturn:device:bkd-pk-rf-2"
CONTROL_QUERIES = (
    ("N09", "sldks.pdf", (7, 34), ("saturn:system:sldks-2", "general"), ("напряжен", "питан")),
    ("Q15/general", "sldks.pdf", (7, 34), (SLD, "general"), ("частот",)),
    ("Q15/no-pc", "sldks.pdf", (7, 34), (SLD, "no-pc"), ("частот",)),
    ("Q21", "sldks.pdf", (34, 35), (SLD, "no-pc"), ("ибп", "режим", "непрерыв")),
    ("Q22", "sldks.pdf", (25,), (SLD, "general", "dispatcher-arm"), ("памят", "озу", "диск")),
    ("Q24/usl-a", "sldks.pdf", (15,), (SLD, "general", "usl-a"), ("усл-а", "усл-п")),
    ("Q24/usl-p", "sldks.pdf", (15,), (SLD, "general", "usl-p"), ("усл-а", "усл-п")),
    ("N10", "bkd.pdf", (4,), (BKD, "general"), ("масс",)),
    ("N11", "sldks.pdf", (7,), (SLD, "general"), ("лифт",)),
    ("Q11", "sldks.pdf", (60,), (SLD, "general"), ("link",)),
)


def counts(decisions):
    totals = Counter(decisions)
    return {state: totals[state] for state in ("MATCH", "MISMATCH", "UNKNOWN")}


def build_trace(documents, refs, ledger, checks, make_scope, decide, normalize):
    by_id = {ref.evidence_id: ref for ref in refs}
    documents = {doc.filename: doc for doc in documents}
    cases = []
    for case, filename, pages, scope_args, hints in CONTROL_QUERIES:
        query = make_scope(*scope_args)
        doc = documents.get(filename)
        regions = [ref for ref in refs if doc and ref.source_revision_id == doc.source_revision_id
                   and ref.physical_page in pages]
        region_ids = {ref.evidence_id for ref in regions}
        # Hints select records for manual review only. They never establish a
        # claim, grant scope, filter the inventory or determine corpus absence.
        assertions = [a for a in ledger.assertions if a.evidence_id in region_ids
                      and any(hint in normalize(a.source_attribute_label + " " + a.source_literal)
                              for hint in hints)]
        rows = [dict(asdict(a), physical_page=by_id[a.evidence_id].physical_page,
                     locator=asdict(by_id[a.evidence_id].locator), scope_decision=decide(a.scope_context, query))
                for a in assertions]
        decisions = counts(row["scope_decision"] for row in rows)
        reason = ("scope_match_requires_semantic_review" if decisions["MATCH"] else
                  "scope_unresolved" if decisions["UNKNOWN"] else
                  "explicit_scope_mismatch" if decisions["MISMATCH"] else
                  "no_structured_pair_for_review_hint")
        if not regions:
            reason = "no_exact_locator_on_control_pages"
        table_context = [table for table in ledger.table_diagnostics
                         if doc and table["source_revision_id"] == doc.source_revision_id
                         and table["physical_page"] in pages]
        unresolved_rows = [row for row in ledger.row_diagnostics
                           if doc and row["source_revision_id"] == doc.source_revision_id
                           and row["physical_page"] in pages]
        cases.append(dict(
            case=case, source_document_id=doc.source_document_id if doc else None,
            physical_pages=pages, query=asdict(query), label_hints=hints,
            reason_code=reason, evidence_ids=[ref.evidence_id for ref in regions],
            evidence_ref_scope=counts(decide(ledger.contexts[ref.evidence_id], query) for ref in regions),
            candidate_scope=decisions, candidates=rows, tables=table_context,
            unresolved_rows=unresolved_rows,
            blocked_regions=dict(Counter(check["reason"] for check in checks
                                        if check["document"] == filename and check["physical_page"] in pages))))
    return cases
