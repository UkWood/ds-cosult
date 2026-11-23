"""Strict candidate-answer/2.1 verification and deterministic offline assembly."""
from collections import Counter, defaultdict
from itertools import combinations
import json
import re
import subprocess

from .corpus import digest, encoded
from .evidence_extract import pdf_fragment, site_fragment, site_identity
from .evidence_lab import nfc_text
from .technical_registry import COVER_REQUIRED, applicability_proved
from .technical_verifier import inspect_claim, numeric, word

VERSION = "candidate-answer/2.1"
PACKET_FIELDS = {"version", "request_id", "wire_identity", "claims", "answer_claim_ids",
                 "evidence_extracts", "unresolved"}
EXTRACT_FIELDS = {"id", "entity", "source", "quote", "conditions", "parts"}
IDENT = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,47}")
RISK = re.compile(r"питан|напряж|подключ(?:ить|айте|ите|ать|ения)|вывод[аы]|контакт|монтаж|ремонт|"
                  r"измер(?:ьте|ить|ять|ение\b)|калибров|поверк|зазем|провод[а-я]*\b|предохран|"
                  r"нейтрал|разбор|схем|\bпуск|замен",
                  re.I)
ACTION = re.compile(r"подать|обесточ|подсоед|подключите|замкни|замкнуть|перемк|шунтир|"
                  r"припая|снимите|установите|проверьте|сбросьте|отключите|включите|"
                  r"\b(?:connect|disconnect|repair|install|replace|remove|check|apply|calibrate|bridge)\b", re.I)
ELECTRICAL = re.compile(r"\b(?:power|voltage|volt|mains|wire|wiring|\d+\s*(?:v|a|в|а))\b", re.I)


# This narrow grammar covers checking a state or inspecting for a defect.
# It does not authorize a technique or a sequence of operations.
DOCUMENTED_CHECK = re.compile(
    r"проверить (?:(?:работоспособность|состояние|наличие|индикацию|целостность) (?P<state_target>[\w -]+)"
    r"|(?P<defect_target>[\w -]+) на (?:обрыв|повреждение|износ|замыкание)"
    r"(?: или (?:обрыв|повреждение|износ|замыкание))?)",
    re.I)
PROCEDURE_WORDING = re.compile(
    r"вскры|снят|откры|вытащ|извлеч|встав|резать|отрез|зачист|паять|замкну|включи|отключи|отсоедин|"
    r"рук[аой]|пальц|вручн|ощуп|враща|движущ|замыка|вывод|"
    r"\b(?:при|после|пут[её]м|затем|используя|нажать)\b", re.I)


def risky(text):
    return any(pattern.search(text) for pattern in (RISK, ACTION, ELECTRICAL))


def strict_json(raw):
    if not isinstance(raw, bytes) or len(raw) > 512 * 1024:
        raise ValueError("response_size_or_format")

    def object_from_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    def reject(_):
        raise ValueError("non_json_constant")

    data = json.loads(raw.decode("utf-8"), object_pairs_hook=object_from_pairs, parse_constant=reject)
    # JSON escape sequences can carry lone surrogates even with valid UTF-8 input.
    json.dumps(data, ensure_ascii=False).encode("utf-8")
    return data


def refs(values, available):
    return (isinstance(values, list) and len(values) <= 32
            and all(isinstance(v, str) and v in available for v in values)
            and len(set(values)) == len(values))


def contract(raw, registry, wire):
    payload = strict_json(raw.encode() if isinstance(raw, str) else raw)
    if (not isinstance(payload, dict) or set(payload) != PACKET_FIELDS
            or (payload["version"], payload["request_id"], payload["wire_identity"]) != (
                VERSION, registry.request_id, wire)
            or not all(isinstance(payload[key], list) and len(payload[key]) <= 32
                       for key in ("claims", "evidence_extracts"))):
        raise ValueError("invalid_response_contract")
    claims, extracts = payload["claims"], payload["evidence_extracts"]
    ids = [row.get("id") if isinstance(row, dict) else None for row in claims + extracts]
    if (any(not isinstance(key, str) or not IDENT.fullmatch(key) for key in ids)
            or len(ids) != len(set(ids))
            or not refs(payload["answer_claim_ids"], ids[:len(claims)])
            or not refs(payload["unresolved"], registry.parts)):
        raise ValueError("invalid_response_ids")
    return payload


def citation(source, locator, applicability_verified=True):
    locator = dict(locator)
    # Citations expose geometry and identity. Raw neighboring cells and blocked
    # source material are available only in the operator's evidence diagnostics.
    locator.pop("physical_rows", None)
    if "headers" in locator:
        locator["header_boxes"] = [header[0] for header in locator.pop("headers")]
    if "cells" in locator:
        locator["cell_boxes"] = [[{k: cell[k] for k in ("row", "column", "bbox")} for cell in row]
                                 for row in locator.pop("cells")]
    scope = source.applicability if applicability_verified else None
    if scope == COVER_REQUIRED:
        scope = "explicit_model_and_edition_on_cover"
    return dict(url=source.url, sha256=source.sha256, doc_id=source.doc_id, revision=source.revision,
                commit=source.commit, blob=source.blob, applicability=scope, **locator)


def inspect_extract(item, registry, extract_pdf, site_pages, applies):
    status = dict(id=item["id"], technical_status="semantic_pending", source_verified=False,
                  source_identity_verified=False, applicability_verified=False,
                  context_status="unproved", covered_parts=[])

    def finish(verdict, reason):
        return status | {"evidence_status": verdict, "reason_codes": [reason]}

    keys = set(item)
    if (keys not in (EXTRACT_FIELDS | {"page"}, EXTRACT_FIELDS | {"field"})
            or not all(isinstance(item[k], str) and item[k] for k in ("entity", "source", "quote"))
            or len(item["quote"]) > 8000 or not nfc_text(item["quote"])
            or not refs(item["parts"], registry.parts) or not isinstance(item["conditions"], list)
            or len(item["conditions"]) > 8
            or not all(isinstance(c, str) and 0 < len(c) <= 1000 for c in item["conditions"])):
        return finish("invalid", "invalid_extract_schema")
    source = registry.sources.get(item["source"])
    entity = registry.entities.get(item["entity"])
    if not source or not entity:
        return finish("invalid", "foreign_entity_or_source")
    if (source.canonical_entity, source.generation) != (entity.canonical_id, entity.generation):
        return finish("invalid", "extract_entity_mismatch")
    quote = nfc_text(item["quote"])
    try:
        if source.kind == "site":
            if not isinstance(item.get("field"), str):
                return finish("invalid", "invalid_site_location")
            page = site_pages.get(source.doc_id)
            if not site_identity(source, page):
                return finish("invalid", "site_identity_mismatch")
            status["source_identity_verified"] = True
            fragment = site_fragment(page["raw"], item["field"], quote)
            origin = {}
        else:
            page_number = item.get("page")
            if type(page_number) is not int or not 1 <= page_number <= source.pages:
                return finish("invalid", "invalid_pdf_location")
            page = extract_pdf(source, page_number)
            status["source_identity_verified"] = True
            fragment = pdf_fragment(page, quote, entity)
            origin = {"page": page_number}
    except (OSError, ValueError, subprocess.SubprocessError):
        return finish("semantic_pending", "source_unavailable")
    if fragment is None:
        return finish("semantic_pending", "literal_or_fragment_boundary_unproved")
    status["source_verified"] = True
    status["applicability_verified"] = applicability_proved(source, entity, applies)
    context = fragment["context"]
    conditions = {nfc_text(c) for c in item["conditions"]}
    trusted_context = {nfc_text(c) for c in context} | {nfc_text(fragment["text"])}
    if "cells" in fragment["locator"]:
        trusted_context.update(nfc_text(c["text"]) for row in fragment["locator"]["cells"] for c in row)
    limited = (fragment.get("context_limited", False) or not status["applicability_verified"]
               or not conditions <= trusted_context)
    origin = citation(source, origin | fragment["locator"], status["applicability_verified"])
    status.update(context_status="limited" if limited else "preserved",
                  text=fragment["text"], context=context, entity=entity.label,
                  applicability=origin["applicability"],
                  action_present=fragment.get("action_present", False),
                  evidence_locator=fragment["locator"],
                  citations=[origin])
    return finish("source_verified", "literal_fragment_verified")


def claim_text(kind, fields, entity):
    if kind in {"quantity", "quantity_limit", "quantity_range"}:
        base = f'{entity}. {fields["subject"]} — {fields["value"]} {fields["unit"]}.'
        details = [f"{label} — {fields[field]}." for field, label in (
            ("condition", "Условие"), ("qualifier", "Оговорка"), ("variant", "Исполнение")) if fields.get(field)]
        return " ".join([base, *details])
    if kind == "symptom":
        return f'{entity}. В таблице неисправностей указан признак «{fields["symptom"]}».'
    if kind == "possible_cause":
        return (f'{entity}. Для признака «{fields["symptom"]}» в документации приведена '
                f'возможная причина «{fields["cause"]}».')
    return (f'{entity}. В документации действие «{fields["action"]}» указано для причины '
            f'«{fields["cause"]}» при признаке «{fields["symptom"]}».')


def empty_answer(status, parts, message, diagnostics=None):
    return dict(answer=message, status=status, confirmed_elements=[], extracts=[], citations=[],
                unresolved=list(parts.values()), diagnostics=diagnostics or {})


def incompatible(a, b):
    if a[:2] == b[:2]:
        return a[2] != b[2]

    def bounds(observed):
        _, comparator, values = observed
        if comparator in ("eq", "range"):
            return (values[0], True), (values[-1], True)
        bound = (values[0], comparator in ("le", "ge"))
        return (None, bound) if comparator in ("le", "lt") else (bound, None)

    def separated(high, low):
        return high is not None and low is not None and (
            high[0] < low[0] or high[0] == low[0] and not (high[1] and low[1]))

    lower_a, upper_a = bounds(a)
    lower_b, upper_b = bounds(b)
    return separated(upper_a, lower_b) or separated(upper_b, lower_a)


def diagnostic_row(item, checked):
    fields = checked["verified_fields"]
    loc = checked["locators"][0]
    cause = next(loc for evidence, loc in zip(item["evidence"], checked["locators"], strict=True)
                 if evidence["role"] == "cause")
    return (item["entity"], loc["source"], cause["page"], cause["table"], cause["row"], cause["column"],
            fields["symptom"], fields["cause"], fields["action"])


def assemble(raw, registry, wire, extract_pdf, site_pages, *, reviewed_coverage=None, applies=None):
    """Optional server review binds exact part, item and provenance digests to this wire."""
    try:
        payload = contract(raw, registry, wire)
    except (ValueError, RecursionError):
        return empty_answer("invalid_contract", registry.parts,
                            "Проверка пакета не пройдена. Документальных выводов пока нет.")

    claims = [inspect_claim(claim, registry, extract_pdf, applies=applies) for claim in payload["claims"]]
    extracts = [inspect_extract(item, registry, extract_pdf, site_pages, applies) for item in payload["evidence_extracts"]]
    evidence_groups = defaultdict(list)
    for item, checked in zip(payload["claims"], claims, strict=True):
        fields = checked.get("verified_fields", {})
        if item.get("kind") in ("quantity", "quantity_limit", "quantity_range") and fields:
            key = (item["entity"], *(word(fields.get(k, "")) for k in ("subject", "condition", "qualifier")),
                   fields["unit"])
            evidence_groups[key].append((item["id"], numeric(fields["value"])))
    conflicts = {key for group in evidence_groups.values() for (left, a), (right, b) in combinations(group, 2)
                 if incompatible(a, b) for key in (left, right)}
    chosen = set(payload["answer_claim_ids"])
    risk = any(risky(part) for part in registry.parts.values())
    confirmed, output_extracts, citations, passages = {}, [], [], {}
    documented_actions = []
    causes = {
        diagnostic_row(item, checked): item["id"]
        for item, checked in zip(payload["claims"], claims, strict=True)
        if checked["technical_status"] == "supported" and item["kind"] == "possible_cause"
        and item["id"] in chosen and not risky(claim_text(
            item["kind"], checked["verified_fields"], registry.entities[item["entity"]].label))
    }
    deferred, covered = set(), set()

    def emit(text, origins):
        urls = passages.setdefault(text, {})
        for origin in origins:
            url = origin["url"] + (f'#page={origin["page"]}' if "page" in origin else "")
            urls[url] = None
            if origin not in citations:
                citations.append(origin)

    def cover(item, text, origins, checked):
        if not reviewed_coverage:
            return
        for part in item["parts"]:
            key = digest(encoded([wire, part, registry.parts[part], item["id"], text, origins]).encode())
            if key in reviewed_coverage:
                covered.add(part)
                checked["covered_parts"].append(part)

    for item, checked in zip(payload["claims"], claims, strict=True):
        key = item["id"]
        verdict = checked["technical_status"]
        if key not in chosen and key not in conflicts:
            continue
        if verdict not in {"supported", "contradicted"}:
            if checked["schema_valid"]:
                deferred.update(item["parts"])
            continue
        origins = [citation(registry.sources[loc["source"]], {
            k: v for k, v in loc.items() if k in {"page", "table", "row", "column", "bbox"}})
                   for loc in checked["locators"]]
        fields = checked["verified_fields"]
        entity = registry.entities[item["entity"]].label
        text = claim_text(item["kind"], fields, entity)
        scope = origins[0]["applicability"]
        if scope and scope.startswith(entity + ", "):
            text += f" Область документа — {scope}."
        if item["kind"] == "conditional_action":
            cause = causes.get(diagnostic_row(item, checked))
            safety = checked.get("work_safety")
            action = fields["action"]
            check = DOCUMENTED_CHECK.fullmatch(action)
            if (safety and cause and check and not risky(text)
                    and not PROCEDURE_WORDING.search(check["state_target"] or check["defect_target"])):
                context = citation(registry.sources[checked["locators"][0]["source"]],
                                   {"page": origins[0]["page"], "bbox": safety["bbox"]})
                conditions = safety["conditions"]
                action_origins = [*origins, context]
                text += " Здесь указано направление проверки. Порядок и способ выполнения уточняются по руководству."
                emit(text, action_origins)
                emit("Ограничения руководства для этих работ. " + " ".join(conditions), [context])
                documented_actions.append(dict(claim_id=key, cause_claim_id=cause, text=text,
                                               citations=action_origins, safety_conditions=conditions))
                checked["publication_reason"] = "documented_conditional_action"
                deferred.update(item["parts"])
                continue
            checked["publication_reason"] = ("unproved_paired_cause" if not cause else
                                              "unproved_work_safety" if not safety else "hazardous_or_unreviewed_action")
        restricted = item["kind"] == "conditional_action" or risky(text)
        if restricted or key in conflicts or verdict == "contradicted":
            reference_only = restricted and ("value" not in fields or not fields.get("condition"))
            label = ("В источниках указаны разные значения. " if key in conflicts else
                     "В документации указано другое значение. " if verdict == "contradicted" else "Справочно. ")
            if reference_only:
                label += "Уточните исполнение и условия по документации или в службе поддержки."
                if any(entry["category"] == "safety" for entry in checked.get("context_evidence", ())):
                    label += " Соблюдайте требования безопасности из источника."
            else:
                label += text
            emit(label, origins)
            deferred.update(item["parts"])
            continue
        emit(text, origins)
        entry = confirmed.setdefault(text, dict(ids=[], text=text, citations=[]))
        entry["ids"].append(key)
        entry["citations"].extend(origin for origin in origins if origin not in entry["citations"])
        cover(item, text, origins, checked)

    for item, checked in zip(payload["evidence_extracts"], extracts, strict=True):
        if not checked["source_verified"]:
            continue
        origins = checked["citations"]
        text = checked["text"]
        context = " ".join(nfc_text(line) for line in checked["context"] if line.strip())
        limited = checked["context_status"] == "limited"
        hide_text = checked["action_present"] or risk or risky(text + " " + context)
        if hide_text or not checked["applicability_verified"]:
            emit("В документации есть справочный материал. Уточните применимость и условия по источнику.",
                 origins)
            deferred.update(item["parts"])
            continue
        attribution = (f'В документации указана следующая запись: «{text}».' if limited else
                       f'В документации для {checked["entity"]} указано: «{text}».')
        if context:
            attribution += f" Контекст источника: «{context}»."
        if checked["applicability"] and checked["applicability"].startswith(checked["entity"] + ", "):
            attribution += f' Область документа — {checked["applicability"]}.'
        if limited:
            attribution += " Применимость записи и её условия требуют сверки."
            deferred.update(item["parts"])
        emit(attribution, origins)
        output_extracts.append(dict(text=text, context=checked["context"], technical_status="semantic_pending",
                                    source_verified=True, context_status=checked["context_status"],
                                    applicability=checked["applicability"], citations=origins))
        if not limited:
            cover(item, attribution, origins, checked)

    lines = [text + (" Источник: " + ", ".join(urls) if urls else "") for text, urls in passages.items()]
    unresolved = [text for part, text in registry.parts.items()
                  if part not in covered or part in deferred or part in payload["unresolved"]]
    if unresolved:
        lines.append("По следующим частям вопроса подтверждение или полнота пока не установлены: "
                     + " / ".join(unresolved))
    if not citations:
        lines.insert(0, "Подтверждённых сведений по запросу не найдено.")
    status = ("full" if not unresolved else "partial" if confirmed else
              "reference" if citations else "needs_support")
    result = dict(answer="\n\n".join(lines), status=status, confirmed_elements=list(confirmed.values()),
                  extracts=output_extracts, citations=citations, unresolved=unresolved,
                  diagnostics={"claims": claims, "evidence_extracts": extracts,
                               "source_conflicts": len(conflicts), "technical_verdicts": dict(
                                   Counter(row["technical_status"] for row in claims))})
    if documented_actions:
        result["documented_actions"] = documented_actions
    return result
