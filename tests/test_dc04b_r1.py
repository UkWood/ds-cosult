"""R1 normalization and conditional publication on independent layouts."""
import json

import pytest

from ds_dc.evidence_answer import assemble
from ds_dc.technical_verifier import inspect_claim
from test_structural_evidence import candidate, grid, registry
from test_dc03c import synthetic_corpus

HEADERS = ["symptom", "possible cause", "corrective action"]
SYMPTOM = "Журнал модуля пуст"
CAUSE = "Отсутствует носитель"
ACTION = "Проверить наличие носителя"
QUALIFIED = "Работы по ремонту оборудования должны проводиться обученным квалифицированным персоналом."
LINK = "Признаки проявления неисправности, возможные причины и действия по устранению неисправности приведены в таблице 8."


def page_with_context(*rows, qualified=True):
    page = grid(HEADERS, *rows)
    table, = page["tables"]
    table["bbox"] = [60, 300, 510, 300 + 15 * len(table["rows"])]
    for i, row in enumerate(table["rows"]):
        for j, cell in enumerate(row):
            if cell:
                cell[0] = [60 + j * 150, 300 + i * 15, 210 + j * 150, 315 + i * 15]
    if qualified:
        page["blocks"] = [
            dict(text=QUALIFIED, x0=60, x1=500, top=257, bottom=269),
            dict(text=LINK, x0=60, x1=500, top=271, bottom=283),
            dict(text="Таблица 8", x0=435, x1=550, top=286, bottom=298),
        ]
    return page


def diagnostic_claim(reg, kind, *, alternate, symptom=SYMPTOM, cause=CAUSE, action=ACTION):
    if kind == "symptom":
        target, condition, qualifier, evidence = symptom, "", "observed", {"symptom": symptom}
    elif kind == "possible_cause":
        target, condition, qualifier, evidence = cause, symptom, "possible", {"symptom": symptom, "cause": cause}
    else:
        target, condition, qualifier, evidence = action, cause, "conditional", {"cause": cause, "action": action}
    subject, value = (condition, target) if alternate and condition else (target, "")
    packet = candidate(reg, kind, subject, value, "", "", "" if alternate else qualifier, condition, evidence)
    return packet["claims"][0]


def packet(reg, claims):
    for index, claim in enumerate(claims, 1):
        claim["id"] = f"C{index}"
    return dict(version="candidate-answer/2.1", request_id=reg.request_id, wire_identity=reg.wire_identity,
                claims=claims, answer_claim_ids=[claim["id"] for claim in claims],
                evidence_extracts=[], unresolved=[])


@pytest.mark.parametrize("kind", ["symptom", "possible_cause", "conditional_action"])
@pytest.mark.parametrize("alternate", [False, True])
def test_exact_roles_normalize_and_original_fields_are_preserved(kind, alternate):
    reg = registry()
    page = page_with_context([SYMPTOM, CAUSE, ACTION])
    item = diagnostic_claim(reg, kind, alternate=alternate)
    original = json.dumps(item)
    verdict = inspect_claim(item, reg, lambda *_: page)
    assert verdict["technical_status"] == "supported"
    assert verdict["normalization"]["status"] == ("normalized" if alternate else "canonical")
    assert verdict["normalization"]["verified_fields"]
    assert len(verdict["locators"]) == len(item["evidence"])
    assert json.dumps(item) == original


@pytest.mark.parametrize("mutation", [
    "wrong_subject", "wrong_value", "wrong_condition", "diagnosis", "mandatory", "added_value",
    "unit", "comparator", "wrong_quote", "cross_row", "cross_source", "cross_page", "cross_table", "wrong_variant",
    "ambiguous", "missing_cell", "unproved_document", "linked_prerequisite",
])
def test_inadmissible_alternatives_keep_their_negative_verdict(mutation):
    reg = registry(applicability=None if mutation == "unproved_document" else "reviewed cover")
    page = page_with_context([SYMPTOM, CAUSE, ACTION], ["Мигает индикатор", "Устарела версия", "Сверить версию"])
    if mutation == "cross_source":
        from dataclasses import replace

        from ds_dc.technical_registry import SourceRegistry

        original_source, = reg.sources.values()
        reg = SourceRegistry(reg.request_id, "a" * 64, list(reg.entities.values()),
                             [original_source, replace(original_source, sha256="c" * 64, doc_id="other")],
                             dict(reg.parts))
    claim = diagnostic_claim(reg, "conditional_action", alternate=True)
    if mutation == "wrong_subject":
        claim["subject"] = "Нет питания"
    elif mutation in {"wrong_value", "added_value"}:
        claim["value"] = "Сверить версию" if mutation == "wrong_value" else ACTION + " и заменить модуль"
    elif mutation == "wrong_condition":
        claim["condition"] = "Устарела версия"
    elif mutation in {"diagnosis", "mandatory"}:
        claim["qualifier"] = "certain" if mutation == "diagnosis" else "mandatory"
    elif mutation in {"unit", "comparator"}:
        claim[mutation] = "A"
    elif mutation == "wrong_quote":
        claim["evidence"][1]["quote"] = "Сверить версию немедленно"
    elif mutation == "cross_row":
        claim["evidence"][1]["quote"] = claim["value"] = "Сверить версию"
    elif mutation == "cross_source":
        claim["evidence"][1]["source"] = list(reg.sources)[1]
    elif mutation == "cross_page":
        claim["evidence"][1]["page"] = 2
    elif mutation == "cross_table":
        page["tables"].extend(grid(HEADERS, ["Другой признак", "Другая причина", "Другое действие"])["tables"])
        claim["evidence"][1]["quote"] = claim["value"] = "Другое действие"
    elif mutation == "wrong_variant":
        page = grid([*HEADERS, "variant"], [SYMPTOM, CAUSE, ACTION, "Machine B"])
    elif mutation == "ambiguous":
        page["tables"] *= 2
    elif mutation == "missing_cell":
        page["tables"][0]["rows"][1][0] = None
    elif mutation == "linked_prerequisite":
        page["blocks"].append(dict(text="Только после полного отключения питания.", x0=60, x1=500, top=350, bottom=360))
    verdict = inspect_claim(claim, reg, lambda *_: page)
    assert verdict["technical_status"] != "supported"
    assert verdict["normalization"]["status"] == "rejected"


@pytest.mark.parametrize("context,action,include_cause,documented", [
    (True, ACTION, True, True),
    (False, ACTION, True, False),
    (True, "Проверить напряжение на контактах", True, False),
    (True, "Проверить люфт вращающегося вала рукой", True, False),
    (True, "Проверить наличие искры замыканием выводов", True, False),
    (True, "Проверить наличие течи пальцем", True, False),
    (True, ACTION, False, False),
])
def test_action_requires_safe_context_and_a_verified_published_cause(context, action, include_cause, documented):
    reg = registry()
    page = page_with_context([SYMPTOM, CAUSE, action], qualified=context)
    claims = [diagnostic_claim(reg, "conditional_action", alternate=True, action=action)]
    if include_cause:
        claims.insert(0, diagnostic_claim(reg, "possible_cause", alternate=True))
    body = json.dumps(packet(reg, claims))
    result = assemble(body, reg, reg.wire_identity, lambda *_: page, {})
    assert result["diagnostics"]["claims"][-1]["technical_status"] == "supported"
    assert result["status"] in {"partial", "reference"}
    assert (action in result["answer"]) is documented
    assert bool(result.get("documented_actions")) is documented
    if documented:
        published, = result["documented_actions"]
        assert published["safety_conditions"] == [QUALIFIED]
        assert published["cause_claim_id"] == "C1"
        assert published["citations"][0]["page"] == 1
        assert QUALIFIED in result["answer"]
    if include_cause:
        assert CAUSE in result["answer"]
    assert result["unresolved"]


def test_qualification_from_a_reference_to_another_table_does_not_enable_action():
    reg = registry()
    page = page_with_context([SYMPTOM, CAUSE, ACTION])
    page["blocks"][1]["text"] = LINK.replace("8.", "9.")
    claims = [diagnostic_claim(reg, kind, alternate=True) for kind in ("possible_cause", "conditional_action")]
    result = assemble(json.dumps(packet(reg, claims)), reg, reg.wire_identity, lambda *_: page, {})
    assert result["diagnostics"]["claims"][1]["technical_status"] == "supported"
    assert result["diagnostics"]["claims"][1]["publication_reason"] == "unproved_work_safety"
    assert CAUSE in result["answer"] and ACTION not in result["answer"]


def test_safety_caption_below_an_adjacent_table_cannot_authorize_its_actions():
    reg = registry()
    page = page_with_context(["Пуст второй журнал", "Носитель не определён", "Проверить наличие второго носителя"])
    earlier = page_with_context([SYMPTOM, CAUSE, ACTION], qualified=False)["tables"][0]
    earlier["bbox"][1], earlier["bbox"][3] = 225, 255
    for row in earlier["rows"]:
        for cell in row:
            cell[0][1] -= 75
            cell[0][3] -= 75
    page["tables"].insert(0, earlier)
    claims = [diagnostic_claim(reg, kind, alternate=True) for kind in ("possible_cause", "conditional_action")]
    result = assemble(json.dumps(packet(reg, claims)), reg, reg.wire_identity, lambda *_: page, {})
    assert result["diagnostics"]["claims"][1]["technical_status"] == "supported"
    assert result["diagnostics"]["claims"][1]["publication_reason"] == "unproved_work_safety"
    assert CAUSE in result["answer"] and ACTION not in result["answer"]


def test_report_preserves_original_fields_and_separates_documented_actions():
    from ds_dc.quality_report import build_report
    from ds_dc.technical_registry import Entity, Source, SourceRegistry

    reg = SourceRegistry("private-test", "a" * 64, [Entity("machine:a", "Устройство A", "G1")],
                         [Source("machine:a", "G1", "pdf", "b" * 64, "c" * 64, "R1", 2,
                                 "https://www.mnppsaturn.ru/ftp/public/doc/mock.pdf", "reviewed cover")],
                         {"P1": "Почему журнал пуст?"})
    page = page_with_context([SYMPTOM, CAUSE, ACTION])
    original = packet(reg, [diagnostic_claim(reg, kind, alternate=True)
                            for kind in ("possible_cause", "conditional_action")])
    original["claims"][1]["id"] = "Original_private_id"
    original["answer_claim_ids"][1] = "Original_private_id"
    body = json.dumps(original).encode()
    result = assemble(body, reg, reg.wire_identity, lambda *_: page, {})
    report = build_report(question=reg.parts["P1"], provenance={"source_registry": reg.sources},
                          candidate=body, result=result, telemetry={})
    assert "Original_private_id" not in json.dumps(report)
    action = report["A"]["claims"][1]
    assert (action["subject"], action["value"], action["qualifier"]) == (CAUSE, ACTION, "")
    assert action["verification"]["normalization"]["status"] == "normalized"
    assert action["publication"] == "published_as_documented_conditional_action"
    published, = report["B"]["documented_actions"]
    assert (published["claim_id"], published["cause_claim_id"]) == ("C2", "C1")
    assert published["safety_conditions"] == [QUALIFIED]
    assert report["B"]["answer"] == result["answer"]
    assert report["B"]["status"] == "partial"


def test_future_prompt_changes_wire_and_preserves_historical_payload(synthetic_corpus):
    from ds_dc import evidence_integration as evidence
    from ds_dc.quality_lab import QUESTION, REQUEST_ID
    from ds_dc.prep import freeze, freeze_digest
    from ds_dc.corpus import BKD

    entries, dossiers, cache = synthetic_corpus
    manifest = freeze_digest(freeze(entries, dossiers))
    page = entries[BKD] | {"scope": [BKD]}
    docs = [doc | {"scope": BKD, "source_path": doc["path"], "field_path": doc["field"]}
            for doc in dossiers[BKD]["included_docs"]]
    args = REQUEST_ID, QUESTION, (), [page], docs, entries, manifest
    previous = evidence.build_request(*args)
    explicit = evidence.build_request(*args, prompt_version=evidence.PROMPT_VERSION)
    future = evidence.build_request(*args, prompt_version=evidence.FUTURE_PROMPT_VERSION)
    assert previous[1:3] == explicit[1:3]
    assert future[1] != previous[1]
    system = future[2]["messages"][0]["content"]
    assert "Не выдумывай недостающие технические характеристики." in system
    assert all(f"subject — текст ячейки {role}" in system for role in ("symptom", "cause", "action"))
    assert QUESTION not in system and "Q01" not in system
    payload = packet(previous[0], [])
    payload["wire_identity"] = previous[1]
    assert assemble(json.dumps(payload), future[0], future[1], lambda *_: {}, {})["status"] == "invalid_contract"
