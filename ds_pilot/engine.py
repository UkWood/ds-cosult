"""Local turn admission, immutable question coverage and controlled rendering."""
from contextlib import contextmanager
from dataclasses import asdict, replace
import fcntl
from datetime import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import time
import unicodedata
from zoneinfo import ZoneInfo

from .catalog import DocumentReference, Relation
from .questions import ALIASES, DICTIONARY, POLICY, OVERRIDE, entities, finalize, normalize, spans

COOLDOWNS = (0, 0, 0, 0, 0, 10, 20, 40, 60, 90)
MESSAGES = {
    "ambiguous_entity": "Уточните модель: БКД-ПК-RF.2 или СЛДКС-1.",
    "ambiguous_question": "Уточните интересующий параметр или задайте вопросы по отдельности.",
    "ambiguous_variant": "Уточните поколение и конфигурацию системы.",
    "insufficient_evidence": "В проверенных источниках недостаточно сведений для этой части вопроса.",
    "source_scope_not_indexed": "Для этого утверждения нет подтверждённого фрагмента документа.",
    "interpretation_unsupported": "Уточните модель и интересующий параметр.",
    "invalid_model_plan": "План модели не подтвердил эту часть запроса.",
    "applicable_source_conflict": "В применимых источниках указаны разные значения.",
    "verifier_internal_error": "Не удалось завершить проверку ответа.",
    "source_integrity_error": "Контроль источника не пройден.",
    "source_unavailable": "Не удалось прочитать источник.",
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def deny(reason, text, status="blocked", **extra):
    return dict(status=status, reason_code=reason, text=text, **extra)


def interpretation_options(question, needs, catalog):
    """Bound a model suggestion to one original span and a checked scoped attribute."""
    options = []
    idioms = {
        "mass": r"(?:сколько (?:он |она )?покажет на весах|насколько (?:он |она )?тяж[её]л(?:ый|ая)?)",
        "dimensions": r"(?:сколько места (?:он |она )?занимает|каких (?:он |она )?габаритов)",
        "purpose": r"(?:зачем (?:он |она )?нуж(?:ен|на)|для каких задач (?:он |она )?нуж(?:ен|на))",
    }
    for need in needs:
        options.append(dict(need_id=need.id, entity=need.entity, attribute=need.attribute))
        if need.attribute != "unknown" or not need.entity:
            continue
        left, right = need.span
        phrase = " ".join(ALIASES.sub("", normalize(question[left:right])).split())
        for attribute, pattern in idioms.items():
            if re.fullmatch(pattern, phrase) and catalog.records.get((need.entity, attribute)):
                options.append(dict(need_id=need.id, entity=need.entity, attribute=attribute))
    return options


class Pilot:
    def __init__(self, catalog, database, timezone="Europe/Moscow", mock=None,
                 mock_budget=0, mock_input_tokens=1, mock_output_tokens=450, *, lab=False, live=None):
        if live and (not lab or mock):
            raise ValueError("Live requires isolated LAB mode")
        self.lab = lab
        self.live = live
        self.catalog = catalog
        self.database = Path(database)
        self.timezone = ZoneInfo(timezone)
        self.mock = mock
        self.mock_budget = mock_budget
        self.mock_input_tokens = mock_input_tokens
        self.mock_output_tokens = mock_output_tokens
        self.database.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.database, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        os.close(fd)
        with self.tx() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS turns (
                request TEXT PRIMARY KEY, session TEXT NOT NULL, received REAL NOT NULL,
                day TEXT NOT NULL, stage TEXT NOT NULL, admitted TEXT NOT NULL,
                mode TEXT NOT NULL, dispatch INTEGER NOT NULL DEFAULT 0,
                frozen TEXT, needs_hash TEXT, response TEXT, responded REAL,
                referent TEXT, delivery TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS source_index (
                record_id TEXT PRIMARY KEY, entity TEXT NOT NULL, attribute TEXT NOT NULL,
                payload TEXT NOT NULL)""")
            db.execute("DELETE FROM source_index")
            db.executemany("INSERT INTO source_index VALUES (?, ?, ?, ?)", (
                (record.id, record.entity, record.attribute, encode(asdict(record)))
                for records in catalog.records.values() for record in records
            ))

    @contextmanager
    def tx(self):
        db = sqlite3.connect(self.database)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            with db:
                yield db
        finally:
            db.close()

    def ask(self, question, session, request, *, now=None, mode="P0"):
        # A process dying between admission and answer releases the OS lock.
        with self.database.with_suffix(".turn.lock").open("a+b") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return deny("in_flight", "Другой запрос ещё выполняется.")
            return self._ask(question, session, request, now, mode)

    def history(self, session):
        with self.tx() as db:
            rows = db.execute("SELECT admitted,response FROM turns WHERE session=? AND response IS NOT NULL ORDER BY received,rowid", (session,))
            return [{"question": json.loads(row["admitted"])["original_question_exact"],
                     "answer": json.loads(row["response"])} for row in rows]

    def reset(self, session):
        if not self.lab:
            raise ValueError("Сброс доступен только в лаборатории.")
        with self.database.with_suffix(".turn.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.tx() as db:
                db.execute("DELETE FROM turns WHERE session=?", (session,))

    def _ask(self, question, session, request, now, mode):
        real_clock = now is None
        now = time.time() if real_clock else now
        if not isinstance(question, str) or not question.strip() or len(question) > 1200:
            return deny("invalid_question", "Введите вопрос длиной от 1 до 1200 символов.")
        if not session or not request or len(session) > 100 or len(request) > 100:
            return deny("invalid_request", "Некорректный идентификатор запроса.")
        if unicodedata.normalize("NFC", question) != question:
            return deny("invalid_question", "Введите вопрос в нормальной форме Unicode NFC.")
        if OVERRIDE.search(question):
            return deny("policy_override_attempt", "Можно задавать вопросы о БКД-ПК-RF.2 и СЛДКС-1.")
        day = datetime.fromtimestamp(now, self.timezone).date().isoformat()
        with self.tx() as db:
            db.execute("DELETE FROM turns WHERE received <= ?", (now - 30 * 86400,))
            interrupted = deny("interrupted", "Процесс прервался. Для продолжения задайте новый вопрос.", "error")
            db.execute("UPDATE turns SET response=?, stage='INTERRUPTED', responded=? WHERE response IS NULL", (encode(interrupted), now))
            prior = db.execute("SELECT * FROM turns WHERE request=?", (request,)).fetchone()
            if prior:
                if prior["session"] != session or json.loads(prior["admitted"])["original_question_exact"] != question or prior["mode"] != mode:
                    return deny("idempotency_conflict", "Идентификатор уже связан с другим запросом.")
                if prior["response"]:
                    return json.loads(prior["response"])
                return deny("in_flight", "Запрос уже принят.")
            scope = "WHERE session=?" if self.lab else ""
            last = db.execute(f"SELECT * FROM turns {scope} ORDER BY received DESC, rowid DESC LIMIT 1",
                              (session,) if self.lab else ()).fetchone()
            series = 0
            referent = None
            if last and now - last["received"] < 1800:
                if last["session"] != session and now - last["received"] < 900:
                    return deny("session_locked", "В этой локальной среде уже открыт активный чат.")
                series = json.loads(last["admitted"])["series"]
                if (last["session"] == session and now - last["received"] < 900
                        and json.loads(last["admitted"])["source"] == self.catalog.manifest()):
                    referent = last["referent"]
            if db.execute("SELECT 1 FROM turns WHERE response IS NULL").fetchone():
                return deny("in_flight", "Другой запрос уже принят.")
            if mode not in {"P0", "P1", "P2"}:
                return deny("invalid_mode", "Неизвестный режим.")
            if mode != "P0":
                if not self.live and (not self.mock or not 0 <= self.mock_input_tokens <= 10000 or not 1 <= self.mock_output_tokens <= 450):
                    return deny("provider_disabled", "Доступен локальный режим P0.")
                reserved = db.execute("SELECT count(*) FROM turns WHERE mode != 'P0'").fetchone()[0]
                if not self.live and reserved >= self.mock_budget:
                    return deny("paid_budget_exhausted", "Тестовый лимит исчерпан. Доступен P0.")
                if not entities(normalize(question)) and not referent:
                    return deny("domain_out_of_scope", "Назовите БКД-ПК-RF.2 или СЛДКС-1.")
            count = db.execute("SELECT count(*) FROM turns WHERE day=?", (day,)).fetchone()[0]
            if not self.lab and count >= 20:
                return deny("daily_limit", "Достигнут дневной лимит вопросов.")
            if not self.lab and series >= 10:
                return deny("series_limit", "Обратитесь к специалисту или вернитесь после 30 минут бездействия.")
            cooldown = 0 if self.lab else COOLDOWNS[series]
            if cooldown and last and now - last["received"] < cooldown:
                return deny("cooldown", "Подождите перед следующим вопросом.",
                            retry_after=max(1, int(cooldown - (now - last["received"]) + 0.999)))
            if self.live and mode != "P0":
                try:
                    self.live.reserve(request)
                except ValueError as exc:
                    return deny("paid_budget_blocked", str(exc))
            anchors = list(spans(question))
            admitted = dict(original_question_exact=question, anchors=anchors, referent=referent,
                            request_id=request, source=self.catalog.manifest(),
                            policy=POLICY, dictionary=DICTIONARY, series=series + 1, ip="127.0.0.1")
            db.execute("""INSERT INTO turns (request,session,received,day,stage,admitted,mode)
                          VALUES (?,?,?,?,?,?,?)""",
                       (request, session, now, day, "ADMITTED", encode(admitted), mode))
        try:
            answer, new_referent = self.complete(admitted, mode)
        except Exception:
            answer = deny("verifier_internal_error", MESSAGES["verifier_internal_error"], "error")
            new_referent = referent
        answer["route_used"] = mode
        if mode != "P0" and self.live:
            receipt = self.live.receipt(request)
            answer["paid_receipt"] = receipt
            answer["provider_attempts"] = receipt.get("attempts", 0)
        with self.tx() as db:
            db.execute("""UPDATE turns SET stage='READY', response=?, responded=?, referent=?
                          WHERE request=?""",
                       (encode(answer), time.time() if real_clock else now, new_referent, request))
        return answer

    def dispatch(self, mode, request, payload):
        with self.tx() as db:
            updated = db.execute("""UPDATE turns SET dispatch=1 WHERE request=? AND mode=?
                                 AND dispatch=0 AND response IS NULL""", (request, mode))
            if updated.rowcount != 1:
                raise RuntimeError("Provider attempt fence")
        try:
            if self.live:
                return self.live.dispatch(request, mode, payload)
            return self.mock(mode, payload)
        except (TimeoutError, ValueError):
            return None

    def complete(self, admitted, mode):
        request = admitted["request_id"]
        reason = None
        if mode == "P1":
            preliminary, _ = finalize(admitted["original_question_exact"], admitted["anchors"], admitted["referent"])
            options = interpretation_options(admitted["original_question_exact"], preliminary, self.catalog)
            plan = self.dispatch(mode, request, {"question": admitted["original_question_exact"],
                                                 "referent": admitted["referent"], "allowed_options": options})
            if not isinstance(plan, dict) or set(plan) not in ({"interpretation_status", "need_ids"}, {"interpretation_status", "need_ids", "interpretations"}) or (
                plan["interpretation_status"] not in ("supported", "unsupported")
                or not isinstance(plan["need_ids"], list)
                or any(not isinstance(item, str) for item in plan["need_ids"])
                or len(set(plan["need_ids"])) != len(plan["need_ids"])
            ):
                reason = "invalid_model_plan"
            elif "interpretations" in plan and (not isinstance(plan["interpretations"], list) or any(item not in options for item in plan["interpretations"])):
                reason = "invalid_model_plan"
            elif plan["interpretation_status"] == "unsupported":
                reason = "interpretation_unsupported"
        needs, referent = finalize(admitted["original_question_exact"], admitted["anchors"], admitted["referent"])
        if mode == "P1" and reason is None and set(plan["need_ids"]) - {need.id for need in needs}:
            reason = "invalid_model_plan"
        if mode == "P1" and reason is None:
            suggestions = plan.get("interpretations", [])
            selected = {item["need_id"]: item["attribute"] for item in suggestions}
            if len(selected) != len(suggestions) or set(selected) - set(plan["need_ids"]):
                reason = "invalid_model_plan"
            else:
                needs = [replace(need, attribute=selected.get(need.id, need.attribute)) for need in needs]
        frozen = [dict(asdict(need), span=list(need.span)) for need in needs]
        fingerprint = hashlib.sha256(encode([admitted, frozen]).encode()).hexdigest()
        with self.tx() as db:
            updated = db.execute("""UPDATE turns SET stage='FROZEN', frozen=?, needs_hash=?
                                     WHERE request=? AND stage='ADMITTED' AND needs_hash IS NULL""",
                                 (encode(frozen), fingerprint, request))
            if updated.rowcount != 1:
                raise RuntimeError("QuestionNeeds already frozen")
        candidates = {need.id: self.lookup(need) for need in needs}
        dependencies = self.dependencies(admitted, needs, candidates)
        selection = None
        if mode == "P2":
            plan = self.dispatch(mode, request, {
                "question": admitted["original_question_exact"], "needs": frozen,
                "evidence": {record.id: record.text for group in candidates.values() for record in group},
                "question_needs_hash": fingerprint,
                "candidates": {key: [record.id for record in records] for key, records in candidates.items()},
            })
            if isinstance(plan, dict) and set(plan) == {"question_needs_hash", "selection"} and (
                plan["question_needs_hash"] == fingerprint and isinstance(plan["selection"], dict)
            ):
                selection = plan["selection"]
                if set(selection) - set(candidates) or any(
                    not isinstance(ids, list) or any(not isinstance(item, str) for item in ids)
                    or len(set(ids)) != len(ids) or set(ids) - {record.id for record in candidates[key]}
                    for key, ids in selection.items()
                ):
                    selection = None
        failures, conflicted = {}, set()
        for need in needs:
            records = candidates[need.id]
            failure = reason
            if mode == "P2" and (selection is None or (records and
                set(selection.get(need.id, [])) != {record.id for record in records})):
                failure = "invalid_model_plan"
            if not failure:
                if need.entity is None:
                    failure = "ambiguous_entity"
                elif need.variant == "unresolved":
                    failure = "ambiguous_variant"
                elif need.attribute == "ambiguous":
                    failure = "ambiguous_question"
                elif not records:
                    failure = ("source_scope_not_indexed" if (need.attribute in {"pdf", "terminal"} or need.attribute.startswith("pdf_"))
                               else "insufficient_evidence")
            values = {}
            for record in records:
                values.setdefault(record.attribute, set()).add(encode(record.value))
            conflict = not failure and need.attribute not in {"composition", "generation", "manual", "feature"} and any(
                len(items) > 1 for items in values.values())
            if conflict:
                conflicted.add(need.id)
                failure = "applicable_source_conflict"
            if failure:
                failures[need.id] = failure

        for dependent, prerequisite in dependencies.items():
            if prerequisite in failures:
                failures[dependent] = failures[prerequisite]
                conflicted.discard(dependent)

        claims, documents, positions, diagnostics, lines = [], [], [], [], []
        for need in needs:
            records = candidates[need.id]
            failure = failures.get(need.id)
            conflict = need.id in conflicted
            if conflict:
                failure = "applicable_source_conflict"
                for record in records:
                    self.bind(positions, lines, need, record, "position_id", "Источник указывает: ")
            if failure:
                diagnostics.append(dict(need_id=need.id, reason_code=failure))
                lines.append(MESSAGES[failure])
            else:
                if selection is not None and records:
                    by_id = {record.id: record for record in records}
                    records = [by_id[key] for key in selection[need.id]]
                for record in records:
                    if isinstance(record, DocumentReference):
                        self.bind(documents, lines, need, record, "document_reference_id")
                    else:
                        self.bind(claims, lines, need, record, "claim_id")
        status, code = reduce_status(claims, documents, diagnostics, mode)
        if status in {"clarification", "error"}:
            positions.clear()
            lines = [MESSAGES[code]]
        retrieval = self.catalog.search(admitted["original_question_exact"], limit=3)
        return dict(status=status, reason_code=code, retrieval_candidates=retrieval, text="\n".join(dict.fromkeys(lines)),
                    question_needs=frozen, question_needs_hash=fingerprint, dependencies=dependencies,
                    verified_claims=claims, document_references=documents, conflict_positions=positions,
                    unresolved_need_ids=[item["need_id"] for item in diagnostics],
                    diagnostics=diagnostics, coverage=self.catalog.coverage,
                    provider_attempts=int(mode != "P0")), referent if status in {"answered", "partial"} else admitted["referent"]

    def dependencies(self, admitted, needs, candidates):
        """The only supported conditional edge is an explicitly requested M2 prerequisite."""
        question = normalize(admitted["original_question_exact"])
        if "если" not in question:
            return {}
        prerequisite = next((need for need in needs if need.attribute == "generation"
                             and need.entity == "sld" and need.variant == "m2"), None)
        if prerequisite is None or not candidates[prerequisite.id]:
            return {}
        source = candidates[prerequisite.id][0].evidence
        return {
            need.id: prerequisite.id for need in needs
            if need.attribute == "composition" and need.entity == "sld" and need.variant == "m2"
            and candidates[need.id] and all(
                record.evidence.blob == source.blob
                and record.evidence.path == source.path
                and isinstance(record, Relation)
                for record in candidates[need.id]
            )
        }

    def lookup(self, need):
        if need.variant == "unresolved":
            return []
        if need.attribute == "power":
            return [record for key in ("dc", "ac")
                    for record in self.catalog.records.get((need.entity, key), [])]
        records = self.catalog.records.get((need.entity, need.attribute), [])
        if need.attribute == "composition":
            configuration = {"m2": "M2 с АРМ диспетчера", "m2_standalone": "М2 без компьютера",
                             "gen1": "1 поколение, аналоговый звук", "gen2": "2 поколение, серия М"}.get(need.variant)
            return [r for r in records if r.configuration == configuration]
        if need.attribute == "generation" and need.variant == "m2":
            return [record for record in records if "серия М2" in record.text]
        return records

    def bind(self, target, lines, need, record, label, prefix=""):
        text = prefix + self.catalog.entities[need.entity].name + " — " + record.text
        object_id = f"{need.id}:{record.id}"
        item = dict(need_id=need.id, text=text, **{label: object_id},
                    citation=dict(target_type=label, target_id=object_id, **asdict(record.evidence)))
        if label == "claim_id":
            item.update(proof_state="eligible", publication_role="established_fact")
            if isinstance(record, Relation):
                item["configuration"] = record.configuration
        if isinstance(record, DocumentReference):
            item["document_url"] = record.document_url
        target.append(item)
        lines.append(text)

    def delivery(self, request, outcome):
        with self.tx() as db:
            db.execute("UPDATE turns SET delivery=? WHERE request=? AND response IS NOT NULL",
                       (outcome, request))


def reduce_status(claims, documents, diagnostics, mode):
    if not diagnostics:
        if not claims and not documents:
            return "clarification", "ambiguous_question"
        return "answered", "fully_supported" if claims else "document_reference_only"
    errors = ["verifier_internal_error", "source_integrity_error", "source_unavailable"]
    clarification = ["interpretation_unsupported", "ambiguous_variant", "ambiguous_entity", "ambiguous_question"]
    support = ["applicable_source_conflict", "source_scope_not_indexed", "insufficient_evidence"]
    (clarification if mode == "P1" else support).insert(0, "invalid_model_plan")
    ranking = errors + clarification + support
    code = min((item["reason_code"] for item in diagnostics), key=ranking.index)
    if claims or documents:
        return "partial", code
    if code in errors:
        return "error", code
    if code in clarification:
        return "clarification", code
    return "needs_support", code
