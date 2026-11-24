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
from decimal import Decimal, InvalidOperation
from pathlib import Path

MODEL = "deepseek-flash"
CONTEXT = 1_000_000
HIT, MISS, OUTPUT, PAGE = 6, 300, 1200, 225_000  # nanodollars
BODY = 48 * 1024**2


class Stop(RuntimeError):
    pass


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


def chat(system, blocks, limit, *, compile_task=False):
    body = {
        "model": MODEL, "stream": False, "max_tokens": limit,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": blocks}],
        "thinking": {"type": "enabled" if compile_task else "disabled"},
    }
    if compile_task:
        body.update(reasoning_effort="high", response_format={"type": "json_object"})
    return body


def reply(response, limit):
    try:
        if response["model"] not in (MODEL, "DeepSeek-V4.1-Flash-1017"):
            raise ValueError
        choice, = response["choices"]
        finish = choice["finish_reason"]
        content = choice["message"].get("content")
        usage = response["usage"]
        names = ("prompt_tokens", "prompt_cache_hit_tokens",
                 "prompt_cache_miss_tokens", "completion_tokens")
        prompt, hit, miss, output = (usage[key] for key in names)
        details = usage.get("completion_tokens_details") or {}
        reasoning = details.get("reasoning_tokens")
        values = (prompt, hit, miss, output)
        if any(type(n) is not int or n < 0 for n in values):
            raise ValueError
        if prompt != hit + miss or prompt > CONTEXT or output > limit:
            raise ValueError
        if reasoning is not None and (type(reasoning) is not int or not 0 <= reasoning <= output):
            raise ValueError
        if not isinstance(finish, str) or (content is not None and not isinstance(content, str)):
            raise ValueError
        result = dict(zip(names, values))
        result["reasoning_tokens"] = reasoning
        return {"text": content or "", "finish_reason": finish, "usage": result,
                "model": response["model"], "cost_nd": hit * HIT + miss * MISS + output * OUTPUT}
    except (KeyError, ValueError, AttributeError, TypeError):
        raise Stop("Unknown provider outcome: invalid model, response or usage") from None


def reserve(limit):
    return CONTEXT * MISS + limit * OUTPUT


def transport(key):
    def post(endpoint, body, content_type):
        if endpoint not in ("/files", "/chat/completions") or len(body) > BODY:
            raise Stop("Request outside approved API contract")
        conn = http.client.HTTPSConnection("api.deepseek.com", timeout=275)
        try:
            conn.request("POST", endpoint, body, {"Authorization": "Bearer " + key,
                                                   "Content-Type": content_type})
            response = conn.getresponse()
            data = response.read(32 * 1024**2 + 1)
            if response.status != 200 or len(data) > 32 * 1024**2:
                raise Stop(f"Unknown provider outcome: HTTP {response.status}")
            return json.loads(data)
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
        if stage not in {"compile", "consult"}:
            raise Stop("Unsupported ledger stage")
        self.path = path
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
                if (key in operations or op["stage"] not in {"compile", "consult"} or op["stage"] not in stages
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
        if any(op["status"] != "SETTLED" for op in ops):
            raise Stop("Pending/unknown operation requires independent reconciliation")
        stage_spent = sum(op["cost_nd"] for op in ops if op["stage"] == self.stage)
        spent = sum(op["cost_nd"] for op in ops)
        remaining = min(self.cap - stage_spent, self.total - spent)
        if amount > remaining:
            raise Stop(f"DEFERRED_BUDGET: next reserve={amount}nd, stage_spent={stage_spent}nd, "
                       f"total_spent={spent}nd, available={remaining}nd")

    def execute(self, id_, endpoint, body, reserve_nd, post, parse, *, content_type="application/json", prefix=None):
        if self.has(id_) or len(body) > BODY or not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{0,127}", id_):
            raise Stop("Duplicate or malformed operation, or oversized body")
        self.check(reserve_nd)
        op = {"stage": self.stage, "id": id_, "status": "PENDING",
              "reserve_nd": reserve_nd, "request_sha256": sha(body), "prefix_sha256": prefix}
        if endpoint == "/chat/completions":
            try:
                params = json.loads(body)
                op["parameters"] = {key: params[key] for key in ("model", "max_tokens", "thinking",
                                    "reasoning_effort", "response_format") if key in params}
            except (ValueError, TypeError):
                raise Stop("Invalid serialized chat request") from None
        self.data["ops"].append(op)
        save(self.path, self.data)
        start = time.monotonic()
        try:
            response = post(endpoint, body, content_type)
            result = parse(response)
            if not 0 <= result["cost_nd"] <= reserve_nd:
                raise Stop("Provider charge outside reserve")
            save(self.path.parent / self.stage / (id_ + ".json"), result)
            op.update(status="SETTLED", cost_nd=result["cost_nd"],
                      duration_ms=round((time.monotonic() - start) * 1000),
                      response_sha256=sha(encode(response)), result_sha256=sha(encode(result)))
            save(self.path, self.data)
            return result
        except BaseException:
            op["status"] = "UNKNOWN"
            save(self.path, self.data)
            raise Stop(f"{id_}: unknown outcome; all paid operations blocked") from None

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


def offline():
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
    print("seccomp: socket denied (EPERM)")


def runtime_digest():
    directory = Path(__file__).resolve().parent
    return sha(encode({p.name: sha(p.read_bytes()) for p in sorted(directory.glob("*.py"))}))


def kernel_release():
    return Path("/proc/sys/kernel/osrelease").read_text().strip()


def live_gate():
    release = kernel_release().lower()
    if "wsl2" not in release or not os.isatty(0) or os.environ.get("CODEX_THREAD_ID"):
        raise Stop("LIVE requires an interactive owner WSL2 session")
