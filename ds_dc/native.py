"""DeepSeek Files and Chat Completions at an injectable HTTP boundary."""
from hashlib import sha256
import json
import re
import time

import httpx

from .context import EXTENDED, FILE_LIMIT, NORMAL, OUTPUT, TOKENIZER_NAME, get_counter, size, wire
from .corpus import MAX_SIZE, digest, encoded
from .finance import Ledger, OWNER, RATES, Stopped, cold_cost, token_cost
from .provider_failure import ProviderFailure, transport_failure
from .recovery import ORIGINAL_UPLOAD, RECOVERY_CHAT, matching_event
from .runtime import PURPOSE, abstention, verify

ORIGIN = "https://api.deepseek.com"
MAX_FILE_ID_SUFFIX = 128
FILE_ID = re.compile(rf"file-api-[A-Za-z0-9_-]{{1,{MAX_FILE_ID_SUFFIX}}}")
SHA = re.compile(r"[0-9a-f]{64}")
MODEL_CONTEXT = 1_048_576
PARSE_TTL = 3600
STATUS_INTERVAL = 300
CHAT_TIMEOUT = 150
UPLOAD_TIMEOUT = 250
PAGE_PRICE = int(RATES["page"])
PARSED_BYTES_LIMIT = 8 * 1024 * 1024
# Admission requires recorded Architecture review in the exact, approved code revision.
# Current provider documentation does not establish a billable bound for any pilot wire.
REVIEWED_BOUNDS = {}

CONTROLLED_CAL = "controlled_calibration"
CAL_MANIFEST = "13fd98159f05809c019dd11a522b1c87fff3faebc505621bde7318880e3051f9"
CAL_POST_RESERVE = 330_000
CAL_WIRES = {
    "Q01": ("7498d9920faf9cf25dfbf461c0bc64a75701089423a1c142c1b45cb85e9b9afd", 4, 80),
    "Q02": ("d6c1ac408cf46c62c1f653a222c4e5af54d07fbc9981f65c21bb622b55303513", 10, 403),
}


def controlled_permit(go):
    cal_id = go.get("cal_id")
    if (not isinstance(cal_id, str) or cal_id not in CAL_WIRES
            or go.get("accepted_residual_risk") is not True
            or go["manifest_sha"] != CAL_MANIFEST):
        return False
    wire_sha, uploads, pages = CAL_WIRES[cal_id]
    prior = go.get("cal01_permit_sha")
    recovery_sha = go.get("recovery_authorization_sha")
    if recovery_sha is not None and (not isinstance(recovery_sha, str) or not SHA.fullmatch(recovery_sha)):
        return False
    return (go.get("wire_sha256") == wire_sha
            and (prior is None if cal_id == "Q01" else isinstance(prior, str) and bool(SHA.fullmatch(prior)))
            and go["limits"] == dict(budget=CAL_POST_RESERVE + pages * PAGE_PRICE,
                normal=0, extended=1, chats=1, pages=pages, upload=uploads,
                status=0, delete=0, calibration=1))


class ProviderObject(dict):
    def __init__(self, content, status):
        super().__init__(content)
        self.http_status = status


def safe_http_error_code(response):
    # The public error reference documents numeric HTTP categories. Accept only the
    # matching documented number from an optional, small JSON error envelope.
    if response.status_code not in {400, 401, 402, 408, 413, 422, 429, 500, 503, 504}:
        return None
    mime = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if mime != "application/json":
        return None
    try:
        raw = bytearray()
        for chunk in response.iter_bytes():
            if len(raw) + len(chunk) > 4096:
                return None
            raw.extend(chunk)
        code = json.loads(raw)["error"]["code"]
    except (httpx.RequestError, KeyError, TypeError, ValueError, RecursionError):
        return None
    expected = str(response.status_code)
    if type(code) in (str, int) and str(code) == expected:
        return expected
    return None


def wire_identity(question, pages, docs, history):
    placeholders = {sha: "file-api-placeholder" for sha in sorted({d["sha256"] for d in docs})}
    return digest(encoded(wire(question, pages, docs, placeholders, history)).encode())


def wire_approval(question, pages, docs, history):
    longest_handles = {
        sha: "file-api-" + "x" * MAX_FILE_ID_SUFFIX for sha in sorted({d["sha256"] for d in docs})}
    return dict(wire_sha256_without_handles=wire_identity(question, pages, docs, history),
                scope_wire_sha256_without_handles=wire_identity("", pages, docs, []),
                max_wire_bytes=len(encoded(wire(question, pages, docs, longest_handles, history)).encode()))


class NativeD1:
    def __init__(self, cache, ledger: Ledger, *, manifest, fixture=None, live=None):
        self.cache = cache
        self.ledger = ledger
        self.manifest = manifest
        self.manifest_sha = digest(encoded(manifest).encode())
        self.approved = {d["sha256"]: d["pages"] for d in manifest["files"]}
        self.chat_posts = 0
        self.fixture = fixture
        self.live = live
        self.limits = OWNER
        self.run = "prep"
        self.campaign = None
        self.principal = "fixture"
        self.permit_sha = self.manifest_sha
        self.account = "fixture"
        self.project = "prep"
        if live:
            if fixture is not None:
                raise ValueError("fixture_and_live_conflict")
            go, head, key, contract = live
            limits = go["limits"]
            contract_sha = digest(encoded(contract).encode())
            if (not key or not SHA.fullmatch(go["manifest_sha"]) or not re.fullmatch(r"[a-f0-9]{40}", head)
                    or go["manifest_sha"] != self.manifest_sha or go["head"] != head or go["rates"] != RATES
                    or go["contract_sha"] != contract_sha or contract["rates"] != RATES
                    or contract["model"] != "DeepSeek-V4.1-Flash-1017"
                    or contract["origin"] != ORIGIN or contract["model_context_max"] != MODEL_CONTEXT
                    or contract["generation_max"] != OUTPUT or contract["parser"] != PURPOSE
                    or type(contract["reviewed_at"]) is not int
                    or not time.time() - 86400 <= contract["reviewed_at"] <= time.time()
                    or not isinstance(contract["reviewer"], str) or not contract["reviewer"].strip()
                    or not isinstance(contract["rates_evidence"], str)
                    or not contract["rates_evidence"].startswith("https://api-docs.deepseek.com/")
                    or not isinstance(contract["approved_bound_ids"], list)
                    or not all(isinstance(value, str) and SHA.fullmatch(value)
                               for value in contract["approved_bound_ids"])
                    or not isinstance(contract["paid_operation_evidence"], str)
                    or not contract["paid_operation_evidence"].startswith("https://api-docs.deepseek.com/")
                    or go["kind"] not in {"regular", "calibration", "cleanup", CONTROLLED_CAL}
                    or type(go["expires"]) is not int or go["expires"] <= time.time()
                    or go["ledger_path"] != str(self.ledger.path.resolve())
                    or not all(isinstance(go[name], str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", go[name])
                               for name in ("run", "account", "project"))
                    or go["run"] == "prep" or go["key_sha256"] != sha256(key.encode()).hexdigest()
                    or set(limits) != set(OWNER) - {"reserve_disabled"}
                    or any(type(n) is not int or not 0 <= n <= OWNER[k] for k, n in limits.items())
                    or type(go["expires"]) is not int or go["expires"] > contract["reviewed_at"] + 86400
                    or (go["kind"] == "regular" and limits["calibration"])
                    or (go["kind"] == CONTROLLED_CAL and not controlled_permit(go))
                    or (go["kind"] != "cleanup" and limits["delete"])
                    or (go["kind"] == "cleanup" and (go.get("cleanup_sha") not in self.approved
                        or limits["delete"] != 1
                        or any(value for name, value in limits.items() if name != "delete")))):
                raise ValueError("invalid_live_go")
            self.run = go["run"]
            self.campaign = "dc02-live"
            self.limits = limits
            self.permit_sha = digest(encoded(go).encode())
            self.account = go["account"]
            self.project = go["project"]
            self.principal = go["key_sha256"]

    def now(self, fallback):
        return time.time() if self.live else fallback

    def check_go(self):
        if self.live and self.live[0]["expires"] <= time.time():
            raise Stopped("go_expired")
        if not self.live and self.fixture is None:
            raise Stopped("live_disabled")

    def send(self, method, route, *, payload=None, data=None, files=None, timeout=30):
        self.check_go()
        allowed = ((method == "POST" and route in {"/files", "/chat/completions"})
                   or (method in {"GET", "DELETE"} and route.startswith("/files/")
                       and FILE_ID.fullmatch(route.removeprefix("/files/"))))
        if not allowed:
            raise ValueError("unknown_provider_operation")
        transport = self.fixture if self.fixture is not None else httpx.HTTPTransport(retries=0)
        key = self.live[2] if self.live else "fixture"
        stage, status = "transport", None
        try:
            with httpx.Client(base_url=ORIGIN, transport=transport, trust_env=False, follow_redirects=False,
                              timeout=httpx.Timeout(timeout, connect=8)) as client:
                with client.stream(method, route, headers={"Authorization": "Bearer " + key},
                                   json=payload, data=data, files=files) as response:
                    status = response.status_code
                    if not response.is_success:
                        raise ProviderFailure("http_status", "http_error", exception_class="HTTPStatusError",
                                              http_status=status, provider_code=safe_http_error_code(response))
                    stage = "response_read"
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > 2_000_000:
                            raise ProviderFailure(stage, "response_too_large", http_status=status)
        except httpx.RequestError as error:
            raise transport_failure(error, stage, status) from None
        try:
            result = json.loads(raw)
        except (ValueError, RecursionError):
            raise ProviderFailure("json_decode", "invalid_json", exception_class="JSONDecodeError",
                                  http_status=status) from None
        if not isinstance(result, dict):
            raise ProviderFailure("response_schema_validation", "expected_object", http_status=status)
        return ProviderObject(result, status)

    def bound(self, approval):
        if not self.live:
            return None
        permit, _, _, contract = self.live
        calibration = permit["kind"] == "calibration"
        exact = approval["wire_sha256_without_handles"]
        scope = approval["scope_wire_sha256_without_handles"]
        kind = "provider_billable_maximum" if calibration else "complete_input_bound"
        choices = [(exact, kind, "request_sha256")]
        if not calibration:
            choices.append((scope, "complete_scope_bound", "scope_sha256"))
        for identity, kind, identity_field in choices:
            if identity not in contract["approved_bound_ids"]:
                continue
            record = REVIEWED_BOUNDS.get((identity, kind))
            if (not isinstance(record, dict) or record.get("kind") != kind
                    or record.get(identity_field) != identity
                    or record.get("manifest_sha256") != self.manifest_sha
                    or type(record.get("billable_input")) is not int
                    or not 0 < record["billable_input"] <= MODEL_CONTEXT - OUTPUT
                    or type(record.get("parsed_bytes_max")) is not int
                    or not 0 <= record["parsed_bytes_max"] <= PARSED_BYTES_LIMIT
                    or not isinstance(record.get("evidence_url"), str)
                    or not record["evidence_url"].startswith("https://api-docs.deepseek.com/")
                    or not isinstance(record.get("derivation"), str) or not record["derivation"].strip()):
                continue
            if kind == "complete_scope_bound" and (type(record.get("wire_bytes_max")) is not int
                    or approval["max_wire_bytes"] > record["wire_bytes_max"]):
                continue
            bound = record["billable_input"]
            if not calibration and bound > EXTENDED:
                raise Stopped("over_cap")
            return bound
        raise Stopped("native_bound_unverified")

    def file_key(self, sha):
        return digest(encoded([self.account, self.project, self.principal, PURPOSE, PURPOSE, sha]).encode())

    def file_snapshot(self, result, sha, raw_length, now):
        stage = "file_metadata_validation"
        fields = {"id": str, "object": str, "purpose": str, "filename": str,
                  "bytes": int, "created_at": int, "expires_at": int}
        for field, kind in fields.items():
            if field not in result:
                raise ProviderFailure(stage, field + "_missing")
            if type(result[field]) is not kind:
                raise ProviderFailure(stage, field + "_type")
        handle, created, expires = result["id"], result["created_at"], result["expires_at"]
        checks = {
            "id_format": FILE_ID.fullmatch(handle),
            "object_mismatch": result["object"] == "file",
            "purpose_mismatch": result["purpose"] == PURPOSE,
            "filename_mismatch": result["filename"] == sha + ".pdf",
            "bytes_mismatch": result["bytes"] == raw_length,
            "created_at_future": created <= now + 30,
            "expires_at_elapsed": expires > now,
            "ttl_mismatch": expires - created == PARSE_TTL,
        }
        for reason, valid in checks.items():
            if not valid:
                raise ProviderFailure(stage, reason)
        return dict(id=handle, sha256=sha, bytes=raw_length, expires=expires,
                    checked=now, created=created, account=self.account,
                    project=self.project, purpose=PURPOSE, parser=PURPOSE)

    def upload(self, state, key, sha, raw, now, pages):
        def call():
            try:
                return self.send("POST", "/files", data={"purpose": PURPOSE,
                    "expires_after[anchor]": "created_at", "expires_after[seconds]": str(PARSE_TTL)},
                    files={"file": (sha + ".pdf", raw, "application/pdf")}, timeout=UPLOAD_TIMEOUT)
            except ProviderFailure as error:
                if self.controlled or error.http_status != 413 or error.stage != "http_status":
                    raise
                return error

        def parse(result):
            if isinstance(result, ProviderFailure):
                return 0, {"upload_rejected": self.file_key(sha), "provider_failure": result.diagnostic(
                    "upload", 0, financial_outcome_unknown=False)}
            snapshot = self.file_snapshot(result, sha, len(raw), self.now(now))
            if any(b["id"] == snapshot["id"] and b["sha256"] != sha for b in state["bindings"].values()):
                raise ProviderFailure("file_metadata_validation", "id_collision")
            state["bindings"][self.file_key(sha)] = snapshot
            return pages * PAGE_PRICE, {}

        return not isinstance(self.ledger.operate(state, key, call, parse), ProviderFailure)

    def status(self, state, key, binding, now):
        def parse(result):
            fresh = self.file_snapshot(result, binding["sha256"], binding["bytes"], self.now(now))
            if any(fresh[field] != binding[field] for field in ("id", "created", "expires")):
                field = next(field for field in ("id", "created", "expires") if fresh[field] != binding[field])
                reason = {"id": "id_changed", "created": "created_at_changed", "expires": "expires_at_changed"}
                raise ProviderFailure("file_metadata_validation", reason[field])
            binding["checked"] = fresh["checked"]
            return 0, {}

        self.ledger.operate(state, key, lambda: self.send("GET", "/files/" + binding["id"]), parse)

    def cleanup(self, sha, now):
        """Operator only. The transaction excludes consumers during acknowledgement."""
        self.check_go()
        if self.live:
            permit = self.live[0]
            if permit["kind"] != "cleanup" or permit["cleanup_sha"] != sha:
                raise Stopped("cleanup_not_authorized")
        if sha not in self.approved:
            raise Stopped("binding_unavailable")
        now = self.now(now)
        with self.ledger.transaction() as state:
            binding = self.binding(state, sha)
            if not binding or binding["expires"] <= now:
                raise Stopped("binding_unavailable")
            k = self.run + "/delete/" + sha + "/" + digest(binding["id"].encode())

            def parse(result):
                if (result.get("id") != binding["id"] or result.get("object") != "file"
                        or result.get("deleted") is not True):
                    raise ValueError("unconfirmed_delete")
                del state["bindings"][self.file_key(sha)]
                return 0, {"delete_acknowledged": True}

            self.ledger.reserve(state, self.run, self.permit_sha, "owner", now, self.limits,
                                {k: dict(kind="delete", reserve=0)}, campaign=self.campaign)
            self.ledger.operate(state, k, lambda: self.send("DELETE", "/files/" + binding["id"]), parse)

    def binding(self, state, sha):
        binding = state["bindings"].get(self.file_key(sha))
        if binding and (binding["account"] != self.account or binding["project"] != self.project
                        or binding["sha256"] != sha or binding["purpose"] != PURPOSE
                        or binding["parser"] != PURPOSE or not FILE_ID.fullmatch(binding["id"])):
            raise Stopped("binding_unavailable")
        return binding

    @property
    def controlled(self):
        return self.live is not None and self.live[0]["kind"] == CONTROLLED_CAL

    @property
    def calibration(self):
        return self.live is not None and self.live[0]["kind"] in {"calibration", CONTROLLED_CAL}

    def controlled_admission(self, approval, context):
        permit = self.live[0]
        wire_sha, uploads, pages = CAL_WIRES[permit["cal_id"]]
        if (approval["wire_sha256_without_handles"] != wire_sha
                or context["unique_files"] != uploads or context["physical_pages"] != pages):
            raise Stopped("calibration_wire_mismatch")

    def controlled_receipt(self, value, question, pages, docs, context, chat_ms):
        choices = value["choices"]
        if len(choices) != 1:
            raise ValueError("invalid_calibration_response")
        choice = choices[0]
        finish = choice.get("finish_reason")
        if finish not in ("stop", "length", "content_filter", "tool_calls",
                          "insufficient_system_resource", "aborted"):
            finish = "unknown"
        raw = choice["message"].get("content")
        raw = raw if isinstance(raw, str) else None
        draft = None
        status, diagnostics = "invalid_candidate", []
        if raw is not None:
            raw = FILE_ID.sub("[redacted file handle]", raw.replace(self.live[2], "[redacted credential]"))
            try:
                raw.encode("utf-8")
                draft = json.loads(raw)
                serialized = encoded(draft)
                serialized.encode("utf-8")
                if FILE_ID.search(serialized) or self.live[2] in serialized:
                    raw, draft = None, None
            except UnicodeError:
                raw, draft = None, None
            except (ValueError, RecursionError):
                draft = None
        if draft is not None:
            status, diagnostics = verify(draft, question, docs, self.cache, pages=pages, dc02=True)
        receipt = dict(finish_reason=finish, raw_draft=raw, candidate=draft, question=question,
                       verification_status=status, diagnostics=diagnostics, documents=docs,
                       site=[{k: v for k, v in page.items() if k != "raw"} for page in pages],
                       estimate=context["estimate"], wire_sha256=self.live[0]["wire_sha256"],
                       upload_latency_ms=context["upload_latency_ms"], chat_latency_ms=chat_ms)
        return receipt

    def dispatch(self, request, question, pages, documents, history, now, cap=None):
        """Compact the caller's working copy of the dialogue before sizing and sending."""
        if self.live and self.live[0]["kind"] == "cleanup":
            return "live_disabled", None, {}
        if self.calibration:
            history = []
        context = size(question, pages, documents, history, self.cache)
        if context["unique_files"] > FILE_LIMIT:
            return "provider_file_limit", None, context
        # Only resolved user turns can be compacted. Preserve unresolved turns and their order.
        original_turns = len(history)
        while context["estimate"] > min(cap if cap is not None else EXTENDED, EXTENDED):
            removable = next((i for i, turn in enumerate(history) if not turn.get("unresolved")), None)
            if removable is None:
                break
            history.pop(removable)
            context = size(question, pages, documents, history, self.cache)
        context["compacted_turns"] = original_turns - len(history)
        approval = wire_approval(question, pages, documents, history)
        context.update(approval)
        if (context["estimate"] > (cap if cap is not None else EXTENDED)
                and not self.live):
            return "over_cap", None, context
        try:
            self.check_go()
            if self.controlled:
                self.controlled_admission(approval, context)
            bound = None if self.controlled else self.bound(approval)
            context["verified_upper_bound"] = bound
            effective = bound if bound is not None else context["estimate"]
            mode = ("calibration" if self.calibration
                    else "normal" if effective <= NORMAL else "extended")
            context["input_mode"] = mode
            context["provider"] = "live" if self.live else "http_fixture"
            started = time.monotonic()
            with self.ledger.transaction() as state:
                try:
                    result = self.turn(state, request, question, pages, documents, history,
                                       now, mode, bound, context)
                finally:
                    for row in reversed(tuple(state["operations"].values())):
                        if row.get("run") == self.run and "provider_failure" in row:
                            context["provider_failure"] = row["provider_failure"]
                            break
                    context["budget"] = self.ledger.summary(state, self.run, self.limits["budget"])
                    if self.campaign:
                        context["campaign_budget"] = self.ledger.summary(
                            state, self.run, OWNER["budget"], self.campaign)
                    context["latency_ms"] = round((time.monotonic() - started) * 1000)
            return *result, context
        except Stopped as exc:
            return str(exc), None, context

    def calibration_scope(self):
        return digest(encoded([self.account, self.project, self.principal, self.manifest_sha,
                               self.live[1]]).encode())

    def check_controlled_sequence(self, state, operation_key):
        if operation_key in state["operations"]:
            raise Stopped("duplicate_operation")
        permit = self.live[0]
        recovery_sha = permit.get("recovery_authorization_sha")
        events = None
        recovery = None
        if recovery_sha:
            events = matching_event(state, recovery_sha, permit, self.live[1])
            recovery = dict(original_operation=ORIGINAL_UPLOAD)
        if permit["cal_id"] == "Q02":
            prior_key = RECOVERY_CHAT if events else self.campaign + "/calibration/" + CAL_WIRES["Q01"][0]
            prior = state["operations"].get(prior_key, {})
            if (prior.get("state") != "settled"
                    or prior.get("permit_sha") != permit["cal01_permit_sha"]
                    or prior.get("calibration_scope") != self.calibration_scope()
                    or prior.get("calibration_result", {}).get("finish_reason") != "stop"
                    or (events and (len(events) != 2
                        or events[1].get("permit_sha") != prior["permit_sha"]))):
                raise Stopped("cal01_not_confirmed")
        elif events:
            if len(events) != 1:
                raise Stopped("recovery_already_consumed")
            recovery["consumption"] = dict(kind="consumed", authorization_sha=recovery_sha,
                                          operation=RECOVERY_CHAT, permit_sha=self.permit_sha)
        return recovery

    def turn(self, state, request, question, pages, docs, history, now, mode, bound, context):
        now = self.now(now)
        if mode == "calibration":
            question_key = self.campaign + "/calibration/" + context["wire_sha256_without_handles"]
        else:
            question_key = self.run + "/question/" + digest(request.rsplit("/", 1)[-1].encode())
        recovery = None
        if self.controlled:
            permit = self.live[0]
            if permit["cal_id"] == "Q01" and permit.get("recovery_authorization_sha"):
                question_key = RECOVERY_CHAT
            recovery = self.check_controlled_sequence(state, question_key)
        ops = {}
        uploads = {}
        references = {}
        unique = {doc["sha256"]: doc["pages"] for doc in docs}
        rejected_bindings = {row["upload_rejected"] for row in state["operations"].values()
                             if row.get("run") == self.run and "upload_rejected" in row}
        rejected = set()
        for sha, count in sorted(unique.items()):
            if self.approved.get(sha) != count:
                raise Stopped("file_manifest_mismatch")
            if self.file_key(sha) in rejected_bindings:
                rejected.add(sha)
                continue
            binding = self.binding(state, sha)
            if binding and self.controlled:
                raise Stopped("calibration_existing_binding")
            if binding and binding["expires"] > now + CHAT_TIMEOUT + 30:
                if now - binding["checked"] >= STATUS_INTERVAL:
                    key = question_key + "/status/" + sha
                    ops[key] = dict(kind="status", reserve=0)
                    references[key] = binding
                continue
            raw_path = self.cache / (sha + ".pdf")
            try:
                if raw_path.stat().st_size > MAX_SIZE:
                    raise Stopped("cache_integrity_error")
                raw = raw_path.read_bytes()
            except OSError:
                raise Stopped("cache_integrity_error") from None
            if digest(raw) != sha:
                raise Stopped("cache_integrity_error")
            key = question_key + "/upload/" + sha
            ops[key] = dict(kind="upload", reserve=count * PAGE_PRICE, pages=count)
            uploads[key] = sha, raw, count
        context["file_cache_hits"] = len(unique) - len(uploads) - len(rejected)
        billing_bound = bound or (NORMAL if mode == "normal" else EXTENDED)
        reserve = (CAL_POST_RESERVE if self.controlled else cold_cost(billing_bound) if mode == "calibration"
                   else 50_000 if mode == "normal" else 90_000)
        slot = "extended" if mode == "calibration" else mode
        ops[question_key] = dict(kind=mode, slot=slot, reserve=reserve)
        if self.controlled:
            ops[question_key].update(permit_sha=self.permit_sha, calibration_scope=self.calibration_scope())
            context["upload_latency_ms"] = {}
        self.ledger.reserve(state, self.run, self.permit_sha, "owner", now, self.limits, ops,
                            campaign=self.campaign, recovery=recovery)
        try:
            for key, (sha, raw, count) in uploads.items():
                self.check_go()
                upload_started = time.monotonic()
                try:
                    if not self.upload(state, key, sha, raw, now, count):
                        rejected.add(sha)
                finally:
                    if self.controlled:
                        elapsed = round((time.monotonic() - upload_started) * 1000)
                        context["upload_latency_ms"][sha] = elapsed
                        state["operations"][key]["latency_ms"] = elapsed
            for key, binding in references.items():
                self.check_go()
                self.status(state, key, binding, now)
            if rejected:
                context["file_omissions"] = [dict(doc_id=doc["id"], sha256=doc["sha256"],
                    scope=doc["scope"], url=doc["url"], state="provider_rejected_pdf")
                    for doc in docs if doc["sha256"] in rejected]
                docs = [doc for doc in docs if doc["sha256"] not in rejected]
                approval = wire_approval(question, pages, docs, history)
                context["outgoing_wire_sha256_without_handles"] = approval["wire_sha256_without_handles"]
                if self.calibration:
                    raise Stopped("calibration_wire_changed")
                if self.live:
                    narrowed_bound = self.bound(approval)
                    if narrowed_bound > billing_bound:
                        raise Stopped("native_bound_changed")
                    billing_bound = narrowed_bound
                    context["verified_upper_bound"] = billing_bound
            bindings = {sha: self.binding(state, sha) for sha in sorted(set(unique) - rejected)}
            if any(item["expires"] <= self.now(now) + CHAT_TIMEOUT for item in bindings.values()):
                raise Stopped("binding_expiry_before_chat")
            payload = wire(question, pages, docs, {s: b["id"] for s, b in bindings.items()}, history)
            self.check_go()

            def chat():
                self.chat_posts += 1
                chat_started = time.monotonic()
                try:
                    return self.send("POST", "/chat/completions", payload=payload, timeout=CHAT_TIMEOUT)
                finally:
                    if self.controlled:
                        state["operations"][question_key]["latency_ms"] = round(
                            (time.monotonic() - chat_started) * 1000)

            def account(result):
                receipt = None
                if self.controlled:
                    row = state["operations"][question_key]
                    receipt = self.controlled_receipt(result, question, pages, docs, context, row["latency_ms"])
                    context["finish_reason"] = receipt["finish_reason"]
                usage = result.get("usage")
                if not isinstance(usage, dict):
                    raise ProviderFailure("financial_accounting", "usage_missing_or_invalid")
                if (result["model"] != "deepseek-flash" or usage.get("server_tool_use")
                        or any(choice.get("message", {}).get("server_tool_calls")
                               or choice.get("message", {}).get("tool_calls")
                               for choice in result.get("choices", []))):
                    raise ProviderFailure("response_schema_validation", "provider_contract_drift")
                keys = ("prompt_tokens", "completion_tokens", "total_tokens",
                        "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")
                counts = {k: usage.get(k) for k in keys}
                if any(type(v) is not int or v < 0 for v in counts.values()):
                    raise ProviderFailure("financial_accounting", "incomplete_usage")
                prompt, output, total, hit, miss = (counts[k] for k in keys)
                if total != prompt + output or prompt != hit + miss:
                    raise ProviderFailure("financial_accounting", "incomplete_usage")
                details = usage.get("completion_tokens_details") or {}
                if "reasoning_tokens" in details:
                    reasoning = details["reasoning_tokens"]
                    if type(reasoning) is not int or not 0 <= reasoning <= output:
                        raise ProviderFailure("financial_accounting", "invalid_reasoning_usage")
                    counts["reasoning_tokens"] = reasoning
                context["observed_usage"] = counts
                cost = token_cost(prompt, hit, output)
                if not self.controlled:
                    return cost, dict(usage=counts, overage=prompt > billing_bound or output > OUTPUT)
                hold_reason = None
                if self.live[0]["expires"] <= time.time():
                    hold_reason = "go_expired"
                elif receipt["finish_reason"] != "stop":
                    hold_reason = "calibration_finish_not_stop"
                return cost, dict(usage=counts, calibration_result=receipt, hold_reason=hold_reason,
                                  overage=total > MODEL_CONTEXT or output > OUTPUT)

            result = self.ledger.operate(state, question_key, chat, account)
        finally:
            self.ledger.cancel_unstarted(state, ops)
        try:
            if result["model"] != "deepseek-flash" or len(result["choices"]) != 1:
                return "invalid_candidate", None
            choice = result["choices"][0]
            context["finish_reason"] = choice["finish_reason"]
            if mode == "calibration":
                return "calibration_observed", None
            if choice["finish_reason"] != "stop":
                return "truncated_candidate" if choice["finish_reason"] == "length" else "invalid_candidate", None
            message = choice["message"]
            content = message["content"]
            candidate = json.loads(content)
            serialized = encoded(candidate)
            serialized.encode("utf-8")
            if FILE_ID.search(serialized) or (self.live and self.live[2] in serialized):
                return "invalid_candidate", None
            if isinstance(candidate, dict) and isinstance(candidate.get("answer_candidate"), str):
                count, _ = get_counter(self.cache / TOKENIZER_NAME)
                visible = count(candidate["answer_candidate"])
                context["visible_tokens_estimate"] = visible
                if visible > 1200:
                    return "candidate_too_long", None
            return "candidate", candidate
        except (ValueError, TypeError, KeyError, IndexError):
            return "invalid_candidate", None


def mock_transport():
    """Deterministic HTTP fixture. Local question and uploaded bytes are real."""
    files = {}

    def handle(request):
        route = request.url.path
        if route == "/files" and request.method == "POST":
            from email.parser import BytesParser
            from email.policy import default
            raw = request.read()
            parts = BytesParser(policy=default).parsebytes(
                b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + raw)
            binary = list(parts.iter_parts())[-1]
            content = binary.get_payload(decode=True)
            name = binary.get_filename()
            file_id = "file-api-" + digest(content)
            now = int(time.time())
            files[file_id] = dict(id=file_id, object="file", bytes=len(content),
                                  created_at=now, expires_at=now + PARSE_TTL, purpose=PURPOSE,
                                  filename=name)
            return httpx.Response(200, json=files[file_id])
        if route.startswith("/files/"):
            file_id = route.rsplit("/", 1)[-1]
            if file_id not in files:
                return httpx.Response(404)
            if request.method == "DELETE":
                del files[file_id]
                return httpx.Response(200, json=dict(id=file_id, object="file", deleted=True))
            return httpx.Response(200, json=files[file_id])
        if route != "/chat/completions" or request.method != "POST":
            return httpx.Response(404)
        answer = abstention(json.loads(request.read()))
        return httpx.Response(200, json=dict(model="deepseek-flash",
            choices=[dict(finish_reason="stop", message=dict(content=encoded(answer)))],
            usage=dict(prompt_tokens=1000, completion_tokens=100, total_tokens=1100,
                       prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=1000)))

    return httpx.MockTransport(handle)
