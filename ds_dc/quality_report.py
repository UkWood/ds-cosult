"""Owner-review derivatives of a native candidate and its deterministic assembly."""
from collections.abc import Mapping
import hashlib
import ipaddress
import json
import math
import re
import unicodedata
from urllib.parse import unquote, urlsplit

from .evidence_answer import PACKET_FIELDS, VERSION, strict_json
from .evidence_extract import FIELD, LINES, SITE_FIELDS
from .technical_registry import Source
from .technical_verifier import KINDS

_STATUS = {"invalid_contract", "full", "partial", "reference", "needs_support"}
_TECHNICAL = {"supported", "contradicted", "invalid", "semantic_pending"}
_REASON = frozenset("""
    invalid_claim_schema foreign_entity_or_source_or_page cross_source_or_non_pdf_relation_unproved
    evidence_unavailable quote_or_structure_unproved crossed_rows_or_tables ambiguous_structural_relation
    merged_value_or_action_unproved unproved_troubleshooting_relation verified_table_relation
    unproved_modality_subject_or_condition unproved_quantity_context numeric_format_unproved verified_quantity
    different_numeric_value unproved_quantity_modality applicability_unproved unproved_row_context_or_variant
    invalid_extract_schema foreign_entity_or_source extract_entity_mismatch invalid_site_location
    site_identity_mismatch invalid_pdf_location source_unavailable literal_or_fragment_boundary_unproved
    literal_fragment_verified missing_row_cell unresolved_column unresolved_table_context unproved_row_applicability
""".split())
_RUN_STATUS = frozenset("""
    completed invalid_candidate provider_unknown provider_overage provider_contract_drift incomplete_finish
    go_expired upload_rejected binding_unavailable wire_drift mock-only mock_only no_permit preflight
    offline live_not_run live_not_authorized invalid_contract permit_required permit_mismatch contract_unreviewed
    campaign_budget_exhausted dossier_drift ready_for_offline_acceptance
""".split())
_PROVIDER_REASON = _RUN_STATUS | frozenset("""
    connect_timeout read_timeout write_timeout pool_timeout network_error protocol_error response_encoding_error
    transport_error http_error response_too_large invalid_json expected_object id_format object_mismatch
    purpose_mismatch filename_mismatch bytes_mismatch created_at_future expires_at_elapsed ttl_mismatch
    id_collision usage_missing_or_invalid incomplete_usage invalid_reasoning_usage
""".split()) | {f"{field}_{failure}" for field in ("id", "object", "purpose", "filename", "bytes", "created_at",
                                                    "expires_at") for failure in ("missing", "type")}
_OPTION_SETS = {
    "request_mode": {"mock_native", "preflight", "direct_native", "live_native"},
    "provider_model": {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"},
    "model": {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"},
    "reasoning_effort": {"high"}, "thinking": {"enabled"}, "response_format": {"json_object"},
}
_HASHES = {
    "commit": 40, "site_commit": 40, "corpus_sha256": 64, "manifest_sha256": 64,
    "logical_wire_sha256": 64, "logical_payload_sha256": 64, "actual_payload_sha256": 64,
    "source_registry_sha256": 64,
}
_NUMBERS = {
    "timing_ms": {"upload", "chat", "local_verification", "total"},
    "tokens": {"prompt", "hit", "miss", "completion", "reasoning", "total"},
    "cost_micro_usd": {"known", "held", "reserved"},
    "estimates_micro_usd": {"chat", "pdf", "total"},
}
_PUBLIC_URL = re.compile(r"https://(?:www\.)?mnppsaturn\.ru/[A-Za-z0-9_.%()/+~-]+"
                         r"|https://ukwood\.github\.io/Saturn-Main-Site/[A-Za-z0-9_.%()/+~-]*")
_URL_IN_ANSWER = re.compile(r"https://[^\s,]+")
_PRIVATE_TEXT = re.compile(
    r"(?i)(?:\b(?:authorization|bearer|api[ _-]?key|reasoning[_ -]?content|chain[ _-]of[ _-]thought|"
    r"raw[_ -]?http)\b|\b(?:ledger|permit|file[_ -]?id|hostname|token|secret)[ \t]*[:=]|\bfile-api-[A-Za-z0-9_-]+|"
    r"\b(?:sk|file|chatcmpl|sess|"
    r"upload|permit|ledger|req|ds)-[A-Za-z0-9_-]{6,}\b|\b(?:file|offline_slot)_[A-Za-z0-9_-]+\b|"
    r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b|\b(?:localhost|[A-Za-z0-9.-]+\.(?:local|internal|lan|"
    r"com|net|org|io|ru))\b|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|"
    r"(?:[A-Za-z]:[\\/]|\\\\|(?<![\w/])/(?!\s|$)|(?:~|\$HOME)[/\\])|"
    r"\b(?:https?|ftp|file|data|ssh)\s*:|\bwww\.|%PDF-|[A-Za-z0-9_+/=-]{48,})"
)
_IPV6_CANDIDATE = re.compile(r"(?<!\w)[0-9A-Fa-f:]{2,}(?!\w)")
_CLAIM_TEXT = ("subject", "value", "unit", "comparator", "qualifier", "condition")
_ROLES = {"subject", "value", "unit", "condition", "qualifier", "symptom", "cause", "action", "variant"}


def _mapping(value):
    return value if isinstance(value, Mapping) else {}


def _items(value, maximum=32):
    return value[:maximum] if isinstance(value, (list, tuple)) else []


def _enum(value, choices):
    return value if isinstance(value, str) and value in choices else None


def _match(value, pattern):
    return value if isinstance(value, str) and re.fullmatch(pattern, value) else None


def _number(value, maximum=10**12, *, whole=False):
    if type(value) is int and 0 <= value <= maximum:
        return value
    if not whole and type(value) is float and math.isfinite(value) and 0 <= value <= maximum:
        return value
    return None


def _compact(values):
    return {key: value for key, value in values.items() if value is not None}


def _is_ipv6(token):
    if token.count(":") < 2:
        return False
    try:
        return ipaddress.ip_address(token).version == 6
    except ValueError:
        return False


class _Export:
    def __init__(self, provenance, telemetry):
        self.removed = False
        fields = _items(telemetry.get("private_values"), 128)
        self.private = tuple(self.normalize(value) for value in fields if isinstance(value, str) and value)
        sources = _mapping(provenance.get("source_registry"))
        self.sources = {key: source for key, source in sources.items() if isinstance(source, Source)
                        and _match(key, r"S[1-9][0-9]{0,2}-[a-f0-9]{16}")}
        self.urls = {source.url for source in self.sources.values()}

    @staticmethod
    def normalize(value):
        # Check percent-encoded as well as literal identifiers without rewriting retained text.
        return unicodedata.normalize("NFKC", unquote(unquote(value))).casefold()

    def safe_text(self, value, limit=1000, urls=()):
        if not isinstance(value, str) or len(value) > limit:
            self.removed = True
            return None
        if urls:
            value_without_urls = _URL_IN_ANSWER.sub(lambda match: "" if match[0] in urls else match[0], value)
        else:
            value_without_urls = value
        normalized = self.normalize(value_without_urls)
        unmasked = self.normalize(value)
        if (_PRIVATE_TEXT.search(normalized) or any(secret in unmasked for secret in self.private)
                or any(unicodedata.category(char).startswith("C") and char not in "\n\t" for char in unmasked)
                or any(_is_ipv6(match[0]) for match in _IPV6_CANDIDATE.finditer(normalized))):
            self.removed = True
            return None
        return value

    def public_url(self, value):
        if (not isinstance(value, str) or len(value) > 512 or not _PUBLIC_URL.fullmatch(value)
                or value not in self.urls):
            self.removed = True
            return None
        target = urlsplit(value)
        path = unquote(unquote(target.path))
        if (any(part in {".", ".."} for part in path.split("/")) or "//" in path
                or any(secret in self.normalize(value) for secret in self.private)
                or any(char in path for char in "\\@?#<>\r\n\t")):
            self.removed = True
            return None
        return value

    def location(self, value, *, proposed=False):
        value = _mapping(value)
        result = {key: _number(value.get(key), 100000, whole=True) for key in ("table", "row", "column")}
        result["page"] = _number(value.get("page"), 500, whole=True) or None
        field = value.get("field")
        if isinstance(field, str) and ((match := FIELD.fullmatch(field)) and match[1] in SITE_FIELDS
                                       or LINES.fullmatch(field)):
            result["field"] = field
        bbox = value.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            coordinates = [_number(position, 100000) for position in bbox]
            if None not in coordinates:
                result["bbox"] = coordinates
        source_key = _match(value.get("source"), r"S[1-9][0-9]{0,2}-[a-f0-9]{16}")
        source = self.sources.get(source_key)
        if source:
            result["source"] = source_key
        elif "source" in value:
            self.removed = True
        url = source.url if source else value.get("url")
        if url is not None:
            result["url"] = self.public_url(url)
        if not proposed:
            for key, size in {"sha256": 64, "commit": 40, "blob": 40}.items():
                result[key] = _match(value.get(key), rf"[a-f0-9]{{{size}}}")
            result["doc_id"] = _match(value.get("doc_id"), r"[a-f0-9]{64}|saturn:[a-z]+:[a-z0-9/-]+")
            for key in ("revision", "applicability"):
                if value.get(key) is not None:
                    result[key] = self.safe_text(value[key], 200)
        return _compact(result)

    def diagnostic(self, row, extract):
        row = _mapping(row)
        status = {"technical_status": _enum(row.get("technical_status"), _TECHNICAL)}
        for key in ("applicability_verified", "source_identity_verified", "schema_valid", "evidence_verified",
                    "relation_verified", "source_verified", "action_present"):
            if type(row.get(key)) is bool:
                status[key] = row[key]
        status["reason_codes"] = [code for code in _items(row.get("reason_codes")) if _enum(code, _REASON)]
        status["covered_parts"] = _parts(row.get("covered_parts"))
        status["locations"] = [self.location(loc) for loc in _items(row.get("citations" if extract else "locators"))]
        if extract:
            status.update(evidence_status=_enum(row.get("evidence_status"), {"invalid", "semantic_pending", "source_verified"}),
                          context_status=_enum(row.get("context_status"), {"limited", "preserved", "unproved"}))
            if row.get("source_verified") is True and row.get("text") is not None:
                status["source_verified_text"] = self.safe_text(row["text"], 1200)
        else:
            status["context_issues"] = [code for code in _items(row.get("context_issues")) if _enum(code, _REASON)]
            if trace := _mapping(row.get("normalization")):
                status["normalization"] = _compact(dict(
                    input_form=_enum(trace.get("input_form"), {
                        "unverified", "unrecognized", "canonical", "condition_in_subject", "missing_observed_qualifier"}),
                    transformation=_enum(trace.get("transformation"), {
                        "none", "infer_qualifier", "relocate_value_and_infer_qualifier"}),
                    status=_enum(trace.get("status"), {"rejected", "canonical", "normalized"}),
                    reason=_enum(trace.get("reason"), _REASON),
                    verified_fields=[field for field in _items(trace.get("verified_fields")) if field in _CLAIM_TEXT],
                ))
            if reason := _enum(row.get("publication_reason"), {
                    "documented_conditional_action", "unproved_paired_cause",
                    "unproved_work_safety", "hazardous_or_unreviewed_action"}):
                status["publication_reason"] = reason
        return _compact(status)

    def native_row(self, row, local_id, *, extract):
        result = {"id": local_id, "parts": _parts(row.get("parts"))}
        # Entity tokens are request-salted in the real packet. The opaque token is not
        # needed in a single-entity review and cannot substitute for source provenance.
        if extract:
            result.update(self.location(row, proposed=True))
            result["quote"] = self.safe_text(row.get("quote"), 1200)
            result["conditions"] = [self.safe_text(text) for text in _items(row.get("conditions"), 8)]
            return _compact(result)
        result["kind"] = _enum(row.get("kind"), KINDS)
        for key in _CLAIM_TEXT:
            value = row.get(key)
            if key == "value" and isinstance(value, list) and len(value) == 2:
                result[key] = [self.safe_text(text) for text in value]
            elif value is not None:
                result[key] = self.safe_text(value)
        evidence = []
        for origin in _items(row.get("evidence"), 8):
            origin = _mapping(origin)
            location = self.location(origin, proposed=True)
            if "hint" in origin:
                location["hint"] = self.location(origin["hint"], proposed=True)
            evidence.append(_compact(dict(location, role=_enum(origin.get("role"), _ROLES),
                                          quote=self.safe_text(origin.get("quote"), 1200))))
        result["evidence"] = evidence
        return _compact(result)


def _parts(values):
    return [value for value in _items(values) if _match(value, r"P(?:[1-9]|[12][0-9]|3[012])")]


def _by_id(rows):
    return {row["id"]: row for row in _items(rows) if isinstance(row, dict) and isinstance(row.get("id"), str)}


def _matched_reference(row, published):
    def coordinates(loc):
        loc = _mapping(loc)
        return tuple(loc.get(key) for key in ("doc_id", "sha256", "page", "table", "row", "column", "field"))

    return any(left.get("doc_id") and coordinates(left) == coordinates(right)
               for left in row if isinstance(left, dict) for right in published)


def _publication(row, diagnostic, raw_id, selected, result, *, extract):
    if not result or not diagnostic:
        return "not_evaluated"
    if extract:
        if any(entry.get("text") == diagnostic.get("text") and entry.get("citations") == diagnostic.get("citations")
               for entry in map(_mapping, _items(result.get("extracts")))):
            return "published_as_source_verified_extract"
        if diagnostic.get("source_verified") is not True:
            return "source_verification_unproved"
        return ("reference_only" if _matched_reference(_items(diagnostic.get("citations")),
                                                         _items(result.get("citations")))
                else "extract_not_published")
    if any(raw_id in _items(entry.get("ids")) for entry in map(_mapping, _items(result.get("confirmed_elements")))):
        return "published_as_verified_fact"
    if raw_id not in selected:
        return "not_selected_by_candidate"
    status = diagnostic.get("technical_status")
    if status != "supported":
        return {"contradicted": "candidate_claim_contradicted", "invalid": "invalid_claim"}.get(
            status, "technical_verification_unproved")
    if row.get("kind") == "conditional_action":
        if any(raw_id == action.get("claim_id") for action in map(_mapping, _items(result.get("documented_actions")))):
            return "published_as_documented_conditional_action"
        return "conditional_action_restricted"
    return "supported_claim_not_published_as_verified_fact"


def _candidate(export, candidate, result):
    raw_hash = hashlib.sha256(candidate).hexdigest() if isinstance(candidate, bytes) else None
    empty = dict(export_status="unavailable", candidate_sha256=raw_hash, claims=[], evidence_extracts=[],
                 answer_claim_ids=[], unresolved_parts=[])
    if candidate is None:
        return empty | {"reason": "candidate_unavailable"}, {}
    try:
        packet = strict_json(candidate)
    except (ValueError, RecursionError):
        return empty | {"reason": "candidate_json_unavailable"}, {}
    if (not isinstance(packet, dict) or packet.get("version") != VERSION
            or not all(isinstance(packet.get(key), list) for key in ("claims", "evidence_extracts"))):
        return empty | {"reason": "candidate_schema_unavailable"}, {}

    diagnostics = _mapping(result.get("diagnostics"))
    report = empty | {"version": VERSION}
    id_map = {}
    selected = [key for key in _items(packet.get("answer_claim_ids")) if isinstance(key, str)]
    for key, prefix in (("claims", "C"), ("evidence_extracts", "X")):
        checked = _by_id(diagnostics.get(key))
        rows = packet[key]
        if len(rows) > 32:
            export.removed = True
        for index, row in enumerate(rows[:32], 1):
            if not isinstance(row, dict):
                export.removed = True
                continue
            raw_id = row.get("id")
            raw_id = raw_id if isinstance(raw_id, str) else None
            local_id = f"{prefix}{index}"
            if raw_id is not None and prefix == "C":
                id_map[raw_id] = local_id
            is_extract = prefix == "X"
            view = export.native_row(row, local_id, extract=is_extract)
            diagnostic = checked.get(raw_id, {})
            if diagnostic:
                view["verification"] = export.diagnostic(diagnostic, is_extract)
            view["publication"] = _publication(row, diagnostic, raw_id, selected, result, extract=is_extract)
            if diagnostic.get("schema_valid") is False or diagnostic.get("evidence_status") == "invalid":
                export.removed = True
            report[key].append(view)
    partial = export.removed or set(packet) != PACKET_FIELDS or result.get("status") == "invalid_contract"
    report.update(export_status="partial" if partial else "available",
                  answer_claim_ids=[id_map[key] for key in selected if key in id_map],
                  unresolved_parts=_parts(packet.get("unresolved")))
    if result.get("status") == "invalid_contract":
        report["reason"] = "candidate_contract_invalid"
    return report, id_map


def _assembly(export, result, id_map):
    answer = dict(export_status="unavailable", status=None, answer=None, verified_facts=[],
                  source_verified_extracts=[], citations=[], unresolved=[])
    if not result:
        return answer
    export.removed = False
    citations = [export.location(loc) for loc in _items(result.get("citations"), 512)]
    links = set()
    for loc in citations:
        if url := loc.get("url"):
            links.add(url + (f'#page={loc["page"]}' if "page" in loc else ""))
    answer.update(status=_enum(result.get("status"), _STATUS), citations=citations,
                  unresolved=[export.safe_text(text, 2000) for text in _items(result.get("unresolved"))])
    for row in map(_mapping, _items(result.get("confirmed_elements"))):
        answer["verified_facts"].append(dict(
            claim_ids=[id_map[item] for item in _items(row.get("ids")) if isinstance(item, str) and item in id_map],
            text=export.safe_text(row.get("text"), 2000),
            citations=[export.location(loc) for loc in _items(row.get("citations"), 512)],
        ))
    if actions := _items(result.get("documented_actions")):
        answer["documented_actions"] = [
            dict(claim_id=id_map.get(row.get("claim_id")), cause_claim_id=id_map.get(row.get("cause_claim_id")),
                 text=export.safe_text(row.get("text"), 2000),
                 citations=[export.location(loc) for loc in _items(row.get("citations"), 512)],
                 safety_conditions=[export.safe_text(text, 600) for text in _items(row.get("safety_conditions"), 8)])
            for row in map(_mapping, actions)
        ]
    for row in map(_mapping, _items(result.get("extracts"))):
        if row.get("source_verified") is not True:
            continue
        context = [export.safe_text(text) for text in _items(row.get("context"), 8)]
        if (len(_items(row.get("context"), 9)) > 8 or
                sum(len(text) for text in context if text is not None) > 1200):
            export.removed = True
            context = []
        answer["source_verified_extracts"].append(dict(
            text=export.safe_text(row.get("text"), 1200),
            context=context,
            technical_status=_enum(row.get("technical_status"), _TECHNICAL),
            context_status=_enum(row.get("context_status"), {"limited", "preserved", "unproved"}),
            citations=[export.location(loc) for loc in _items(row.get("citations"), 512)],
        ))
    if not export.removed:
        original = export.safe_text(result.get("answer"), 24000, links)
        if original is not None and all(len(block) <= 2600 for block in original.split("\n\n")):
            answer["answer"] = original
    answer["export_status"] = "partial" if answer["answer"] is None or answer["status"] is None else "available"
    return answer


def _provenance(provenance):
    result = {key: _match(provenance.get(key), rf"[a-f0-9]{{{size}}}") for key, size in _HASHES.items()}
    result.update(prompt_version=_match(provenance.get("prompt_version"), r"[a-z][a-z0-9_-]{0,29}/[0-9]{1,2}"),
                  **{key: _enum(provenance.get(key), choices) for key, choices in _OPTION_SETS.items()})
    settings = _mapping(provenance.get("model_settings"))
    model_settings = _compact({key: _enum(settings.get(key), choices) for key, choices in _OPTION_SETS.items()})
    for key in ("stream", "tools", "web_search"):
        if type(settings.get(key)) is bool:
            model_settings[key] = settings[key]
    if settings.get("max_tokens") == 8192:
        model_settings["max_tokens"] = 8192
    result["model_settings"] = model_settings
    dossier = _mapping(provenance.get("dossier"))
    result["dossier"] = _compact({key: _number(dossier.get(key), 500, whole=True)
                                 for key in ("pdf_count", "page_count")})
    if pdfs := _items(provenance.get("ordered_pdf_sha256"), 4):
        files = [_match(item, r"[a-f0-9]{64}") for item in pdfs]
        if None not in files:
            result["ordered_pdf_sha256"] = files
    return _compact(result)


def _telemetry(telemetry):
    result = {category: _compact({key: _number(_mapping(telemetry.get(category)).get(key),
                                              whole=category != "timing_ms") for key in sorted(keys)})
              for category, keys in _NUMBERS.items()}
    result["status"] = _enum(telemetry.get("status"), _RUN_STATUS)
    result["diagnostics"] = [code for code in _items(telemetry.get("diagnostics")) if _enum(code, _PROVIDER_REASON)]
    return result


def build_report(*, question, provenance, candidate, result, telemetry):
    """Create a data-minimized derivative. The runner retains private raw artifacts."""
    export = _Export(provenance, telemetry)
    candidate_report, id_map = _candidate(export, candidate, _mapping(result))
    assembled = _assembly(export, _mapping(result), id_map)
    return dict(
        schema="ds-dc-04a-quality-report/1", derivative_copy=True,
        redaction_rules=["Only explicitly enumerated data fields and diagnostic codes are exported.",
                         "Candidate item IDs are replaced by report-local IDs. Retained technical text is verbatim.",
                         "Unsafe, oversized or unrecognized content is omitted. The assembled answer is kept verbatim or withheld in full.",
                         "Only public source URLs are exported. Page coordinates describe locations, not technical claims."],
        question=dict(id=_match(provenance.get("question_id"), r"Q[0-9]{2}-N"),
                      text=export.safe_text(question, 2000)),
        provenance=_provenance(provenance), A=candidate_report, B=assembled, telemetry=_telemetry(telemetry),
        expert_score="NOT RUN",
    )


def markdown(report):
    """Render the already sanitized data as a Markdown experiment card."""
    def fenced(content, language="text"):
        width = max((len(match[0]) for match in re.finditer(r"`+", content)), default=0) + 1
        fence = "`" * max(3, width)
        return f"{fence}{language}\n{content}\n{fence}"

    def structured(content):
        return fenced(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False), "json")

    b = report["B"]
    pages = dict.fromkeys(
        row["url"] + (f'#page={row["page"]}' if "page" in row else "")
        for row in b["citations"] if "url" in row
    )
    return "\n\n".join([
        "# DS-DC-04A experiment card", "Sanitized derivative for owner review.",
        *[f"- {rule}" for rule in report["redaction_rules"]],
        "## Question and provenance", structured(dict(question=report["question"], **report["provenance"])),
        "## A · Native candidate before verification", structured(report["A"]),
        "## B · Deterministic assembly", fenced(b["answer"]) if b["answer"] is not None else "Answer unavailable.",
        structured({key: value for key, value in b.items() if key != "answer"}),
        *(["## Source pages", "\n".join(f"- <{page}>" for page in pages)] if pages else []),
        "## Timing, tokens and costs", structured(report["telemetry"]),
        f'## Independent expert score\n\n{report["expert_score"]}',
    ]) + "\n"
