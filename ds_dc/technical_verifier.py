"""Deterministic verification of mechanically supported technical table relations."""
from decimal import Decimal
import re
import subprocess

from .evidence_lab import nfc_text
from .structural_pdf import row_cells
from .technical_registry import VERSION

KINDS = {"quantity", "quantity_limit", "quantity_range", "symptom", "possible_cause", "conditional_action"}
FIELDS = {"id", "entity", "kind", "subject", "value", "unit", "comparator",
          "qualifier", "condition", "parts", "evidence"}
HEADER_ROLES = {
    "признаки проявления неисправности": "symptom", "symptom": "symptom",
    "возможные причины": "cause", "possible cause": "cause",
    "действия по устранению неисправности": "action", "corrective action": "action",
    "параметр": "subject", "parameter": "subject", "значение": "value", "value": "value",
    "единица": "unit", "unit": "unit", "условие": "condition", "condition": "condition",
    "квалификатор": "qualifier", "qualifier": "qualifier",
}
NUM = r"[+-]?[0-9]{1,18}(?:[.,][0-9]{1,18})?"
LIMITS = {"не более": "le", "не менее": "ge", "≤": "le", "≥": "ge", "<": "lt", ">": "gt"}


def word(text):
    return nfc_text(text).lower()


def numeric(text):
    if re.fullmatch(NUM, text):
        return "quantity", "eq", (Decimal(text.replace(",", ".")),)
    limit = re.fullmatch(r"(не более|не менее|≤|≥|<|>)\s*(" + NUM + ")", text)
    if limit:
        return "quantity_limit", LIMITS[limit[1]], (Decimal(limit[2].replace(",", ".")),)
    interval = re.fullmatch(r"(?:от (" + NUM + r") до (" + NUM + r")|(" + NUM + r")\s+[–—]\s+(" + NUM + r"))", text)
    if interval:
        a, b = tuple(Decimal(item.replace(",", ".")) for item in interval.groups() if item is not None)
        if a <= b:
            return "quantity_range", "range", (a, b)
    return None


def table_rows(page):
    for table_id, table in enumerate(page["tables"]):
        if not table["rows"] or any(cell is None for cell in table["rows"][0]):
            continue
        roles = [HEADER_ROLES.get(word(cell[1])) for cell in table["rows"][0]]
        known = [role for role in roles if role]
        if len(known) != len(set(known)):
            continue
        for row_id in range(1, len(table["rows"])):
            cells = row_cells(table, row_id)
            yield table_id, row_id, {role: cell for role, cell in zip(roles, cells, strict=True) if role}


def locator_valid(loc):
    return (isinstance(loc, dict) and {"role", "source", "page", "quote"} <= set(loc)
            and set(loc) <= {"role", "source", "page", "quote", "hint"}
            and all(isinstance(loc[key], str) and loc[key] for key in ("role", "source", "quote"))
            and type(loc["page"]) is int and loc["page"] >= 1
            and ("hint" not in loc or (isinstance(loc["hint"], dict)
                 and set(loc["hint"]) == {"table", "row", "column"}
                 and all(type(n) is int and n >= 0 for n in loc["hint"].values()))))


def claim_valid(item, registry):
    return (isinstance(item, dict) and set(item) == FIELDS
            and all(isinstance(item[k], str) for k in FIELDS - {"value", "parts", "evidence"})
            and item["id"] and item["subject"] and item["kind"] in KINDS
            and (isinstance(item["value"], list) and len(item["value"]) == 2
                 and all(isinstance(n, str) for n in item["value"])
                 if item["kind"] == "quantity_range" else isinstance(item["value"], str))
            and isinstance(item["parts"], list) and len(item["parts"]) <= 32
            and all(isinstance(p, str) and p in registry.parts for p in item["parts"])
            and len(set(item["parts"])) == len(item["parts"])
            and isinstance(item["evidence"], list) and 1 <= len(item["evidence"]) <= 8
            and all(locator_valid(loc) for loc in item["evidence"])
            and len({loc["role"] for loc in item["evidence"]}) == len(item["evidence"]))


def relation(item, cells, roles):
    required = {
        "symptom": {"symptom"}, "possible_cause": {"symptom", "cause"},
        "conditional_action": {"cause", "action"},
    }.get(item["kind"])
    if required is not None:
        if roles != required or not {"symptom", "cause", "action"} <= cells.keys():
            return "semantic_pending", "unproved_troubleshooting_relation"
        target = {"symptom": "symptom", "possible_cause": "cause", "conditional_action": "action"}[item["kind"]]
        prerequisite = {"possible_cause": "symptom", "conditional_action": "cause"}.get(item["kind"])
        expected_condition = word(cells[prerequisite]["text"]) if prerequisite else ""
        qualifier = {"symptom": "observed", "possible_cause": "possible", "conditional_action": "conditional"}[item["kind"]]
        if (word(item["subject"]) == word(cells[target]["text"]) and word(item["condition"]) == expected_condition
                and item["qualifier"] == qualifier and item["value"] == item["unit"] == item["comparator"] == ""):
            return "supported", "verified_table_relation"
        return "semantic_pending", "unproved_modality_subject_or_condition"

    expected_roles = {"subject", "value", "unit"}
    expected_roles |= {k for k in ("condition", "qualifier") if k in cells and cells[k] and cells[k]["text"].strip()}
    if roles != expected_roles or any(k in cells and cells[k] is None for k in ("condition", "qualifier")):
        return "semantic_pending", "unproved_quantity_context"
    if (word(item["subject"]) != word(cells["subject"]["text"]) or item["unit"] != nfc_text(cells["unit"]["text"])
            or any(word(item[k]) != (word(cells[k]["text"]) if k in expected_roles else "")
                   for k in ("condition", "qualifier"))):
        return "semantic_pending", "unproved_quantity_context"
    observed = numeric(nfc_text(cells["value"]["text"]))
    proposed = item["value"] if isinstance(item["value"], list) else [item["value"]]
    if not observed or not all(re.fullmatch(NUM, value) for value in proposed):
        return "semantic_pending", "numeric_format_unproved"
    values = tuple(Decimal(value.replace(",", ".")) for value in proposed)
    if observed == (item["kind"], item["comparator"], values):
        return "supported", "verified_quantity"
    if observed[:2] == (item["kind"], item["comparator"]) and len(observed[2]) == len(values):
        return "contradicted", "different_numeric_value"
    return "semantic_pending", "unproved_quantity_modality"


def inspect_claim(item, registry, extract):
    result = dict(id=item.get("id") if isinstance(item, dict) else None, schema_valid=False,
                  source_identity_verified=False, applicability_verified=False, evidence_verified=False,
                  relation_verified=False, technical_status="invalid", covered_parts=[],
                  reason_codes=[], locators=[])

    def finish(status, code):
        result.update(technical_status=status, reason_codes=[code])
        return result

    if not claim_valid(item, registry):
        return finish("invalid", "invalid_claim_schema")
    result["schema_valid"] = True
    entity = registry.entities.get(item["entity"])
    locations = item["evidence"]
    sources = [registry.sources.get(loc["source"]) for loc in locations]
    if not entity or any(source is None or loc["page"] > source.pages for loc, source in zip(locations, sources)):
        return finish("invalid", "foreign_entity_or_source_or_page")
    # Registry lookup alone does not verify the source bytes.
    if any((s.canonical_entity, s.generation) != (entity.canonical_id, entity.generation)
           or not s.applicability for s in sources):
        return finish("semantic_pending", "applicability_unproved")
    result["applicability_verified"] = True
    if any(s.kind != "pdf" for s in sources) or len({(loc["source"], loc["page"]) for loc in locations}) != 1:
        return finish("semantic_pending", "cross_source_or_non_pdf_relation_unproved")
    try:
        page = extract(sources[0], locations[0]["page"])
    except (OSError, ValueError, subprocess.SubprocessError):
        return finish("semantic_pending", "evidence_unavailable")
    result["source_identity_verified"] = True

    # Resolve each quote within a role's physical cell. Then intersect candidate table rows.
    row_sets = []
    matches = {}
    for loc in locations:
        candidates = set()
        for table_id, row_id, cells in table_rows(page):
            cell = cells.get(loc["role"])
            if cell is None or nfc_text(cell["text"]) != nfc_text(loc["quote"]):
                continue
            coordinate = {"table": table_id, "row": cell["row"], "column": cell["column"]}
            if "hint" in loc and loc["hint"] != coordinate:
                continue
            candidates.add((table_id, row_id))
            matches[(table_id, row_id)] = cells
        if not candidates:
            return finish("semantic_pending", "quote_or_structure_unproved")
        row_sets.append(candidates)
    result["evidence_verified"] = True
    common = set.intersection(*row_sets)
    if not common:
        return finish("semantic_pending", "crossed_rows_or_tables")
    roles = {loc["role"] for loc in locations}
    # A merged symptom can have one physical identity across multiple body rows.
    signatures = {tuple((table_id, matches[(table_id, row_id)][loc["role"]]["row"],
                         matches[(table_id, row_id)][loc["role"]]["column"]) for loc in locations)
                  for table_id, row_id in common}
    if len(signatures) != 1 or (item["kind"] != "symptom" and len(common) != 1):
        return finish("semantic_pending", "ambiguous_structural_relation")
    table_id, row_id = min(common)
    cells = matches[(table_id, row_id)]
    if any(cells[role]["row"] != row_id for role in roles & {"cause", "action", "value"}):
        return finish("semantic_pending", "merged_value_or_action_unproved")
    result["locators"] = [{"source": loc["source"], "doc_id": sources[0].doc_id, "sha256": sources[0].sha256,
                           "revision": sources[0].revision, "page": loc["page"], "table": table_id,
                           **{k: cells[loc["role"]][k] for k in ("row", "column", "bbox")}}
                          for loc in locations]
    status, code = relation(item, cells, roles)
    result["relation_verified"] = status in {"supported", "contradicted"}
    return finish(status, code)


def verify(candidate, registry, extract, *, reviewed_parts=None):
    required = {"version", "request_id", "wire_identity", "claims", "answer_claim_ids", "unresolved"}
    if (not isinstance(candidate, dict) or set(candidate) != required
            or candidate["version"] != VERSION or candidate["request_id"] != registry.request_id
            or candidate["wire_identity"] != registry.wire_identity
            or not all(isinstance(candidate[k], list) and len(candidate[k]) <= 32
                       for k in ("claims", "answer_claim_ids", "unresolved"))
            or not all(isinstance(x, str) for key in ("answer_claim_ids", "unresolved") for x in candidate[key])):
        return {"status": "invalid_contract", "claims": [], "confirmed_claim_ids": []}
    ids = [item.get("id") for item in candidate["claims"] if isinstance(item, dict) and isinstance(item.get("id"), str)]
    if (len(ids) != len(set(ids)) or not set(candidate["answer_claim_ids"]) <= set(ids)
            or not set(candidate["unresolved"]) <= registry.parts.keys()):
        return {"status": "invalid_contract", "claims": [], "confirmed_claim_ids": []}
    results = [inspect_claim(item, registry, extract) for item in candidate["claims"]]
    confirmed = []
    covered = set()
    for item, result in zip(candidate["claims"], results):
        if result["technical_status"] == "supported" and item["id"] in candidate["answer_claim_ids"]:
            confirmed.append(item["id"])
            proven = set((reviewed_parts or {}).get(item["id"], ())) & set(item["parts"])
            result["covered_parts"] = sorted(proven)
            covered |= proven
    remaining = set(registry.parts) - covered
    return {"status": "shadow_only", "claims": results, "confirmed_claim_ids": confirmed,
            "coverage": "semantic_pending" if remaining or covered.intersection(candidate["unresolved"]) else "reviewed",
            "unresolved_parts": sorted(remaining | set(candidate["unresolved"]))}
