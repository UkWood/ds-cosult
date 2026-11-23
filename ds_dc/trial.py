"""Owner trial chain from the accepted Resolver to the Evidence-First R1 answer."""
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
from threading import RLock
import time
from urllib.parse import unquote
from uuid import uuid4

from ds_pilot.questions import OVERRIDE

from . import context
from .corpus import COMMIT, PIN, digest, encoded
from .evidence_integration import FUTURE_PROMPT_VERSION, build_request, measure, verify_reply
from .finance import OWNER
from .native import NativeD1, PARSED_BYTES_LIMIT
from .prep import freeze, freeze_digest, load
from .quality_report import build_report
from .recovery import MANIFEST
from .resolver import Resolver
from .runtime import HOSTILE, Pilot, Session

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "docs/reports/ds-dc-02/corpus-manifest.json"
REQUEST = re.compile(r"[A-Za-z0-9_-]{1,100}")
PRIVATE = re.compile(r"\b(?:sk-[\w-]{6,}|file-api-[\w-]+|chatcmpl-[\w-]+|bearer\s+\S+)", re.I)
USAGE_PANEL = "https://platform.deepseek.com/usage"
CAP_SCOPE = {"id": "manual", "label": "Основное руководство"}
OMITTED = "Часть закреплённых материалов недоступна для этой проверки."
OUTSIDE = "Часть ссылок страницы не входит в утверждённую область или недоступна."
NARROWED = "Выбраны основные руководства и закреплённые страницы. Остальные PDF вне выбранной области."
MESSAGES = {
    "offline": "Стенд офлайн. Подбор источников выполнен. Запрос DeepSeek не отправлен.",
    "clarification": "Укажите обозначение изделия из каталога покрытия.",
    "not_ready": "Для выбранного изделия нет закреплённого досье.",
    "domain_denied": "Задайте технический вопрос без адресов, ключей и служебных инструкций.",
    "invalid_request": "Не удалось принять вопрос. Проверьте длину и выбранную область.",
    "over_cap": "Документальная область превышает локальный лимит. Выберите основное руководство или начните новый диалог с более узким вопросом.",
    "incomplete_dossier": "Закреплённые источники для выбранной области недоступны.",
    "sizing_unavailable": "Не удалось подтвердить локальный размер запроса.",
    "invalid_contract": "Формат ответа модели не позволил проверить технические сведения.",
    "provider_unknown": "Операция у провайдера не подтверждена. Начисление неизвестно. Проверьте DeepSeek Usage перед новым запуском.",
    "budget_exhausted": "Доступного остатка лимита запуска недостаточно для резерва запроса.",
    "finish_not_stop": "Ответ модели завершился не полностью. Доступный usage отражён отдельно.",
    "provider_failure": "Операция DeepSeek завершилась ошибкой. Возможное начисление отражено в журнале. Проверьте DeepSeek Usage.",
    "native_state_unavailable": "Запись учёта недоступна. Перед продолжением проверьте состояние и DeepSeek Usage.",
    "file_unavailable": "Оригинал PDF стал недоступен после выбора источников. Проверьте локальный кэш.",
    "binding_expiry_before_chat": "Действие привязки PDF истекает. Новый запрос возможен только по вашей отправке.",
    "invalid_native_request": "Настройки запроса не прошли проверку. Отправки не было.",
    "invalid_candidate": "Полученный пакет модели непригоден для доказательной проверки.",
    "contract_expired": "Срок проверки условий DeepSeek истёк. Новых операций не было.",
    "duplicate_request": "Этот запрос уже был принят. Новых операций не выполнено.",
}
CHOICE_REASONS = {"ambiguous_function", "ambiguous_models", "ambiguous_reference", "clarification"}


def load_trial_materials(site, cache):
    """Read the frozen acceptance scope and admit only locally matching originals."""
    cache = Path(cache)
    manifest = json.loads(FROZEN.read_text(encoding="utf-8"))
    if freeze_digest(manifest) != MANIFEST or manifest["site_commit"] != COMMIT:
        raise ValueError("frozen_manifest_mismatch")
    tokenizer = cache / context.TOKENIZER_NAME
    if not tokenizer.is_file() or context.get_counter(tokenizer)[1] == "local-subword-proxy-v1":
        raise ValueError("tokenizer_integrity_error")
    entries, dossiers, _ = load(Path(site), cache)
    actual = freeze(entries, dossiers)
    if set(actual["dossiers"]) != set(manifest["dossiers"]) or any(
        record[field] != manifest["dossiers"][key][field]
        for key, record in actual["dossiers"].items() for field in ("pages", "component_links")
    ):
        raise ValueError("frozen_site_scope_mismatch")
    approved = {
        (item["sha256"], item["pages"], item["bytes"], encoded(link))
        for item in manifest["files"] for link in item["links"]
    }
    fields = ("id", "scope", "path", "field", "url", "final_url", "revision", "applicability", "applicability_source")
    for dossier in dossiers.values():
        for doc in dossier["included_docs"]:
            link = encoded({field: doc.get(field) for field in fields})
            if (doc["sha256"], doc["pages"], doc["bytes"], link) not in approved:
                doc["state"] = "revision_drift"
                dossier["completeness"] = "partial"
        dossier["included_docs"] = [doc for doc in dossier["included_docs"] if doc["state"] == "ready"]
    return entries, dossiers


class TrialResolver(Resolver):
    def __init__(self, entries, coverage):
        super().__init__(entries)
        self.coverage = coverage

    def resolve(self, question, active=(), hint=None):
        decision = super().resolve(question, active)
        eligible = {item["id"] for item in decision["candidates"]} & self.coverage
        if (hint in self.coverage and decision["reason"] in CHOICE_REASONS
                and (not eligible or hint in eligible)):
            return self.result("owner_selected", [hint], decision["candidates"])
        return decision


class TrialConsultant:
    """Single-owner context with a replaceable native or offline provider boundary."""
    def __init__(self, entries, dossiers, cache, native=None, *, mode="offline"):
        if mode not in {"offline", "mock", "live"} or (
            mode == "offline" and native is not None or
            mode != "offline" and (native is None or native.mode != mode)
        ):
            raise ValueError("trial_mode_mismatch")
        self.entries, self.dossiers, self.cache = entries, dossiers, Path(cache)
        self.mode, self.native = mode, native
        self._lock = RLock()
        self._session = Session(None, time.time())
        self._scope = "full"
        provider = NativeD1(self.cache, None, manifest=freeze(entries, dossiers))
        provider.dispatch = self._dispatch
        self._router = Pilot(entries, dossiers, self.cache, None, provider, context.EXTENDED, owner_dc02=True)
        self._router.resolver = TrialResolver(entries, set(dossiers))
        self.catalog = [self._catalog_item(entity, dossier) for entity, dossier in dossiers.items()]

    def _catalog_item(self, entity, dossier):
        unique = {}
        for row in dossier["included_docs"]:
            unique.setdefault(row["sha256"], {key: row[key] for key in ("url", "sha256", "pages")})
        docs = list(unique.values())
        return dict(id=entity, label=self.entries[entity]["title"],
                    url=self.entries[entity].get("production_url", self.entries[entity]["canonical"]),
                    pages=sum(row["pages"] for row in docs), pdf_count=len(docs), documents=docs,
                    limitations=[OUTSIDE] if any(row["state"] != "ready"
                                                 for row in dossier["docs"] + dossier["issues"]) else [])

    def reset(self):
        with self._lock:
            self._session = Session(None, time.time())

    def accepts_text(self, text):
        if not isinstance(text, str) or any(0xD800 <= ord(char) <= 0xDFFF for char in text):
            return False
        normalized = unquote(unquote(text))
        return not PRIVATE.search(normalized) and (
            self.native is None or not self.native.contains_secret(normalized))

    def ask(self, question, *, hint=None, request_id=None, scope="full"):
        request_id = request_id or uuid4().hex
        if (not isinstance(question, str) or not question.strip() or len(question) > 1200
                or not isinstance(request_id, str) or not REQUEST.fullmatch(request_id)
                or scope not in ("full", "manual") or hint is not None and (
                    not isinstance(hint, str) or hint not in self.dossiers)):
            return self._result("invalid_request", "", {})
        if (not self.accepts_text(question) or OVERRIDE.search(question) or HOSTILE.search(question)
                or re.search(r"https?://", question, re.I)):
            return self._result("domain_denied", "", {})
        with self._lock:
            self._scope = scope
            result = self._router.complete(self._session, "trial/" + request_id, question, hint, "D1", time.time())
            if result["status"] == "trial_evidence":
                safe = result["context"]["answer"]
                if self._session.history:
                    rendered = safe["expert"]["B"]
                    verified = [row["text"] for field in ("verified_facts", "documented_actions")
                                for row in rendered.get(field, ()) if row.get("text")]
                    if verified:
                        self._session.history[-1]["verified"] = verified
            else:
                selected = result.get("decision", {}).get("candidates", [])
                safe = self._result(result["status"], question, {},
                                    choices=[item["id"] for item in selected])
            if result.get("document_diagnostics"):
                limitations = safe["public"]["limitations"]
                if OUTSIDE not in limitations:
                    limitations.append(OUTSIDE)
                safe["expert"]["limitations"] = limitations.copy()
            return safe

    def _result(self, status, question, provenance, *, candidate=None, verified=None, telemetry=None,
                private_values=(), documents=(), limits=(), choices=()):
        mode = {"mock": "mock_native", "live": "live_native", "offline": "preflight"}[self.mode]
        provenance = dict(prompt_version=FUTURE_PROMPT_VERSION, request_mode=mode, provider_model="deepseek-flash",
                          site_commit=COMMIT, manifest_sha256=MANIFEST) | provenance
        expert = build_report(question=question, provenance=provenance, candidate=candidate, result=verified,
                              telemetry={"private_values": private_values})
        b = expert["B"]
        if not b.get("answer"):
            b["answer"] = MESSAGES.get(status, "Подтверждённый ответ недоступен. Причина указана в журнале.")
        expert.update(mode=self.mode, status=status, documents=list(documents), limitations=list(limits), telemetry=(telemetry or {"provider": "unavailable"})
                      | {"usage_panel": USAGE_PANEL})
        public = dict(status=status, answer=b["answer"],
                      citations=[row for row in b.get("citations", []) if row.get("url")],
                      unresolved=b.get("unresolved", []), limitations=list(limits),
                      choices=[dict(id=item["id"], label=item["label"]) for item in self.catalog
                               if item["id"] in choices or not choices and status == "clarification"],
                      scope_options=[CAP_SCOPE] if status == "over_cap" and self._scope == "full" else [])
        return dict(public=public, expert=expert)

    def _dispatch(self, request, question, pages, docs, history, _now, cap):
        start = time.monotonic()
        selected = {entity for page in pages for entity in page["scope"]}
        expected = Counter((row["scope"], row["id"]) for entity in selected
                           for row in self.dossiers[entity]["included_docs"])
        limits = [OMITTED] if Counter((row["scope"], row["id"]) for row in docs) != expected else []
        if self._scope == "manual":
            limits.append(NARROWED)
            docs = [row for row in docs if row["scope"] in PIN and row["sha256"] == PIN[row["scope"]][0]]
        verified_docs = []
        failed = set()
        try:
            counter, _ = context.get_counter(self.cache / context.TOKENIZER_NAME)
            for row in docs:
                sha = row["sha256"]
                if sha not in failed:
                    try:
                        context.pdf_size(self.cache / (sha + ".pdf"), row["pages"], counter)
                    except (OSError, ValueError, subprocess.SubprocessError):
                        failed.add(sha)
                        continue
                    verified_docs.append(row)
        except (OSError, ValueError):
            verified_docs = []
            failed = {row["sha256"] for row in docs}
        if failed:
            limits.append(OMITTED)
        if self._scope == "manual" and set(row["scope"] for row in verified_docs) != selected:
            return "trial_evidence", None, {"answer": self._result(
                "incomplete_dossier", question, {}, limits=tuple(dict.fromkeys(limits)))}
        request_key = request.rsplit("/", 1)[-1]
        registry, wire, payload, site, unique = build_request(
            request_key, question, history, pages, verified_docs, self.entries, MANIFEST,
            prompt_version=FUTURE_PROMPT_VERSION)
        provenance = dict(source_registry=registry.sources, source_registry_sha256=registry.wire_identity,
                          logical_wire_sha256=wire, logical_payload_sha256=digest(encoded(payload).encode()),
                          ordered_pdf_sha256=list(unique),
                          dossier=dict(pdf_count=len(unique), page_count=sum(unique.values())))
        documents = [dict(source=source_id, sha256=source.sha256, pages=source.pages, url=source.url,
                          kind=source.kind, revision=source.revision)
                     for source_id, source in registry.sources.items()]

        def outcome(status, **details):
            return "trial_evidence", None, {"answer": self._result(
                status, question, provenance, documents=documents, limits=tuple(dict.fromkeys(limits)), **details)}

        if len(unique) > context.FILE_LIMIT or sum(unique.values()) > OWNER["pages"]:
            return outcome("over_cap")
        try:
            sizing = measure(payload, unique, self.cache)
        except (OSError, ValueError, subprocess.SubprocessError):
            return outcome("sizing_unavailable")
        local = dict(local_tokens=sizing["estimate"], input_mode=sizing["input_mode"],
                     estimated_micro_usd=sizing["estimated_cold_micro_usd"], verified_billable_bound=None)
        if sizing["estimate"] > cap or sizing["local_text_bytes"] > PARSED_BYTES_LIMIT:
            return outcome("over_cap", telemetry=local)
        if self.native is None:
            return outcome("offline", telemetry=local | {"provider": "offline"})
        try:
            reply = self.native.dispatch(payload, unique, request_key, sizing)
        except (OSError, ValueError):
            return outcome("provider_unknown", telemetry=local | {"provider": "operation_state_unavailable"})
        telemetry = local | reply.telemetry
        candidate = reply.content
        if reply.status == "completed_usage_unknown":
            limits.append("Начисление по этому ответу неизвестно. Новые платные операции приостановлены.")
        if reply.status not in {"completed", "completed_usage_unknown"} or candidate is None:
            return outcome(reply.status, telemetry=telemetry, candidate=candidate,
                           private_values=reply.private_values)
        verify_start = time.monotonic()
        verified = verify_reply(candidate, registry, wire, site, unique, self.cache)
        telemetry.update(verification_ms=round((time.monotonic() - verify_start) * 1000),
                         total_ms=round((time.monotonic() - start) * 1000))
        return outcome(verified["status"], telemetry=telemetry, candidate=candidate, verified=verified,
                       private_values=reply.private_values)
