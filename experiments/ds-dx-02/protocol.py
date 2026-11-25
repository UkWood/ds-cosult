"""Shared DeepSeek transport and conservative paid-operation accounting."""
import ctypes
import errno
import fcntl
import hashlib
import http.client
import json
import os
import re
import socket
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sse import ChatStream

MODEL = "deepseek-flash"
CONTEXT = 1_000_000
HIT, MISS, OUTPUT, PAGE = 6, 300, 1200, 225_000  # nanodollars
BODY = 48 * 1024**2
RESPONSE_MAX = 32 * 1024**2
MODES = {"disabled", "low", "high"}
STAGES = {"compile", "consult", "r4-a", "r4-c"}
ENDPOINTS = {"/files", "/chat/completions"}


class Stop(RuntimeError):
    pass


class ProviderContract(Stop):
    def __init__(self, stage):
        self.stage = stage
        super().__init__("Unknown provider outcome: invalid " + stage)


@dataclass
class Delivery:
    value: object = None
    raw: bytes | None = None
    metadata: dict | None = None


class TransportFault(Stop):
    def __init__(self, stage, exception, delivery):
        super().__init__("Provider transport outcome is uncertain")
        self.stage = stage
        self.exception = exception
        self.delivery = delivery


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    os.replace(file.name, path)
    with directory_fd(path.parent) as fd:
        os.fsync(fd)


@contextmanager
def directory_fd(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield fd
    finally:
        os.close(fd)


def save(path, obj):
    write(path, encode(obj))


def load(path):
    return json.loads(path.read_bytes())


def money(text):
    try:
        value = Decimal(text) * 1_000_000_000
        if not value.is_finite() or value <= 0 or value != value.to_integral_value():
            raise Stop("Invalid USD cap")
        return int(value)
    except InvalidOperation:
        raise Stop("Invalid USD cap") from None


def text(value):
    return {"type": "text", "text": value}


def chat(system, blocks, limit, *, compile_task=False, mode="disabled", streaming=False):
    if mode not in MODES or not compile_task and mode != "disabled":
        raise Stop("Unsupported reasoning mode")
    body = {
        "model": MODEL, "stream": streaming, "max_tokens": limit,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": blocks}],
        "thinking": {"type": "enabled" if mode != "disabled" else "disabled"},
    }
    if streaming:
        body["stream_options"] = {"include_usage": True}
    if compile_task:
        body["response_format"] = {"type": "json_object"}
    if mode != "disabled":
        body["reasoning_effort"] = mode
    return body


def reply(response, limit):
    try:
        if response["model"] not in (MODEL, "DeepSeek-V4.1-Flash-1017"):
            raise ValueError
        choice, = response["choices"]
        finish = choice["finish_reason"]
        content = choice["message"].get("content")
        if not isinstance(finish, str) or (content is not None and not isinstance(content, str)):
            raise ValueError
    except (KeyError, ValueError, AttributeError, TypeError):
        raise ProviderContract("parse") from None
    try:
        usage = response["usage"]
        names = ("prompt_tokens", "prompt_cache_hit_tokens",
                 "prompt_cache_miss_tokens", "completion_tokens")
        prompt, hit, miss, output = (usage[key] for key in names)
        details = usage.get("completion_tokens_details")
        reasoning = None if details is None else details.get("reasoning_tokens")
        if any(type(n) is not int or n < 0 for n in (prompt, hit, miss, output)):
            raise ValueError
        if prompt != hit + miss or prompt > CONTEXT or output > limit:
            raise ValueError
        if "total_tokens" in usage and (type(usage["total_tokens"]) is not int
                                      or usage["total_tokens"] != prompt + output):
            raise ValueError
        if reasoning is not None and (type(reasoning) is not int or not 0 <= reasoning <= output):
            raise ValueError
    except (KeyError, ValueError, AttributeError, TypeError):
        raise ProviderContract("usage") from None
    observed = response.get("thinking")
    observed_type = observed.get("type") if isinstance(observed, dict) else None
    effort = response.get("reasoning_effort")
    reported = ("disabled" if observed_type == "disabled" else
                effort if observed_type == "enabled" and effort in ("low", "high") else
                "enabled" if observed_type == "enabled" else None)
    result = dict(zip(names, (prompt, hit, miss, output)))
    result["reasoning_tokens"] = reasoning
    return {"text": content or "", "finish_reason": finish, "usage": result,
            "model": response["model"], "reported_mode": reported,
            "cost_nd": hit * HIT + miss * MISS + output * OUTPUT}


def reserve(limit):
    return CONTEXT * MISS + limit * OUTPUT


def provider_error(value, key):
    error = value.get("error") if isinstance(value, dict) else None
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    message = error.get("message")
    code = str(code) if type(code) is int else code
    allowed = {"invalid_request_error", "authentication_error", "rate_limit_error",
               "server_error", "insufficient_balance", "invalid_request", "model_not_found"}
    cleaned = code if isinstance(code, str) and (code in allowed or re.fullmatch(r"[0-9]{1,8}", code)) else None
    # Use fixed classifications; error text can echo credentials or supplied material.
    reasons = ("rate limit", "invalid api key", "insufficient balance", "invalid request",
               "context length", "server error", "service unavailable", "overloaded")
    match = next((reason for reason in reasons if reason in message[:2048].lower()), None) if isinstance(message, str) else None
    return {"code": cleaned if cleaned != key else None, "message": match or "[redacted]"}


def transport(key):
    def safe_id(value):
        return value if (isinstance(value, str) and key not in value
                         and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", value)) else None

    def post(endpoint, body, content_type):
        if endpoint not in ENDPOINTS or len(body) > BODY:
            raise Stop("Request outside approved API contract")
        streaming = endpoint == "/chat/completions" and json.loads(body).get("stream") is True
        conn = http.client.HTTPSConnection("api.deepseek.com", timeout=275)
        stage = "connect"
        stream = ChatStream() if streaming else None
        delivery = Delivery(metadata=dict(stream.metadata(), response_format="sse") if stream else {})
        try:
            conn.connect()
            stage = "send"
            headers = {"Authorization": "Bearer " + key, "Content-Type": content_type}
            if streaming:
                headers["Accept"] = "text/event-stream"
            conn.request("POST", endpoint, body, headers)
            stage = "headers"
            response = conn.getresponse()
            delivery.metadata.update(http_status=response.status, request_id=safe_id(response.getheader("x-request-id") or response.getheader("request-id")))
            stage = "read"
            if response.status != 200:
                stream = None
            data = bytearray()
            deadline = time.monotonic() + 1200
            try:
                if stream and (response.getheader("Content-Type") or "").partition(";")[0].strip().lower() != "text/event-stream":
                    stage = "headers"
                    raise Stop("Expected a DeepSeek SSE response")
                while len(data) <= RESPONSE_MAX:
                    if stream and time.monotonic() > deadline:
                        raise TimeoutError("SSE wall timeout")
                    read_size = min(65536, RESPONSE_MAX + 1 - len(data))
                    try:
                        chunk = response.read1(read_size)
                    except http.client.IncompleteRead as error:
                        data.extend(error.partial[:read_size])
                        raise
                    if not chunk:
                        break
                    data.extend(chunk)
                    if stream:
                        stage = "parse"
                        stream.feed(chunk)
                        stage = "read"
                        if stream.done:
                            break
            finally:
                raw = bytes(data)
                delivery.metadata.update(response_bytes=len(raw), response_sha256=sha(raw))
                if stream:
                    delivery.metadata.update(stream.metadata(), response_format="sse",
                                             response_id=safe_id(stream.response_id))
                if len(raw) <= RESPONSE_MAX and key.encode() not in raw:
                    delivery.raw = raw
            if len(data) > RESPONSE_MAX:
                raise Stop("Response exceeds local size limit")
            if stream:
                if not stream.done:
                    raise http.client.IncompleteRead(b"", None)
                stage = "parse"
                delivery.value = stream.assembled()
                delivery.metadata["response_complete"] = True
                return delivery
            if response.length not in (None, 0):
                raise http.client.IncompleteRead(b"", response.length)
            delivery.metadata["response_complete"] = True
            stage = "parse"
            if response.status != 200:
                stage = "headers"
                if len(data) <= 65536:
                    try:
                        value = json.loads(data)
                        delivery.metadata["provider_error"] = provider_error(value, key)
                        if isinstance(value, dict):
                            delivery.metadata["response_id"] = safe_id(value.get("id"))
                    except (ValueError, RecursionError, UnicodeError):
                        pass
                raise TransportFault(stage, "HTTPStatusError", delivery)
            delivery.value = json.loads(data)
            if isinstance(delivery.value, dict):
                delivery.metadata["response_id"] = safe_id(delivery.value.get("id"))
            return delivery
        except TransportFault:
            raise
        except BaseException as error:
            raise TransportFault(stage, type(error).__name__, delivery) from None
        finally:
            conn.close()
    return post


@contextmanager
def locked(root):
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (root / ".lock").open("ab") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop("State already in use") from None
        yield


class Ledger:
    def __init__(self, path, stage, cap, total, identity, resume=False, approval=None):
        if stage not in STAGES:
            raise Stop("Unsupported ledger stage")
        self.path = path
        self.inflight = path.parent / ".inflight"
        if self.inflight.exists():
            raise Stop("A durable in-flight operation requires independent reconciliation")
        self.stage = stage
        self.cap = cap
        self.total = total
        self.identity = identity
        self.data = load(path) if path.exists() else {
            "initial_total": total, "total": total, "stages": {}, "initial_stages": {}, "ops": [], "approvals": []}
        self.verify_history()
        prior = self.data["stages"].get(stage)
        if cap > total or (prior is None and (resume or approval or self.data["total"] != total)):
            raise Stop("Invalid initial or resumed stage GO")
        if prior is not None:
            if not resume or prior["identity"] != identity:
                raise Stop("Stage already started. Resume requires identical pins and plan")
            if approval is None:
                if prior["cap"] != cap or self.data["total"] != total:
                    raise Stop("Increased budget requires an explicit owner approval record")
            else:
                self.amend(prior, approval)
        else:
            self.data["initial_stages"][stage] = {"cap": cap, "identity": identity}
            self.data["stages"][stage] = {"cap": cap, "identity": identity}

    def replay_approval(self, record, stages, total, seen):
        stage = record["stage"]
        prior = stages[stage]
        token = record["owner_go"]
        if (not isinstance(token, str) or not token.strip() or token in seen
                or prior != {"cap": record["old_cap"], "identity": record["identity"]}
                or record["old_total"] != total
                or type(record["new_cap"]) is not int or type(record["new_total"]) is not int
                or not prior["cap"] < record["new_cap"] <= record["new_total"] or record["new_total"] < total):
            raise Stop("Invalid or reused owner approval")
        stages[stage] = {"cap": record["new_cap"], "identity": record["identity"]}
        seen.add(token)
        return record["new_total"]

    def verify_history(self):
        try:
            stages = dict(self.data["initial_stages"])
            total = self.data["initial_total"]
            previous = None
            seen = set()
            for approval in self.data["approvals"]:
                record = approval["record"]
                if approval["digest"] != sha(encode([previous, record])):
                    raise Stop("Owner approval digest mismatch")
                total = self.replay_approval(record, stages, total, seen)
                previous = approval["digest"]
            if total != self.data["total"] or stages != self.data["stages"]:
                raise Stop("Budget history differs from ledger caps")
            operations = set()
            for op in self.data["ops"]:
                if op["status"] != "SETTLED":
                    raise Stop("Pending/unknown operation requires independent reconciliation")
                key = (op["stage"], op["id"])
                if (key in operations or op["stage"] not in STAGES or op["stage"] not in stages
                        or not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{0,127}", op["id"])
                        or not 0 <= op["cost_nd"] <= op["reserve_nd"]):
                    raise Stop("Invalid operation history")
                raw = (self.path.parent / op["stage"] / (op["id"] + ".json")).read_bytes()
                if sha(raw) != op["result_sha256"] or json.loads(raw)["cost_nd"] != op["cost_nd"]:
                    raise Stop("Checkpoint cost or digest mismatch")
                operations.add(key)
        except (KeyError, TypeError, ValueError, OSError):
            raise Stop("Invalid ledger format or incompatible ledger revision") from None

    def amend(self, prior, record):
        expected = {"stage": self.stage, "identity": self.identity, "old_cap": prior["cap"],
                    "new_cap": self.cap, "old_total": self.data["total"], "new_total": self.total}
        if set(record) != set(expected) | {"owner_go"} or any(record[k] != v for k, v in expected.items()):
            raise Stop("Amendment does not bind the requested caps and plan")
        chain = self.data["approvals"]
        seen = {item["record"]["owner_go"] for item in chain}
        self.data["total"] = self.replay_approval(record, self.data["stages"], self.data["total"], seen)
        previous = chain[-1]["digest"] if chain else None
        chain.append({"record": record, "digest": sha(encode([previous, record]))})
        save(self.path, self.data)

    def has(self, id_):
        return any(op["stage"] == self.stage and op["id"] == id_ for op in self.data["ops"])

    def settled(self, id_):
        return any(op["stage"] == self.stage and op["id"] == id_ and op["status"] == "SETTLED"
                   for op in self.data["ops"])

    def check(self, amount):
        ops = self.data["ops"]
        if self.inflight.exists() or any(op["status"] != "SETTLED" for op in ops):
            raise Stop("Pending/unknown operation requires independent reconciliation")
        stage_spent = sum(op["cost_nd"] for op in ops if op["stage"] == self.stage)
        spent = sum(op["cost_nd"] for op in ops)
        remaining = min(self.cap - stage_spent, self.total - spent)
        if amount > remaining:
            raise Stop(f"DEFERRED_BUDGET: next reserve={amount}nd, stage_spent={stage_spent}nd, "
                       f"total_spent={spent}nd, available={remaining}nd")

    def execute(self, id_, endpoint, body, reserve_nd, post, parse, *, content_type="application/json", prefix=None):
        if (self.has(id_) or endpoint not in ENDPOINTS or len(body) > BODY
                or type(reserve_nd) is not int or reserve_nd <= 0
                or not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{0,127}", id_)):
            raise Stop("Duplicate or malformed operation, or oversized body")
        self.check(reserve_nd)
        op = {"stage": self.stage, "id": id_, "status": "PENDING", "endpoint": endpoint,
              "reserve_nd": reserve_nd, "request_sha256": sha(body), "prefix_sha256": prefix}
        mode = None
        if endpoint == "/chat/completions":
            try:
                params = json.loads(body)
                op["parameters"] = {key: params[key] for key in ("model", "max_tokens", "thinking",
                                    "reasoning_effort", "response_format", "stream", "stream_options") if key in params}
                mode = ("disabled" if params.get("thinking", {}).get("type") == "disabled"
                        else params.get("reasoning_effort"))
            except (ValueError, TypeError, AttributeError):
                raise Stop("Invalid serialized chat request") from None
        diag = dict(operation_id=id_, endpoint=endpoint, request_sha256=op["request_sha256"],
                    request_bytes=len(body), mode=mode, started_utc=utc_now(), http_status=None,
                    request_id=None, response_id=None, response_bytes=None, response_sha256=None,
                    response_complete=False, provider_error=None, raw_saved=False, result_saved=False)
        self.data["ops"].append(op)
        start = time.monotonic()
        stage = "persist_pending"
        delivery = Delivery()
        root = self.path.parent
        diagnostic_path = root / "diagnostics" / self.stage / (id_ + ".json")

        def timing():
            return dict(ended_utc=utc_now(), elapsed_ms=round((time.monotonic() - start) * 1000))

        def private_response():
            if delivery.raw is not None and not diag["raw_saved"]:
                write(root / "responses" / self.stage / (id_ + ".bin"), delivery.raw)
                diag["raw_saved"] = True

        def diagnostic():
            diag.update(delivery.metadata or {})
            diag.update(timing())
            save(diagnostic_path, diag)

        try:
            save(self.path, self.data)
            save(self.inflight, {key: op[key] for key in ("id", "stage", "reserve_nd", "request_sha256")})
            stage = "send"
            response = post(endpoint, body, content_type)
            if isinstance(response, Delivery):
                delivery = response
            else:
                raw = encode(response)
                delivery = Delivery(response, raw, dict(response_bytes=len(raw), response_sha256=sha(raw),
                                                       response_complete=True))
            stage = "persist_response"
            private_response()
            stage = "parse"
            result = parse(delivery.value)
            stage = "usage"
            if not 0 <= result["cost_nd"] <= reserve_nd:
                raise ProviderContract("usage")
            stage = "persist_result"
            save(root / self.stage / (id_ + ".json"), result)
            diag["result_saved"] = True
            stage = "persist_diagnostic"
            diag.update(stage="complete", exception=None)
            diagnostic()
            stage = "persist_ledger"
            settled = dict(op, status="SETTLED", cost_nd=result["cost_nd"], duration_ms=diag["elapsed_ms"],
                           response_sha256=sha(encode(delivery.value)), result_sha256=sha(encode(result)))
            self.data["ops"][-1] = settled
            save(self.path, self.data)
            stage = "persist_clear_inflight"
            self.inflight.unlink()
            return result
        except BaseException as error:
            if isinstance(error, TransportFault):
                delivery = error.delivery
                stage = error.stage
            elif isinstance(error, ProviderContract):
                stage = error.stage
            kind = error.exception if isinstance(error, TransportFault) else type(error).__name__
            # A failed settlement write can leave a valid result but must still block further POSTs.
            op.update(status="UNKNOWN", uncertainty_stage=stage)
            self.data["ops"][-1] = op
            diag.update(stage=stage, exception=kind)
            try:
                private_response()
            except OSError:
                diag["raw_persist_failed"] = True
            try:
                diagnostic()
            except OSError:
                pass
            try:
                save(self.path, self.data)
            except OSError:
                pass  # the last durable PENDING remains blocking
            raise Stop(f"{id_}: unknown outcome at {stage}; all paid operations blocked") from None

    def checkpoint_request(self, id_, body, prefix):
        op, = (item for item in self.data["ops"] if item["stage"] == self.stage and item["id"] == id_)
        if op["request_sha256"] != sha(body) or op["prefix_sha256"] != prefix:
            raise Stop("Checkpoint request digest mismatch")

    def result(self, id_):
        op, = (item for item in self.data["ops"] if item["stage"] == self.stage and item["id"] == id_)
        raw = (self.path.parent / self.stage / (id_ + ".json")).read_bytes()
        if sha(raw) != op["result_sha256"]:
            raise Stop("Checkpoint digest mismatch")
        return json.loads(raw)


def offline(*, stream=None):
    lib = ctypes.CDLL("libseccomp.so.2")
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7fff0000)
    if not ctx:
        raise Stop("Cannot initialize seccomp")
    try:
        for name in (b"socket", b"socketpair", b"connect", b"io_uring_setup"):
            number = lib.seccomp_syscall_resolve_name(name)
            if number >= 0 and lib.seccomp_rule_add(ctx, 0x00050000 | errno.EPERM, number, 0):
                raise Stop("Cannot configure seccomp")
        if lib.seccomp_load(ctx):
            raise Stop("Cannot activate seccomp")
    finally:
        lib.seccomp_release(ctx)
    try:
        with socket.socket():
            raise Stop("Offline socket probe succeeded")
    except PermissionError as error:
        if error.errno != errno.EPERM:
            raise
    print("seccomp: socket denied (EPERM)", file=stream)


def runtime_digest():
    directory = Path(__file__).resolve().parent
    return sha(encode({p.name: sha(p.read_bytes()) for p in sorted(directory.glob("*.py"))}))


def kernel_release():
    return Path("/proc/sys/kernel/osrelease").read_text().strip()


def live_gate():
    release = kernel_release().lower()
    if "wsl2" not in release or not os.isatty(0) or os.environ.get("CODEX_THREAD_ID"):
        raise Stop("LIVE requires an interactive owner WSL2 session")
