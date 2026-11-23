"""DeepSeek Files and Chat for the owner trial, with independent private accounting."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
import fcntl
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from urllib.parse import unquote
from uuid import uuid4

import httpx

from .context import EXTENDED, FILE_LIMIT, OUTPUT
from .corpus import MAX_SIZE, digest, encoded
from .dc04b import unique_fields
from .evidence_answer import strict_json
from .evidence_integration import FUTURE_PROMPT_VERSION, PROMPTS
from .finance import Ledger, cold_cost, token_cost
from .native import (CHAT_TIMEOUT, FILE_ID, MODEL_CONTEXT, ORIGIN, PAGE_PRICE, PARSE_TTL,
                     SHA, UPLOAD_TIMEOUT, NativeD1, ProviderObject, safe_http_error_code)
from .pdf_policy import MAX_PAGES
from .provider_failure import ProviderFailure, transport_failure
from .runtime import PURPOSE

MODEL = "deepseek-flash"
# Use the protocol context capacity at the peak uncached rate plus our full output
# cap. This is an operational reserve under the reviewed contract, not a price quote.
CHAT_RESERVE = cold_cost(MODEL_CONTEXT)
STATE_FILE = "owner-trial-native.json"
FINISH_REASONS = {"stop", "length", "content_filter", "tool_calls", "insufficient_system_resource", "aborted"}
USAGE_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens",
              "prompt_cache_hit_tokens", "prompt_cache_miss_tokens")


@dataclass(frozen=True)
class TrialReply:
    status: str
    content: bytes | None = field(default=None, repr=False)
    telemetry: dict = field(default_factory=dict)
    private_values: tuple[str, ...] = field(default=(), repr=False)


class NativeStateError(ValueError):
    """Expected private-state error before a new payment can be authorized."""


def _check_state_files(directory):
    if (directory / "ledger.json").is_symlink() or (directory / "ledger.json").exists():
        raise NativeStateError("historical_ledger_directory")
    for path, kind in ((directory, stat.S_ISDIR), (directory / STATE_FILE, stat.S_ISREG),
                       (directory / ".lock", stat.S_ISREG)):
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        if not kind(mode) or stat.S_IMODE(mode) & 0o077:
            raise NativeStateError("native_state_must_be_private")


def _check_state(state):
    if (not isinstance(state, dict) or type(state.get("version")) is not int or state["version"] != 1
            or not isinstance(state.get("requests"), dict) or not isinstance(state.get("bindings"), dict)):
        raise NativeStateError("native_state_invalid")
    for row in state["requests"].values():
        if (not isinstance(row, dict) or not isinstance(row.get("operations"), list)
                or not isinstance(row.get("session"), str) or not isinstance(row.get("status"), str)):
            raise NativeStateError("native_state_invalid")
        for op in row["operations"]:
            if (not isinstance(op, dict) or not isinstance(op.get("state"), str) or op["state"] not in
                    {"reserved", "inflight", "settled", "unknown", "cancelled"}
                    or type(op.get("reserve")) is not int or op["reserve"] < 0
                    or (op["state"] == "settled" and (type(op.get("cost")) is not int
                        or not 0 <= op["cost"] <= op["reserve"]))):
                raise NativeStateError("native_state_invalid")


def _reject_json_constant(_):
    raise ValueError("non_json_constant")


def _read_state(directory):
    _check_state_files(directory)
    try:
        state = json.loads((directory / STATE_FILE).read_text(encoding="utf-8"), object_pairs_hook=unique_fields,
                           parse_constant=_reject_json_constant)
    except FileNotFoundError:
        state = dict(version=1, requests={}, bindings={})
    except (ValueError, RecursionError):
        raise NativeStateError("native_state_invalid") from None
    _check_state(state)
    return state


class _TrialLedger(Ledger):
    def __init__(self, directory):
        _check_state_files(directory)
        super().__init__(directory)
        self.file = directory / STATE_FILE

    @contextmanager
    def transaction(self):
        _check_state_files(self.path)
        descriptor = os.open(self.path / ".lock", os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "ab") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield _read_state(self.path)


def _recover(state):
    changed = False
    for row in state["requests"].values():
        if row["status"] != "inflight":
            continue
        for op in row["operations"]:
            if op["state"] == "inflight":
                op["state"] = "unknown"
            elif op["state"] == "reserved":
                op["state"] = "cancelled"
        row["status"] = "provider_unknown" if any(op["state"] == "unknown" for op in row["operations"]) else "interrupted"
        changed = True
    return changed


def _amounts(operations):
    known = sum(op["cost"] for op in operations if op["state"] == "settled")
    held = sum(op["reserve"] for op in operations if op["state"] in {"reserved", "inflight", "unknown"})
    return known, held


def _inspect_chat(value, observed):
    if "error" in value or value.get("object") != "chat.completion":
        raise ProviderFailure("response_schema_validation", "unexpected_envelope")
    if value.get("model") != MODEL:
        observed["observed_model"] = "other" if isinstance(value.get("model"), str) else None
        raise ProviderFailure("response_schema_validation", "model_mismatch")
    observed["observed_model"] = MODEL
    choices = value.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ProviderFailure("response_schema_validation", "unexpected_choice")
    choice = choices[0]
    message, finish = choice.get("message"), choice.get("finish_reason")
    if (not isinstance(message, dict) or message.get("role") != "assistant"
            or type(choice.get("index")) is not int or choice["index"] != 0 or not isinstance(finish, str)):
        raise ProviderFailure("response_schema_validation", "unexpected_choice")
    observed["finish_reason"] = finish if finish in FINISH_REASONS else "unknown"
    usage = value.get("usage")
    if (finish == "tool_calls" or message.get("tool_calls") or message.get("server_tool_calls")
            or message.get("function_call") or (isinstance(usage, dict) and usage.get("server_tool_use"))):
        raise ProviderFailure("response_schema_validation", "unexpected_tools")
    return finish, message.get("content"), usage


def _chat_cost(usage, observed):
    if not isinstance(usage, dict):
        raise ProviderFailure("financial_accounting", "incomplete_usage")
    counts = {key: usage.get(key) for key in USAGE_KEYS}
    if any(type(number) is not int or number < 0 for number in counts.values()):
        raise ProviderFailure("financial_accounting", "incomplete_usage")
    prompt, output, total, hit, miss = counts.values()
    if prompt != hit + miss or total != prompt + output:
        raise ProviderFailure("financial_accounting", "incomplete_usage")
    details = usage.get("completion_tokens_details")
    if details is not None:
        if not isinstance(details, dict):
            raise ProviderFailure("financial_accounting", "invalid_reasoning_usage")
        if "reasoning_tokens" in details:
            reasoning = details["reasoning_tokens"]
            if type(reasoning) is not int or not 0 <= reasoning <= output:
                raise ProviderFailure("financial_accounting", "invalid_reasoning_usage")
            counts["reasoning_tokens"] = reasoning
    observed["usage"] = counts
    if total > MODEL_CONTEXT or output > OUTPUT:
        raise ProviderFailure("financial_accounting", "usage_exceeds_contract")
    return token_cost(prompt, hit, output)


def _pinned_payload(payload, files):
    if not isinstance(payload, dict):
        return False
    settings = dict(model=MODEL, thinking={"type": "enabled"}, reasoning_effort="high", stream=False,
                    max_tokens=OUTPUT, response_format={"type": "json_object"})
    if (payload.keys() != settings.keys() | {"messages"}
            or any(type(payload[key]) is not type(value) or payload[key] != value for key, value in settings.items())):
        return False
    messages = payload["messages"]
    if (not isinstance(messages, list) or len(messages) != 2
            or messages[0] != {"role": "system", "content": PROMPTS[FUTURE_PROMPT_VERSION]}):
        return False
    user = messages[1]
    if not isinstance(user, dict) or user.keys() != {"role", "content"} or user["role"] != "user":
        return False
    parts = user["content"]
    slots = [{"type": "file", "file_id": f"OFFLINE_SLOT_{i}"} for i in range(1, len(files) + 1)]
    if (not isinstance(parts, list) or len(parts) != len(slots) + 2 or parts[:-2] != slots
            or not all(isinstance(part, dict) and part.keys() == {"type", "text"}
                       and part["type"] == "text" and isinstance(part["text"], str) for part in parts[-2:])):
        return False
    try:
        metadata = json.loads(parts[-2]["text"], object_pairs_hook=unique_fields)
        declared = {(source["file_part"], source["physical_pages"]) for source in metadata["sources"].values()
                    if source["kind"] == "pdf"}
        return metadata["prompt_version"] == FUTURE_PROMPT_VERSION and declared == set(enumerate(files.values(), 1))
    except (AttributeError, KeyError, TypeError, ValueError, RecursionError):
        return False


class TrialNative:
    project = "dc05a-owner-trial"

    def __init__(self, cache, directory, budget_micro_usd, *, key=None, transport=None, clock=time.time,
                 expires_at=None):
        if transport is not None and type(transport) is not httpx.MockTransport:
            raise ValueError("native_test_transport_must_be_mock")
        if key is not None and (not isinstance(key, str) or not re.fullmatch(r"[!-~]{1,512}", key)):
            raise ValueError("invalid_api_credential")
        if expires_at is not None and (type(expires_at) not in (int, float) or not math.isfinite(expires_at)
                                       or expires_at <= 0):
            raise ValueError("invalid_provider_contract_expiry")
        self.mode = "mock" if transport is not None else "live" if key else "offline"
        self._key = key
        self._transport = transport
        self._clock = clock
        self._expires_at = expires_at
        self._budget = budget_micro_usd
        self._session = uuid4().hex
        self._cache = Path(cache)
        self._directory = Path(directory)
        self.account = digest(encoded([self.mode, key]).encode())
        if self.mode != "offline":
            if type(budget_micro_usd) is not int or budget_micro_usd <= 0:
                raise ValueError("owner_budget_required")
            self._ledger = _TrialLedger(self._directory)

    @staticmethod
    def check_state(directory):
        """Report whether recorded or interrupted payments require reconciliation."""
        state = _read_state(Path(directory))
        return any(op["state"] in {"unknown", "inflight"}
                   for row in state["requests"].values() for op in row["operations"])

    def contains_secret(self, text):
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        if not isinstance(text, str):
            return False
        text = unquote(unquote(text))
        return bool((self._key and self._key in text) or FILE_ID.search(text))

    def _candidate(self, raw):
        if not isinstance(raw, str) or self.contains_secret(raw):
            return None
        try:
            content = raw.encode("utf-8")
            candidate = strict_json(content)
            if not isinstance(candidate, dict):
                return None
            pending = [candidate]
            while pending:
                item = pending.pop()
                if isinstance(item, dict):
                    pending.extend(item)
                    pending.extend(item.values())
                elif isinstance(item, list):
                    pending.extend(item)
                elif self.contains_secret(item):
                    return None
            return content
        except (ValueError, RecursionError):
            return None

    def _send(self, route, *, timeout, payload=None, data=None, files=None):
        if self.mode == "offline" or route not in {"/files", "/chat/completions"}:
            raise ValueError("unknown_trial_provider_operation")
        transport = self._transport if self.mode == "mock" else httpx.HTTPTransport(retries=0, trust_env=False)
        status, stage = None, "transport"
        try:
            with httpx.Client(base_url=ORIGIN, transport=transport, trust_env=False, follow_redirects=False,
                              timeout=httpx.Timeout(timeout, connect=8)) as client:
                with client.stream("POST", route, headers={"Authorization": "Bearer " + (self._key or "fixture")},
                                   json=payload, data=data, files=files) as response:
                    status = response.status_code
                    if not response.is_success:
                        raise ProviderFailure("http_status", "http_error", exception_class="HTTPStatusError",
                                              http_status=status, provider_code=safe_http_error_code(response))
                    stage = "response_read"
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        if len(raw) + len(chunk) > 2_000_000:
                            raise ProviderFailure(stage, "response_too_large", http_status=status)
                        raw.extend(chunk)
        except httpx.RequestError as error:
            raise transport_failure(error, stage, status) from None
        try:
            result = json.loads(raw, object_pairs_hook=unique_fields, parse_constant=_reject_json_constant)
        except (ValueError, RecursionError):
            raise ProviderFailure("json_decode", "invalid_json", exception_class="JSONDecodeError",
                                  http_status=status) from None
        if not isinstance(result, dict):
            raise ProviderFailure("response_schema_validation", "expected_object", http_status=status)
        return ProviderObject(result, status)

    def _read_pdf(self, sha):
        try:
            with (self._cache / (sha + ".pdf")).open("rb") as source:
                raw = source.read(MAX_SIZE + 1)
        except OSError:
            return None
        if not (len(raw) <= MAX_SIZE and raw.startswith(b"%PDF-") and digest(raw) == sha):
            return None
        return raw

    def _binding_key(self, sha):
        return digest(encoded([self.account, self.project, PURPOSE, sha]).encode())

    def _binding(self, state, sha, size, now):
        item = state["bindings"].get(self._binding_key(sha))
        if item is None:
            return None
        if (not isinstance(item, dict) or item.get("account") != self.account or item.get("project") != self.project
                or item.get("purpose") != PURPOSE or item.get("parser") != PURPOSE or item.get("sha256") != sha
                or item.get("bytes") != size or not isinstance(item.get("id"), str) or not FILE_ID.fullmatch(item["id"])
                or type(item.get("created")) is not int or type(item.get("expires")) is not int
                or item["created"] > now + 30 or item["expires"] - item["created"] != PARSE_TTL):
            raise NativeStateError("binding_identity_mismatch")
        return item if item["expires"] > now + CHAT_TIMEOUT else None

    def _accept_upload(self, result, state, sha, size, pages):
        if "error" in result:
            raise ProviderFailure("file_metadata_validation", "unexpected_envelope")
        binding = NativeD1.file_snapshot(self, result, sha, size, self._clock())
        if any(item.get("account") == self.account and item.get("id") == binding["id"]
               and item.get("sha256") != sha for item in state["bindings"].values()):
            raise ProviderFailure("file_metadata_validation", "id_collision")
        if self._key and self._key in binding["id"]:
            raise ProviderFailure("file_metadata_validation", "credential_detected")
        state["bindings"][self._binding_key(sha)] = binding
        return pages * PAGE_PRICE, binding

    def _begin(self, state, op):
        op.update(state="inflight", started_at=int(self._clock()))
        self._ledger.save(state)

    def _operate(self, state, op, route, interpret, **params):
        started = time.monotonic()
        response = None
        try:
            response = self._send(route, **params)
            cost, result = interpret(response)
        except ProviderFailure as failure:
            op["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            op.update(state="unknown", failure=failure.diagnostic(op["kind"], op["elapsed_ms"],
                http_status=response.http_status if response is not None else None))
            self._ledger.save(state)
            return None
        op.update(state="settled", cost=cost, elapsed_ms=round((time.monotonic() - started) * 1000))
        self._ledger.save(state)
        return result

    def _contract_expired(self):
        return self._expires_at is not None and self._clock() >= self._expires_at

    def dispatch(self, payload, files, request_key, sizing):
        telemetry = dict(provider=self.mode, observed_model=None, finish_reason=None, usage=None,
                         upload=dict(attempted=0, completed=0, reused=0, pages=0), chat_attempted=False,
                         provider_failure=None, estimated_micro_usd=None, planned_reserve_micro_usd=None,
                         known_micro_usd=0, held_micro_usd=0, cost_breakdown=None, budget=None,
                         timings_ms=dict(upload=0, chat=0))
        if self.mode == "offline":
            return TrialReply("offline", telemetry=telemetry)
        if self._contract_expired():
            return TrialReply("contract_expired", telemetry=telemetry)
        if (not isinstance(request_key, str) or not re.fullmatch(r"[!-~]{1,200}", request_key)
                or not isinstance(sizing, dict) or type(sizing.get("estimate")) is not int or sizing["estimate"] < 0
                or not isinstance(files, dict) or any(not isinstance(sha, str) or not SHA.fullmatch(sha)
                    or type(pages) is not int or not 1 <= pages <= MAX_PAGES for sha, pages in files.items())):
            return TrialReply("invalid_native_request", telemetry=telemetry)
        if len(files) > FILE_LIMIT:
            return TrialReply("provider_file_limit", telemetry=telemetry)
        if sizing["estimate"] > EXTENDED:
            return TrialReply("over_cap", telemetry=telemetry)
        if not _pinned_payload(payload, files):
            return TrialReply("invalid_native_request", telemetry=telemetry)
        try:
            with self._ledger.transaction() as state:
                if _recover(state):
                    self._ledger.save(state)
                return self._dispatch(state, deepcopy(payload), files.copy(), digest(request_key.encode()), sizing, telemetry)
        except (OSError, NativeStateError):
            if telemetry["chat_attempted"] or telemetry["upload"]["attempted"]:
                telemetry.update(known_micro_usd=None, held_micro_usd=telemetry["planned_reserve_micro_usd"], budget=None)
            return TrialReply("native_state_unavailable", telemetry=telemetry)

    def _dispatch(self, state, payload, files, request_id, sizing, telemetry):
        requests = state["requests"]
        operations = [op for item in requests.values() if item["session"] == self._session for op in item["operations"]]
        unresolved = [op for item in requests.values() for op in item["operations"] if op["state"] == "unknown"]
        known, held = _amounts(operations)
        remaining = max(0, self._budget - known - held)
        telemetry["budget"] = dict(limit_micro_usd=self._budget, known_micro_usd=known, held_micro_usd=held,
                                   remaining_micro_usd=remaining, unresolved_micro_usd=_amounts(unresolved)[1])
        if request_id in requests:
            return TrialReply("duplicate_request", telemetry=telemetry)
        if unresolved:
            return TrialReply("provider_unknown", telemetry=telemetry)
        now = self._clock()
        bindings, sizes = {}, {}
        for sha in files:
            raw = self._read_pdf(sha)
            if raw is None:
                return TrialReply("file_unavailable", telemetry=telemetry)
            sizes[sha] = len(raw)
            binding = self._binding(state, sha, len(raw), now)
            if binding is not None:
                bindings[sha] = binding
        missing = {sha: dict(kind="upload", state="reserved", sha256=sha, pages=pages, reserve=pages * PAGE_PRICE)
                   for sha, pages in files.items() if sha not in bindings}
        upload_cost = sum(op["reserve"] for op in missing.values())
        telemetry.update(estimated_micro_usd=cold_cost(sizing["estimate"]) + upload_cost,
                         planned_reserve_micro_usd=CHAT_RESERVE + upload_cost)
        telemetry["upload"]["reused"] = len(bindings)
        if telemetry["planned_reserve_micro_usd"] > remaining:
            return TrialReply("budget_exhausted", telemetry=telemetry)
        if self._contract_expired():
            return TrialReply("contract_expired", telemetry=telemetry)
        chat = dict(kind="chat", state="reserved", reserve=CHAT_RESERVE)
        request = dict(session=self._session, created_at=int(now), status="inflight", operations=[*missing.values(), chat])
        state["bindings"] = {key: item for key, item in state["bindings"].items()
                             if isinstance(item, dict) and type(item.get("expires")) is int and item["expires"] > now}
        requests[request_id] = request
        self._ledger.save(state)
        status, content = self._execute(state, payload, files, missing, sizes, bindings, chat, telemetry)
        for op in request["operations"]:
            if op["state"] == "reserved":
                op["state"] = "cancelled"
        request["status"] = status
        self._ledger.save(state)
        known, held = _amounts(request["operations"])
        breakdown = {}
        for kind, ops in (("upload", tuple(missing.values())), ("chat", (chat,))):
            subtotal, hold = _amounts(ops)
            breakdown[kind] = dict(known_micro_usd=subtotal, held_micro_usd=hold)
        telemetry.update(known_micro_usd=known, held_micro_usd=held, cost_breakdown=breakdown)
        budget = telemetry["budget"]
        budget["known_micro_usd"] += known
        budget["held_micro_usd"] += held
        budget["unresolved_micro_usd"] += held
        budget["remaining_micro_usd"] = remaining - known - held
        private_values = tuple(item["id"] for item in bindings.values())
        if self._key:
            private_values += (self._key,)
        return TrialReply(status, content, telemetry, private_values)

    def _execute(self, state, payload, files, missing, sizes, bindings, chat, telemetry):
        upload = telemetry["upload"]
        for sha, op in missing.items():
            raw = self._read_pdf(sha)
            if raw is None or len(raw) != sizes[sha]:
                return "file_unavailable", None
            self._begin(state, op)
            upload["attempted"] += 1
            upload["pages"] += files[sha]
            binding = self._operate(state, op, "/files",
                lambda response: self._accept_upload(response, state, sha, len(raw), files[sha]),
                data={"purpose": PURPOSE, "expires_after[anchor]": "created_at", "expires_after[seconds]": str(PARSE_TTL)},
                files={"file": (sha + ".pdf", raw, "application/pdf")}, timeout=UPLOAD_TIMEOUT)
            telemetry["timings_ms"]["upload"] += op["elapsed_ms"]
            if binding is None:
                telemetry["provider_failure"] = op["failure"]
                return "provider_failure", None
            upload["completed"] += 1
            bindings[sha] = binding
        check_until = self._clock() + CHAT_TIMEOUT
        if any(item["expires"] <= check_until for item in bindings.values()):
            return "binding_expiry_before_chat", None
        parts = payload["messages"][1]["content"]
        for part, sha in zip(parts[:-2], files, strict=True):
            part["file_id"] = bindings[sha]["id"]
        observed = chat["observed"] = {}
        candidate = None

        def inspect(response):
            nonlocal candidate
            finish, raw, usage = _inspect_chat(response, observed)
            if finish == "stop":
                candidate = self._candidate(raw)
            return _chat_cost(usage, observed), finish

        self._begin(state, chat)
        telemetry["chat_attempted"] = True
        finish = self._operate(state, chat, "/chat/completions", inspect, payload=payload, timeout=CHAT_TIMEOUT)
        telemetry.update(observed)
        telemetry["timings_ms"]["chat"] = chat["elapsed_ms"]
        if finish is None:
            telemetry["provider_failure"] = chat["failure"]
            if chat["failure"]["failure_stage"] == "financial_accounting" and candidate is not None:
                return "completed_usage_unknown", candidate
            return "provider_failure", None
        if finish != "stop":
            return "finish_not_stop", None
        return ("completed", candidate) if candidate is not None else ("invalid_candidate", None)
