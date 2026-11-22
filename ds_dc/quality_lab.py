"""Q01-N preflight and closed native V2.1 mock experiment. No live activation."""
import argparse
from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import time

import httpx

from .context import EXTENDED, OUTPUT, TOKENIZER_NAME, TOKENIZER_SHA
from .corpus import BKD, COMMIT, MAX_SIZE, digest, encoded
from .evidence_integration import MockReply, OfflineConsultant, PROMPT_VERSION, build_request, measure
from .finance import Ledger, OWNER, RATES, Stopped, token_cost
from .native import (CAL_POST_RESERVE, CHAT_TIMEOUT, FILE_ID, MODEL_CONTEXT, NativeD1, ORIGIN,
                     PAGE_PRICE, PARSE_TTL, PARSED_BYTES_LIMIT, PURPOSE, UPLOAD_TIMEOUT)
from .prep import freeze, freeze_digest, load
from .provider_failure import ProviderFailure
from .recovery import CAMPAIGN, MANIFEST, ORIGINAL_UPLOAD
from .runtime import Journal, Pilot

QUESTION_ID = "Q01-N"
QUESTION = "Что проверить, если на БКД-ПК-RF.2 не горит зелёный индикатор Link?"
REQUEST_ID = "r53d6ef982e1a4303a9f4978ce0bf2197"
ALIAS = "deepseek-flash"
VERSION = "DeepSeek-V4.1-Flash-1017"
CHAT_KEY = CAMPAIGN + "/candidate-answer-v2.1/single-experiment"
MOCK_KEY = "fixture"
PROPOSED_RESERVE = CAL_POST_RESERVE + 80 * PAGE_PRICE
EXACT_LIMITS = dict(budget=PROPOSED_RESERVE, normal=0, extended=1, chats=1,
                                   pages=80, upload=4, status=0, delete=0, calibration=1)
USAGE_KEYS = ("prompt_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
              "completion_tokens", "total_tokens")
ROOT = Path(__file__).resolve().parents[1]


def require(condition, reason):
    if not condition:
        raise Stopped(reason)


@dataclass(frozen=True)
class Prepared:
    commit: str
    manifest: str
    wire: str
    logical_payload: str
    files: tuple
    estimate: int
    sparse_pages: int
    wire_bytes: int
    cold_estimate: int
    registry: object

    @property
    def payload_digest(self):
        return digest(self.logical_payload.encode())

    @property
    def identity(self):
        return self.commit, self.manifest, self.wire, self.payload_digest, self.files


def prepare_materials(entries, dossiers, cache, commit):
    require(bool(re.fullmatch("[a-f0-9]{40}", commit)), "invalid_head")
    manifest = freeze(entries, dossiers)
    require(freeze_digest(manifest) == MANIFEST, "manifest_mismatch")
    captured = []

    def capture(request, question, pages, docs, history, _now, _cap):
        require(question == QUESTION and not history and request.rsplit("/", 1)[-1] == REQUEST_ID,
                "question_scope_mismatch")
        expected = [(d["sha256"], d["pages"], d["id"], d["path"], d["field"])
                    for d in dossiers[BKD]["included_docs"]]
        actual = [(d["sha256"], d["pages"], d["id"], d["source_path"], d["field_path"]) for d in docs]
        require(actual == expected and all(page["scope"] == [BKD] for page in pages), "dossier_drift")
        registry, wire, payload, _, unique = build_request(REQUEST_ID, question, history, pages, docs, entries, MANIFEST)
        require(len(unique) == 4 and sum(unique.values()) == 80, "dossier_drift")
        observed = measure(payload, unique, cache)
        require(observed["estimate"] <= EXTENDED and observed["local_text_bytes"] <= PARSED_BYTES_LIMIT,
                "context_over_cap")
        captured.append(Prepared(commit, MANIFEST, wire, encoded(payload), tuple(unique.items()),
                                 observed["estimate"], observed["sparse_pages"], observed["wire_bytes_max_handles"],
                                 observed["estimated_cold_micro_usd"], registry))
        return "mock_preflight", None, {}

    with TemporaryDirectory(prefix="dc04a-preflight-") as direc:
        root = Path(direc)
        native = NativeD1(cache, Ledger(root / "ledger"), manifest=manifest)
        native.send = OfflineConsultant._reject_send
        native.dispatch = capture
        pilot = Pilot(entries, dossiers, cache, Journal(root / "journal"), native, owner_dc02=True)
        peer = "127.0.0.1"
        result = pilot.ask(peer, pilot.open(peer), REQUEST_ID, QUESTION)
    require(result["status"] == "mock_preflight" and len(captured) == 1 and native.chat_posts == 0
            and result["material_scope"] == {BKD: "full_available"}, "dossier_drift")
    return captured[0]


def inspect_ledger(path):
    """Read under the existing lock without creating files or maintaining the ledger."""
    if path is None:
        return {"status": "not_run", "owner_go": "blocked"}
    path = Path(path)
    if path.is_symlink() or not path.is_dir() or path.stat().st_mode & 0o077:
        raise Stopped("ledger_directory_must_be_private")
    require(not any((path / name).is_symlink() for name in (".lock", "ledger.json")), "ledger_path_invalid")
    with (path / ".lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_SH)
        state = json.loads((path / "ledger.json").read_text(encoding="utf-8"))
    operations = state["operations"]
    original = operations.get(ORIGINAL_UPLOAD, {})
    owner_rows = [row for row in operations.values() if row["state"] != "cancelled"
                  and row.get("profile") == "owner"]
    active = [row for row in owner_rows if row.get("campaign") == CAMPAIGN]
    accounted = sum(map(Ledger.accounted, active))
    held = [row for row in owner_rows if row["state"] in {"unknown", "inflight", "reserved"}]
    counts = {"budget_micro_usd": max(0, OWNER["budget"] - accounted),
              "spendable_micro_usd": max(0, OWNER["budget"] - OWNER["reserve_disabled"] - accounted),
              "pages": max(0, OWNER["pages"] - sum(row.get("pages", 0) for row in active))}
    for key in ("normal", "extended", "upload", "status", "delete", "calibration"):
        counts[key] = max(0, OWNER[key] - sum(row["kind"] == key or row.get("slot") == key for row in active))
    counts["chats"] = max(0, OWNER["chats"] - sum(row["kind"] in {"normal", "extended", "calibration"}
                                                  for row in active))
    original_state = original.get("state")
    known_states = {"unknown", "inflight", "reserved", "cancelled", "settled"}
    status = ("blocked_unknown_or_pending" if held else
              "original_operation_missing" if ORIGINAL_UPLOAD not in operations else "read_only_complete")
    return {"status": status, "owner_go": "blocked",
            "original_status": original_state if original_state in known_states else "not_found",
            "original_accounted_micro_usd": Ledger.accounted(original) if original_state in known_states else None,
            "unknown_or_pending_count": len(held), "remaining_limits": counts}


@dataclass(frozen=True)
class MockContract:
    reviewed_at: int
    terms_digest: str
    evidence: tuple
    model_alias: str = ALIAS
    model_version: str = VERSION
    origin: str = ORIGIN
    parser: str = PURPOSE
    max_context: int = MODEL_CONTEXT
    max_output: int = OUTPUT
    rates: tuple = tuple(sorted(RATES.items()))
    ttl: int = PARSE_TTL


@dataclass(frozen=True, repr=False)
class MockPermit:
    commit: str
    manifest: str
    wire: str
    payload_digest: str
    request_id: str
    contract_digest: str
    key_digest: str
    account: str
    project: str
    ledger_path: str
    operations: tuple
    limits: tuple
    expires: int
    accepted_residual_risk: bool


def proposed_mock_permit(prepared, contract, ledger, expiry):
    return MockPermit(prepared.commit, prepared.manifest, prepared.wire, prepared.payload_digest,
                      REQUEST_ID, digest(encoded(asdict(contract)).encode()), digest(MOCK_KEY.encode()),
                      "mock-account", "mock-project", str(ledger.path.resolve()),
                      (4, 80, 1, 0, 0, 0), tuple(sorted(EXACT_LIMITS.items())), expiry, True)


def bind_payload(prepared, bindings, now):
    payload = json.loads(prepared.logical_payload)
    parts = payload["messages"][-1]["content"]
    require(set(bindings) == {sha for sha, _ in prepared.files}, "binding_unavailable")
    ids = set()
    for index, (sha, _) in enumerate(prepared.files):
        binding = bindings[sha]
        handle = binding.get("id", "")
        require(isinstance(handle, str) and FILE_ID.fullmatch(handle) and handle not in ids
                and binding.get("sha256") == sha and binding.get("purpose") == binding.get("parser") == PURPOSE
                and type(binding.get("created")) is int and binding["created"] <= now + 30
                and type(binding.get("expires")) is int and binding["expires"] > now + CHAT_TIMEOUT + 30
                and binding["expires"] - binding["created"] == PARSE_TTL
                and parts[index] == {"type": "file", "file_id": f"OFFLINE_SLOT_{index + 1}"},
                "binding_unavailable")
        ids.add(handle)
        parts[index]["file_id"] = handle
    return payload


def normalizes_to_preflight(body, prepared, bindings):
    try:
        payload = json.loads(body)
        parts = payload["messages"][-1]["content"]
        for number, (sha, _) in enumerate(prepared.files, 1):
            if parts[number - 1] != {"type": "file", "file_id": bindings[sha]["id"]}:
                return False
            parts[number - 1]["file_id"] = f"OFFLINE_SLOT_{number}"
        return encoded(payload) == prepared.logical_payload
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def account_chat(result):
    usage = result.get("usage")
    def require_usage(reason):
        return ProviderFailure("financial_accounting", reason)

    if not isinstance(usage, dict):
        raise require_usage("usage_missing_or_invalid")
    counts = {key: usage.get(key) for key in USAGE_KEYS}
    if any(type(value) is not int or value < 0 for value in counts.values()):
        raise require_usage("incomplete_usage")
    prompt, hit, miss, completion, total = counts.values()
    if prompt != hit + miss or total != prompt + completion:
        raise require_usage("incomplete_usage")
    details = usage.get("completion_tokens_details")
    details_invalid = details is not None and not isinstance(details, dict)
    if isinstance(details, dict) and "reasoning_tokens" in details:
        reasoning = details["reasoning_tokens"]
        details_invalid = type(reasoning) is not int or not 0 <= reasoning <= completion
        if not details_invalid:
            counts["reasoning_tokens"] = reasoning
    choices = result.get("choices")
    choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else None
    message = choice.get("message") if isinstance(choice, dict) else None
    drift = (result.get("model") != ALIAS or bool(usage.get("server_tool_use")) or
             not isinstance(message, dict) or bool(message.get("tool_calls") or message.get("server_tool_calls")) or
             (isinstance(choice, dict) and choice.get("finish_reason") == "tool_calls"))
    billable = result.get("model") == ALIAS and not usage.get("server_tool_use") and (
        not isinstance(message, dict) or not (message.get("tool_calls") or message.get("server_tool_calls")))
    finish = choice.get("finish_reason") if isinstance(choice, dict) else None
    hold = "provider_contract_drift" if drift or details_invalid else "incomplete_finish" if finish != "stop" else None
    cost = token_cost(prompt, hit, completion) if billable else 0
    return cost, {"usage": counts, "cost_known": bool(billable), "hold_reason": hold,
                  "accounting_issue": "invalid_reasoning_usage" if details_invalid else None,
                  "overage": total > MODEL_CONTEXT or completion > OUTPUT}


class MockLab:
    """The only executable native transport here is an explicitly injected MockTransport."""
    def __init__(self, entries, dossiers, cache, transport, *, clock=time.time):
        require(type(transport) is httpx.MockTransport, "mock_transport_required")
        self.work = TemporaryDirectory(prefix="dc04a-mock-")
        self.private = Path(self.work.name)
        self.ledger = Ledger(self.private / "ledger")
        self.entries, self.dossiers, self.cache = entries, dossiers, Path(cache)
        self.transport, self.clock = transport, clock

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.work.cleanup()

    def _validate(self, plan, permit, contract, head):
        require(type(permit) is MockPermit and type(contract) is MockContract, "permit_required")
        now = self.clock()
        expect = MockContract(contract.reviewed_at, contract.terms_digest, contract.evidence)
        require(contract == expect and type(contract.reviewed_at) is int
                and now - 86400 <= contract.reviewed_at <= now
                and bool(re.fullmatch("[a-f0-9]{64}", contract.terms_digest))
                and len(contract.evidence) >= 2
                and all(url.startswith("https://api-docs.deepseek.com/") for url in contract.evidence),
                "contract_unreviewed")
        require(type(permit.expires) is int and now < permit.expires <= contract.reviewed_at + 86400,
                "go_expired")
        require(head == plan.commit and permit.accepted_residual_risk is True
                and permit == proposed_mock_permit(plan, contract, self.ledger, permit.expires),
                "permit_mismatch")

    def run(self, plan, permit, contract, *, head):
        start = time.monotonic()
        def check_plan():
            require(prepare_materials(self.entries, self.dossiers, self.cache, head).identity == plan.identity,
                    "wire_drift")

        self._validate(plan, permit, contract, head)
        check_plan()
        bindings = {}
        actual = None
        times = dict(upload=0, chat=0, local_verification=0, total=0)
        candidate = None
        verified = None
        status = "completed"

        def receive(request):
            nonlocal actual
            if request.url.path == "/chat/completions":
                body = request.read()
                if not normalizes_to_preflight(body, plan, bindings):
                    raise ProviderFailure("request_validation", "wire_drift")
                actual = digest(body)
                (self.private / "actual-request.sha256").write_text(actual + "\n", encoding="ascii")
            response = self.transport.handle_request(request)
            if request.url.path == "/chat/completions":
                response.request = request
                # Mirror the existing boundary's size limit. Capture before its parser sees the body.
                # Preserve the decoded HTTP entity before parsing or accounting.
                # The processing copy carries no transport compression headers.
                headers = httpx.Headers(response.headers)
                for key in ("content-encoding", "content-length"):
                    headers.pop(key, None)
                body_chunks = response.iter_bytes(chunk_size=64 * 1024)
                with (self.private / "native-response.bin").open("xb") as file:
                    size = 0
                    for chunk in body_chunks:
                        size += len(chunk)
                        if size > 2_000_000:
                            raise ProviderFailure("response_read", "response_too_large",
                                                  http_status=response.status_code)
                        file.write(chunk)
                    file.flush()
                    os.fsync(file.fileno())
                return httpx.Response(response.status_code, headers=headers,
                                      content=(self.private / "native-response.bin").read_bytes())
            return response

        native = NativeD1(self.cache, self.ledger, manifest=freeze(self.entries, self.dossiers),
                          fixture=httpx.MockTransport(receive))
        native.account, native.project, native.principal = permit.account, permit.project, permit.key_digest
        operations = {CHAT_KEY + "/upload/" + sha: {"kind": "upload", "reserve": pages * PAGE_PRICE, "pages": pages}
                      for sha, pages in plan.files}
        operations[CHAT_KEY] = {"kind": "calibration", "slot": "extended", "reserve": CAL_POST_RESERVE}
        raw_files = {}
        for sha, _ in plan.files:
            with (self.cache / (sha + ".pdf")).open("rb") as artifact:
                raw = artifact.read(MAX_SIZE + 1)
            require(len(raw) <= MAX_SIZE and digest(raw) == sha, "dossier_drift")
            raw_files[sha] = raw

        with self.ledger.transaction() as state:
            self._validate(plan, permit, contract, head)
            remaining = self.ledger.summary(state, "mock-dc04a", OWNER["budget"], campaign=CAMPAIGN)
            require(remaining["remaining_micro_usd"] - OWNER["reserve_disabled"] >= PROPOSED_RESERVE,
                    "campaign_budget_exhausted")
            self.ledger.reserve(state, "mock-dc04a", digest(encoded(asdict(permit)).encode()), "owner",
                                self.clock(), EXACT_LIMITS, operations, campaign=CAMPAIGN)
            try:
                for sha, pages in plan.files:
                    self._validate(plan, permit, contract, head)
                    check_plan()
                    sent_at = self.clock()
                    raw = raw_files[sha]
                    operation = CHAT_KEY + "/upload/" + sha

                    def upload():
                        return native.send("POST", "/files", data={"purpose": PURPOSE,
                            "expires_after[anchor]": "created_at", "expires_after[seconds]": str(PARSE_TTL)},
                            files={"file": (sha + ".pdf", raw, "application/pdf")}, timeout=UPLOAD_TIMEOUT)

                    def interpret(response):
                        item = native.file_snapshot(response, sha, len(raw), self.clock())
                        if item["created"] < sent_at - 30:
                            raise ProviderFailure("file_metadata_validation", "binding_age_mismatch")
                        if any(old["id"] == item["id"] and old["sha256"] != sha
                               for old in state["bindings"].values()):
                            raise ProviderFailure("file_metadata_validation", "id_collision")
                        state["bindings"][native.file_key(sha)] = item
                        return pages * PAGE_PRICE, {}

                    started = time.monotonic()
                    try:
                        self.ledger.operate(state, operation, upload, interpret)
                    finally:
                        times["upload"] += round((time.monotonic() - started) * 1000)

                check_plan()
                for sha, _ in plan.files:
                    item = native.binding(state, sha)
                    require(item is not None and item["bytes"] == len(raw_files[sha]), "binding_unavailable")
                    bindings[sha] = item
                payload = bind_payload(plan, bindings, self.clock())
                self._validate(plan, permit, contract, head)
                def account(response):
                    cost, facts = account_chat(response)
                    if self.clock() >= permit.expires and not facts["hold_reason"]:
                        facts["hold_reason"] = "go_expired"
                    return cost, facts

                started = time.monotonic()
                try:
                    result = self.ledger.operate(state, CHAT_KEY,
                        lambda: native.send("POST", "/chat/completions", payload=payload, timeout=CHAT_TIMEOUT),
                        account)
                    content = result["choices"][0]["message"].get("content")
                    candidate = content.encode("utf-8", errors="surrogatepass") if isinstance(content, str) else None
                finally:
                    times["chat"] = round((time.monotonic() - started) * 1000)
            except (Stopped, OSError, ValueError, subprocess.SubprocessError) as error:
                status = str(error) if isinstance(error, Stopped) else "wire_drift"
            finally:
                self.ledger.cancel_unstarted(state, operations)
            rows = [state["operations"][key] for key in operations]
            chat_row = state["operations"][CHAT_KEY]

        if status == "completed" and candidate is not None:
            started = time.monotonic()

            def replay(logical):
                require(encoded(logical) == plan.logical_payload, "wire_drift")
                return MockReply(candidate)

            try:
                with OfflineConsultant(self.entries, self.dossiers, self.cache, replay) as advisor:
                    verified = advisor.ask(QUESTION, request_id=REQUEST_ID)
                if verified["status"] == "invalid_contract":
                    status = "invalid_candidate"
                elif advisor.mock_calls != 1:
                    status = "wire_drift"
            except (Stopped, OSError, ValueError, subprocess.SubprocessError):
                status = "wire_drift"
            finally:
                times["local_verification"] = round((time.monotonic() - started) * 1000)
        elif status == "completed":
            status = "invalid_candidate"
        # Preserve a partial response's A even when the current policy withholds B.
        if candidate is None and (self.private / "native-response.bin").is_file():
            try:
                content = json.loads((self.private / "native-response.bin").read_bytes())["choices"][0]["message"]["content"]
                if isinstance(content, str):
                    candidate = content.encode("utf-8", errors="surrogatepass")
            except (KeyError, TypeError, IndexError, ValueError):
                pass
        times["total"] = round((time.monotonic() - start) * 1000)
        counts = chat_row.get("usage", {})
        telemetry = {
            "status": status, "timing_ms": times,
            "tokens": {key: counts.get(source) for key, source in
                       zip(("prompt", "hit", "miss", "completion", "total", "reasoning"),
                           USAGE_KEYS + ("reasoning_tokens",), strict=True)},
            "cost_micro_usd": {"known": sum(row.get("cost", 0) for row in rows if row.get("cost_known", True)),
                               "held": sum(Ledger.accounted(row) for row in rows if row["state"] == "unknown"),
                               "reserved": PROPOSED_RESERVE},
            "estimates_micro_usd": {"chat": plan.cold_estimate - 80 * PAGE_PRICE, "pdf": 80 * PAGE_PRICE,
                                    "total": plan.cold_estimate},
            "diagnostics": ([r["provider_failure"]["safe_reason_code"] for r in rows if "provider_failure" in r]
                            + ([chat_row["accounting_issue"]] if chat_row.get("accounting_issue") else [])),
            "private_values": [item["id"] for item in bindings.values()],
        }
        return candidate, verified, telemetry, actual


def run_live(args=None):
    if args is None or args.stage is None:
        raise Stopped("live_not_authorized")
    from .dc04b import cli
    return cli(args)


def git_head():
    cmd = ["git", "-c", "core.fsmonitor=false", "-C", str(ROOT)]
    require(not subprocess.check_output(cmd + ["status", "--porcelain", "--untracked-files=all"],
                                       text=True, timeout=20).strip(), "checkout_dirty")
    return subprocess.check_output(cmd + ["rev-parse", "HEAD"], text=True, timeout=20).strip()


def preflight(site, cache, head, ledger_path=None):
    require(git_head() == head, "head_mismatch")
    tokenizer = Path(cache) / TOKENIZER_NAME
    with tokenizer.open("rb") as stream:
        raw = stream.read(10_000_001)
    require(len(raw) <= 10_000_000 and digest(raw) == TOKENIZER_SHA, "tokenizer_integrity_error")
    entries, dossiers, _ = load(site, cache)
    plan = prepare_materials(entries, dossiers, cache, head)
    return {"passed": True, "status": "ready_for_offline_acceptance", "live": "live_not_run",
            "owner_go": "blocked", "provider_operations": 0, "score": "not_run",
            "question_id": QUESTION_ID, "site_commit": COMMIT, "manifest": plan.manifest,
            "request_id": REQUEST_ID, "wire": plan.wire, "logical_payload_sha256": plan.payload_digest,
            "source_registry_sha256": plan.registry.wire_identity, "prompt_version": PROMPT_VERSION,
            "ordered_pdf_sha256": [sha for sha, _ in plan.files], "pdfs": 4, "pages": 80,
            "local_estimated_tokens": plan.estimate, "local_wire_bytes_max_handles": plan.wire_bytes,
            "sizing_method": "pinned_tokenizer_poppler_layout",
            "sparse_pages": plan.sparse_pages, "local_cold_estimate_micro_usd": plan.cold_estimate,
            "proposed_reserve_micro_usd": PROPOSED_RESERVE, "verified_billable_bound": None,
            "financial_terms": "unreviewed", "ledger": inspect_ledger(ledger_path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    offline = commands.add_parser("preflight")
    offline.add_argument("--site", type=Path, default=os.getenv("SATURN_SOURCE"))
    offline.add_argument("--cache", type=Path, default=os.getenv("DS_DC_CACHE"))
    offline.add_argument("--commit", required=True)
    offline.add_argument("--ledger", type=Path)
    live = commands.add_parser("live")
    live.add_argument("--stage", choices=("replay", "preflight"), help=argparse.SUPPRESS)
    live.add_argument("--commit", help=argparse.SUPPRESS)
    for name in ("site", "cache", "ledger", "receipt", "output", "offline-summary", "history-archive"):
        live.add_argument("--" + name, type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.command == "live":
            return run_live(args)
        require(args.site and args.cache, "offline_inputs_missing")
        data = preflight(args.site, args.cache, args.commit, args.ledger)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        code = str(error) if isinstance(error, Stopped) else "offline_preflight_failed"
        print(json.dumps({"passed": False, "status": code, "live": "live_not_run", "provider_operations": 0}))
        return 1
    print(json.dumps(data, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
