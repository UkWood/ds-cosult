"""Closed WSL entry for the recorded, one-shot Q01-N experiment."""
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import time
import warnings
from urllib.parse import unquote_to_bytes

import httpx

from . import dc04b_permit as permit, quality_lab as lab, recovery
from .context import TOKENIZER_NAME, TOKENIZER_SHA
from .corpus import COMMIT, digest, encoded
from .evidence_integration import MockReply, OfflineConsultant, PROMPT_VERSION
from .finance import Ledger, OWNER, Stopped
from .native import CHAT_TIMEOUT, ORIGIN, PAGE_PRICE, PARSE_TTL, PURPOSE, UPLOAD_TIMEOUT, NativeD1
from .prep import freeze, load
from .provider_failure import ProviderFailure
from .quality_report import build_report

RESPONSE = "native-response.bin"
WITHHELD = "native-response-withheld.json"
REQUEST_SHA = "actual-request.sha256"
REPORT = "report.json"
FINISH_REASONS = {"stop", "length", "content_filter", "tool_calls", "insufficient_system_resource"}
KEY_FORMAT = re.compile(r"[!-~]{1,512}")
MAX_RESPONSE = 2_000_000


def private_directory(ledger):
    return ledger.path / permit.RUN


def write_private(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    directory = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def hidden_key():
    with open("/dev/tty", "w", encoding="utf-8") as tty, warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass("DeepSeek API KEY: ", stream=tty)


def check_head(head):
    lab.require(lab.git_head() == head and head != permit.BASELINE, "head_mismatch")
    cmd = ["git", "-C", str(lab.ROOT), "merge-base", "--is-ancestor", permit.BASELINE, head]
    lab.require(subprocess.run(cmd, timeout=20, capture_output=True).returncode == 0, "head_mismatch")


def check_plan(plan, head):
    lab.require(plan.commit == head, "head_mismatch")
    lab.require(COMMIT == permit.SITE and plan.manifest == permit.MANIFEST and plan.wire == permit.WIRE
                and plan.payload_digest == permit.PAYLOAD and plan.registry.wire_identity == permit.REGISTRY
                and plan.registry.request_id == lab.REQUEST_ID and PROMPT_VERSION == "evidence-integration/1"
                and plan.files == tuple((sha, pages) for sha, pages, _ in permit.FILES), "wire_drift")


def load_plan(site, cache, head):
    check_head(head)
    with (cache / TOKENIZER_NAME).open("rb") as source:
        lab.require(digest(source.read(10_000_001)) == TOKENIZER_SHA, "tokenizer_integrity_error")
    entries, dossiers, _ = load(site, cache)
    plan = lab.prepare_materials(entries, dossiers, cache, head)
    check_plan(plan, head)
    lab.require(plan.wire_bytes == 14984, "local_wire_size_drift")
    return entries, dossiers, plan


def preflight(site, cache, head, ledger, archive):
    with ledger.transaction(maintain=False) as state:
        basis = permit.admit(state)
        permit.confirm_archive(state, archive, ledger.path.parent)
    permit.terms(time.time())
    _, _, plan = load_plan(site, cache, head)
    return dict(task="DS-DC-04B", head=head, wire=plan.wire, contract=permit.CONTRACT_DIGEST, ledger_basis=basis)


class ExperimentTransport(httpx.BaseTransport):
    """Own the experiment's route sequence and capture the actual chat entity."""
    def __init__(self, downstream, key, work, plan, bindings, clock):
        self.downstream, self.key, self.work = downstream, key, work
        self.plan, self.bindings, self.clock = plan, bindings, clock
        self.next = 0
        self.chat_http_status = None
        self.response_entity = b""
        self.capture = "absent"

    def handle_request(self, request):
        route = "/files" if self.next < len(self.plan.files) else "/chat/completions"
        if (self.next > len(self.plan.files) or request.method != "POST"
                or str(request.url) != ORIGIN + route or self.clock() >= permit.EXPIRES):
            raise ProviderFailure("request_validation", "experiment_route_or_expiry")
        if route == "/chat/completions":
            body = request.read()
            if not lab.normalizes_to_preflight(body, self.plan, self.bindings):
                raise ProviderFailure("request_validation", "wire_drift")
            write_private(self.work / REQUEST_SHA, (digest(body) + "\n").encode("ascii"))
        self.next += 1
        request.headers["Authorization"] = "Bearer " + self.key
        response = self.downstream.handle_request(request)
        if route != "/chat/completions":
            return response

        response.request = request
        body = bytearray()
        try:
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                if len(body) + len(chunk) > MAX_RESPONSE:
                    raise ProviderFailure("response_read", "response_too_large", http_status=response.status_code)
                body.extend(chunk)
            headers = httpx.Headers(response.headers)
            for name in ("content-encoding", "content-length"):
                headers.pop(name, None)
            self.chat_http_status = response.status_code
            return httpx.Response(response.status_code, headers=headers, content=bytes(body))
        finally:
            self.response_entity = bytes(body)
            try:
                # Scan the credential and common JSON or URL encodings before any write.
                unescaped = re.sub(rb"\\+u00([a-fA-F0-9]{2})",
                                   lambda match: bytes.fromhex(match[1].decode()), unquote_to_bytes(self.response_entity))
                if self.key.encode() in body or self.key.encode() in unescaped:
                    self.capture = "credential_detected"
                    write_private(self.work / WITHHELD, encoded(dict(
                        reason=self.capture, size=len(body), response_sha256=digest(body))).encode())
                else:
                    write_private(self.work / RESPONSE, self.response_entity)
                    self.capture = "private_raw"
            finally:
                response.close()


def fields(envelope):
    model = envelope.get("model")
    choices = envelope.get("choices")
    choice = choices[0] if isinstance(choices, list) and len(choices) == 1 else {}
    if not isinstance(choice, dict):
        choice = {}
    message = choice.get("message")
    if not isinstance(message, dict):
        message = {}
    finish = choice.get("finish_reason")
    tools = bool(message.get("tool_calls") or message.get("server_tool_calls") or finish == "tool_calls")
    usage = envelope.get("usage")
    tools |= isinstance(usage, dict) and bool(usage.get("server_tool_use"))
    content = message.get("content")
    return model, finish, tools, content.encode("utf-8", errors="surrogatepass") if isinstance(content, str) else None


def account(envelope):
    cost, facts = lab.account_chat(envelope)
    model, finish, tools, _ = fields(envelope)
    if facts["cost_known"] and not tools:
        # Finish and candidate validity are evaluated after financial settlement.
        facts["hold_reason"] = None
    else:
        cost = 0
        facts.update(cost_known=False, hold_reason="provider_contract_drift")
    return cost, facts | dict(
        observed_model_alias=model if model == lab.ALIAS else "other" if isinstance(model, str) else None,
        finish_reason=finish if isinstance(finish, str) and finish in FINISH_REASONS else None)


def audit(ledger, state):
    rows = {key: state["operations"][key] for key in permit.operations()}
    active = [row for row in rows.values() if row["state"] != "cancelled"]
    chat = rows[permit.CHAT]
    summary = ledger.summary(state, permit.RUN, OWNER["budget"], recovery.CAMPAIGN)
    financial = dict(
        chat_state=chat["state"],
        campaign_remaining_micro_usd=summary["remaining_micro_usd"],
        campaign_spendable_micro_usd=max(0, summary["remaining_micro_usd"] - OWNER["reserve_disabled"]),
        campaign_held_micro_usd=summary["held_micro_usd"],
        original_held_micro_usd=recovery.HOLD, valuation="approved_peak_rates",
        pdf_reserve_micro_usd=18_000, chat_reserve_micro_usd=permit.CHAT_RESERVE,
        campaign_page_attempts=summary["page_attempts"], campaign_operations=summary["operations"],
        attempted_uploads=sum(row["state"] in {"settled", "unknown", "inflight"} and row["kind"] == "upload"
                              for row in active),
        attempted_chat=int(chat["state"] in {"settled", "unknown", "inflight"}))
    costs = dict(known=sum(row.get("cost", 0) for row in active if row.get("cost_known", True)),
                 held=sum(Ledger.accounted(row) for row in active if row["state"] != "settled"),
                 reserved=permit.LIMITS["budget"])
    return financial, costs, chat, active


def replay_report(ledger):
    with ledger.transaction(maintain=False) as state:
        if not state.get("dc04b_events"):
            return None
        financial, costs, _, _ = audit(ledger, state)
        events = state["dc04b_events"]
        work = private_directory(ledger)
        saved = work / REPORT
        if len(events) == 2 and events[1]["kind"] == "report_saved":
            raw = saved.read_bytes()
            lab.require(digest(raw) == events[1]["digest"], "saved_report_integrity_error")
            return json.loads(raw)
        if len(events) == 1 and saved.is_file():
            # The sidecar is published atomically before its checksum is attached to the ledger.
            report = json.loads(saved.read_bytes())
            scope = events[0]["permit"]
            provenance = report.get("provenance", {})
            lab.require(report.get("schema") == "ds-dc-04b-quality-report/1"
                        and provenance.get("commit") == scope["head"]
                        and provenance.get("logical_wire_sha256") == scope["wire"],
                        "saved_report_integrity_error")
            return report
        return dict(task="DS-DC-04B", status="previous_run_interrupted", expert_score="NOT RUN",
                    financial=financial, telemetry={"cost_micro_usd": costs},
                    response_retained=(work / RESPONSE).is_file())


def unique_fields(pairs):
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate_response_key")
    return value


def response_entity(raw):
    try:
        value = json.loads(raw, object_pairs_hook=unique_fields)
    except (OSError, ValueError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


def run_experiment(entries, dossiers, cache, plan, ledger, basis, *, key_reader=hidden_key,
                   transport=None, clock=time.time, archive=None):
    timings = dict(upload=0, chat=0, local_verification=0, total=0)
    lab.require((transport is None and archive is not None and ledger.path == permit.canonical_ledger()
                 and "microsoft" in os.uname().release.lower())
                or type(transport) is httpx.MockTransport, "wsl_or_mock_required")
    permit.terms(clock())
    check_plan(plan, lab.git_head())
    with ledger.transaction(maintain=False) as state:
        lab.require(permit.admit(state) == basis, "ledger_changed")

    pdfs = {}
    manifest = freeze(entries, dossiers)
    for sha, pages, size in permit.FILES:
        with (cache / (sha + ".pdf")).open("rb") as source:
            raw = source.read(size + 1)
        lab.require(len(raw) == size and digest(raw) == sha and any(
            doc["sha256"] == sha and doc["bytes"] == size and doc["pages"] == pages
            for doc in manifest["files"]), "dossier_drift")
        pdfs[sha] = raw

    work = private_directory(ledger)
    bindings = {}
    status = "completed"
    # The campaign lock covers both the atomic reservation and every paid request.
    # No maintenance runs here, so the historical rows remain byte-equivalent as values.
    with ledger.transaction(maintain=False) as state:
        lab.require(permit.admit(state) == basis, "ledger_changed")
        permit.terms(clock())
        scope = permit.confirm_archive(state, archive, ledger.path.parent) if archive is not None else None
        work.mkdir(mode=0o700, exist_ok=True)
        lab.require(not work.is_symlink() and work.stat().st_uid == os.getuid()
                    and not work.stat().st_mode & 0o077 and not any(work.iterdir()), "private_work_invalid")
        key = key_reader()
        lab.require(isinstance(key, str) and KEY_FORMAT.fullmatch(key), "credential_invalid")
        check_plan(plan, lab.git_head())
        approval = permit.issue(state, basis, plan.commit, key, clock(), scope)
        started = time.monotonic()
        permit.reserve(ledger, state, approval, clock())
        operations = permit.operations()
        boundary = None
        try:
            with transport if transport is not None else httpx.HTTPTransport(retries=0, trust_env=False) as downstream:
                boundary = ExperimentTransport(downstream, key, work, plan, bindings, clock)
                native = NativeD1(cache, ledger, manifest=manifest, fixture=boundary)
                native.account, native.project, native.principal = approval["account"], approval["project"], approval["principal"]
                for sha, pages, _ in permit.FILES:
                    send_at = clock()
                    raw = pdfs[sha]

                    def upload():
                        return native.send("POST", "/files", data={"purpose": PURPOSE,
                            "expires_after[anchor]": "created_at", "expires_after[seconds]": str(PARSE_TTL)},
                            files={"file": (sha + ".pdf", raw, "application/pdf")}, timeout=UPLOAD_TIMEOUT)

                    def parse(result):
                        item = native.file_snapshot(result, sha, len(raw), clock())
                        if key in item["id"]:
                            raise ProviderFailure("file_metadata_validation", "credential_in_binding")
                        if item["created"] < send_at - 30:
                            raise ProviderFailure("file_metadata_validation", "binding_age_mismatch")
                        if any(old.get("id") == item["id"]
                               for old in (*state["bindings"].values(), *bindings.values())):
                            raise ProviderFailure("file_metadata_validation", "id_collision")
                        bindings[sha] = item
                        return pages * PAGE_PRICE, dict(provider_binding=item)

                    tick = time.monotonic()
                    try:
                        ledger.operate(state, permit.CHAT + "/upload/" + sha, upload, parse)
                    finally:
                        timings["upload"] += round((time.monotonic() - tick) * 1000)

                payload = lab.bind_payload(plan, bindings, clock())
                def settle(_result):
                    envelope = response_entity(boundary.response_entity)
                    if not envelope:
                        raise ProviderFailure("json_decode", "invalid_json")
                    return account(envelope)

                tick = time.monotonic()
                try:
                    ledger.operate(state, permit.CHAT, lambda: native.send(
                        "POST", "/chat/completions", payload=payload, timeout=CHAT_TIMEOUT), settle)
                finally:
                    timings["chat"] = round((time.monotonic() - tick) * 1000)
        except Stopped as error:
            status = str(error)
        finally:
            ledger.cancel_unstarted(state, operations)
        financial, costs, chat, rows = audit(ledger, state)

    model, finish, tools, candidate = fields(response_entity(boundary.response_entity) if boundary else {})
    candidate_status = "unavailable"
    result = None
    if candidate is not None:
        candidate_status = "incomplete" if finish != "stop" else "unavailable"
    if (candidate is not None and finish == "stop" and model == lab.ALIAS and not tools
            and boundary and boundary.capture != "absent" and boundary.chat_http_status is not None
            and 200 <= boundary.chat_http_status < 300):
        def replay(payload):
            lab.require(encoded(payload) == plan.logical_payload, "wire_drift")
            return MockReply(candidate)

        tick = time.monotonic()
        try:
            with OfflineConsultant(entries, dossiers, cache, replay) as advisor:
                result = advisor.ask(lab.QUESTION, request_id=lab.REQUEST_ID)
                lab.require(advisor.mock_calls == 1, "wire_drift")
            candidate_status = result["status"]
        except (OSError, ValueError, subprocess.SubprocessError):
            candidate_status, result = "verification_failed", None
        finally:
            timings["local_verification"] = round((time.monotonic() - tick) * 1000)
    timings["total"] = round((time.monotonic() - started) * 1000)
    counts = chat.get("usage", {})
    request_sha = (work / REQUEST_SHA).read_text().strip() if (work / REQUEST_SHA).is_file() else None
    report = build_report(question=lab.QUESTION, provenance=dict(
        question_id=lab.QUESTION_ID, site_commit=permit.SITE, commit=plan.commit, manifest_sha256=plan.manifest,
        logical_wire_sha256=plan.wire, logical_payload_sha256=plan.payload_digest, actual_payload_sha256=request_sha,
        source_registry_sha256=plan.registry.wire_identity, ordered_pdf_sha256=[sha for sha, _ in plan.files],
        prompt_version=PROMPT_VERSION, request_mode="mock_native" if transport is not None else "live_native",
        provider_model=lab.ALIAS, model_settings=dict(thinking="enabled", reasoning_effort="high",
            response_format="json_object", max_tokens=8192, stream=False, tools=False, web_search=False),
        dossier=dict(pdf_count=4, page_count=80), source_registry=plan.registry.sources,
    ), candidate=candidate, result=result, telemetry=dict(
        timing_ms=timings, status=status, cost_micro_usd=costs,
        tokens=dict(zip(("prompt", "hit", "miss", "completion", "total", "reasoning"),
            (counts.get(label) for label in (*lab.USAGE_KEYS, "reasoning_tokens")), strict=True)),
        diagnostics=[row["provider_failure"]["safe_reason_code"] for row in rows if "provider_failure" in row],
        private_values=[key, approval["account"], approval["project"], str(ledger.path),
                        *[row["id"] for row in bindings.values()]],
    ))
    report.update(schema="ds-dc-04b-quality-report/1", task="DS-DC-04B",
                  status=status, candidate_status=candidate_status, financial=financial,
                  contract_digest=permit.CONTRACT_DIGEST, provider_contract=permit.contract(),
                  response_capture=boundary.capture if boundary else "absent",
                  local_sizing=dict(method="pinned_tokenizer_poppler_layout", tokens=plan.estimate,
                                    accepted_wsl_tokens=52643, wire_bytes_max_handles=plan.wire_bytes,
                                    verified_billable_bound=None),
                  observed_model_alias=model if model == lab.ALIAS else "other" if isinstance(model, str) else None,
                  finish_reason=finish if isinstance(finish, str) and finish in FINISH_REASONS else None)
    raw = encoded(report).encode()
    with TemporaryDirectory(dir=work, prefix=".report-") as stage:
        staged = Path(stage) / REPORT
        write_private(staged, raw)
        os.link(staged, work / REPORT)
        directory = os.open(work, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    with ledger.transaction(maintain=False) as state:
        state["dc04b_events"].append(dict(kind="report_saved", digest=digest(raw)))
        ledger.save(state)
    return report


def launcher_entry(stage, site, cache, head, ledger_path, receipt, output, offline_summary, archive):
    ledger = permit.open_ledger(ledger_path)
    previous = replay_report(ledger)
    if previous is not None:
        write_private(output, encoded(previous).encode())
        return 0 if stage == "replay" else 4

    if stage == "replay":
        return 3

    summary = offline_summary.read_bytes()
    acceptance = json.loads(summary)
    lab.require(acceptance.get("status") == "PASS" and acceptance.get("pin") == head
                and acceptance.get("task") == "DS-DC-04A" and acceptance.get("environment") == "WSL"
                and acceptance.get("isolation") == "linux_network_namespace_plus_python_socket_audit"
                and acceptance.get("checks", {}).get("full_regression") == "PASS"
                and acceptance.get("checks", {}).get("dc04a_pinned_wire_mock") == "PASS",
                "offline_preflight_required")
    lab.require(stage == "preflight", "offline_preflight_required")
    parent = os.environ.get("DC04B_PARENT_NETNS")
    lab.require(os.environ.get("DC03C_GUARD_ACTIVE") == "1" and parent
                and os.readlink("/proc/self/ns/net") != parent, "offline_isolation_required")
    values = preflight(site, cache, head, ledger, archive)
    values["offline_acceptance"] = digest(summary)
    write_private(receipt, encoded(values).encode())
    return 0


def execute_prepared(site, cache, head, ledger, receipt, summary, archive):
    """Called in process by the coordinator after it runs and checks the isolated worker."""
    lab.require("microsoft" in os.uname().release.lower() and not os.environ.get("DC03C_GUARD_ACTIVE"),
                "trusted_wsl_required")
    lab.require(receipt.is_file() and not receipt.is_symlink() and not receipt.stat().st_mode & 0o077,
                "offline_preflight_required")
    proof = json.loads(receipt.read_bytes())
    lab.require(proof == dict(task="DS-DC-04B", head=head, wire=permit.WIRE,
                              contract=permit.CONTRACT_DIGEST, ledger_basis=proof.get("ledger_basis"),
                              offline_acceptance=digest(summary)),
                "offline_preflight_required")
    entries, dossiers, plan = load_plan(site, cache, head)
    return run_experiment(entries, dossiers, cache, plan, ledger, proof["ledger_basis"], archive=archive)


def cli(args):
    try:
        return launcher_entry(args.stage, args.site, args.cache, args.commit, args.ledger,
                              args.receipt, args.output, args.offline_summary, args.history_archive)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, EOFError,
            KeyboardInterrupt, getpass.GetPassWarning) as error:
        code = str(error) if isinstance(error, Stopped) else "experiment_blocked"
        print(json.dumps({"status": code}))
        return 1
