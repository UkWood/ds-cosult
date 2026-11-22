"""Strictly offline, two-checkout replay of the accepted private Q01-N response."""
import argparse
from contextlib import contextmanager
import errno
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory


BASELINE = "2dac638843b1ce4ac7506de8fb3e3bb222d2199d"
ACCEPTED_REPORT = "062a7656a1afdb324506e80392f8bbba5f2be6282cb4411508501a6e7ce501ff"
ACTUAL_PAYLOAD = "a1114cded7217d2c4cbd807db1cb3fd843048cbd3310035bc772084421bd9a2d"
CANDIDATE = "5fbae4db9a008331e1f1f1314144856b120a65901172f7d48199b38389018c7c"
HISTORICAL_PROMPT = "evidence-integration/1"
CONTRACT = "candidate-answer/2.1"
MODEL = "deepseek-flash"
RUN_DIRECTORY = "dc04b-q01-n"
MANUAL = "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a"
CANDIDATE_HANDOFF = "candidate.private"
BASELINE_HANDOFF = "replay-baseline.private.json"
HISTORY_FILES = {"ledger.json": 16_000_000, "report.json": 2_000_000,
                 "actual-request.sha256": 65, "native-response.bin": 2_000_000}
USAGE_FIELDS = {"prompt": "prompt_tokens", "hit": "prompt_cache_hit_tokens",
                "miss": "prompt_cache_miss_tokens", "completion": "completion_tokens",
                "total": "total_tokens", "reasoning": "reasoning_tokens"}
EXPECTED_ROLES = {
    "C1": ("symptom", {(2, 0)}),
    "C2": ("possible_cause", {(2, 0), (2, 1)}),
    "C3": ("possible_cause", {(2, 0), (3, 1)}),
    "C4": ("conditional_action", {(2, 1), (2, 2)}),
    "C5": ("conditional_action", {(3, 1), (3, 2)}),
}
EXPECTED_PAIRS = {"C4": "C2", "C5": "C3"}


class ReplayError(ValueError):
    def __init__(self, code, status="FAIL"):
        super().__init__(code)
        self.status = status


def require(condition, reason):
    if not condition:
        raise ReplayError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def strict_object(raw, reason):
    def object_from_pairs(pairs):
        obj = dict(pairs)
        if len(obj) != len(pairs):
            raise ValueError
        return obj

    def reject_constant(_):
        raise ValueError

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=object_from_pairs,
                           parse_constant=reject_constant)
        # Check for escapes encoding lone surrogates and nonfinite numerals.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, RecursionError):
        raise ReplayError(reason) from None
    require(isinstance(value, dict), reason)
    return value


def extract_candidate(raw, expected_sha, telemetry):
    """Extract the actual UTF-8 content exactly once, without reserializing it."""
    from ds_dc.quality_lab import account_chat
    from ds_dc.provider_failure import ProviderFailure

    reason = "historical_response_invalid"
    require(isinstance(raw, bytes) and 0 < len(raw) <= HISTORY_FILES["native-response.bin"], reason)
    envelope = strict_object(raw, reason)
    choices = envelope.get("choices")
    require(envelope.get("model") == MODEL and "error" not in envelope
            and isinstance(choices, list) and len(choices) == 1, reason)
    choice = choices[0]
    require(isinstance(choice, dict) and choice.get("finish_reason") == "stop"
            and type(choice.get("index")) is int and choice["index"] == 0, reason)
    message = choice.get("message")
    require(isinstance(message, dict) and message.get("role") == "assistant"
            and message.get("function_call") is None and message.get("tool_call_id") is None
            and message.get("tool_calls") in (None, [])
            and message.get("server_tool_calls") in (None, []), reason)
    try:
        cost, usage = account_chat(envelope)
    except ProviderFailure:
        raise ReplayError(reason) from None
    require(usage["cost_known"] and not usage["hold_reason"] and not usage["accounting_issue"]
            and not usage["overage"], reason)
    # Without the already accepted telemetry, an otherwise valid substitute
    # envelope could contain the same candidate and unrelated usage.
    counts = {key: usage["usage"].get(old) for key, old in USAGE_FIELDS.items()}
    require(counts == telemetry.get("tokens")
            and cost + 18_000 == telemetry.get("cost_micro_usd", {}).get("known"),
            "historical_response_telemetry_mismatch")
    content = message.get("content")
    require(isinstance(content, str), reason)
    try:
        candidate = content.encode("utf-8")
    except UnicodeError:
        raise ReplayError(reason) from None
    require(0 < len(candidate) <= 512 * 1024 and digest(candidate) == expected_sha,
            "historical_candidate_digest_mismatch")
    return candidate


def private_fd(path, *, parent=None, directory=False, missing_code="private_history_missing"):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(path, flags | (os.O_DIRECTORY if directory else 0), dir_fd=parent)
    except FileNotFoundError:
        raise ReplayError(missing_code, "BLOCKED") from None
    except OSError as error:
        if error.errno in {errno.ELOOP, errno.ENOTDIR, errno.EISDIR, errno.EACCES, errno.EPERM}:
            raise ReplayError("private_history_permissions") from None
        raise
    info = os.fstat(fd)
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    if not expected or info.st_uid != os.getuid() or info.st_mode & 0o077:
        os.close(fd)
        raise ReplayError("private_history_permissions")
    return fd


@contextmanager
def private_directory(path, *, parent=None):
    fd = private_fd(path, parent=parent, directory=True)
    try:
        yield fd
    finally:
        os.close(fd)


def read_private(directory, name, limit, *, missing_code="private_history_missing"):
    fd = private_fd(name, parent=directory, missing_code=missing_code)
    with os.fdopen(fd, "rb") as file:
        raw = file.read(limit + 1)
    require(len(raw) <= limit, "private_history_size_invalid")
    return raw


@contextmanager
def historical_lock(ledger):
    # Refuse linked ancestors as well as linked final entries. All files inside
    # the ledger are opened through validated directory descriptors.
    require(ledger.resolve() == ledger.absolute(), "private_history_permissions")
    with private_directory(ledger) as directory:
        fd = private_fd(".lock", parent=directory)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ReplayError("private_history_busy", "BLOCKED") from None
            yield snapshot_reader(ledger, directory, fd)
        finally:
            os.close(fd)


def snapshot_reader(ledger, directory, lock):
    def same_entry(path, fd, parent=None):
        link = os.stat(path, dir_fd=parent, follow_symlinks=False)
        handle = os.fstat(fd)
        require((link.st_dev, link.st_ino) == (handle.st_dev, handle.st_ino), "private_history_changed")

    def snapshot():
        same_entry(ledger, directory)
        same_entry(".lock", lock, directory)
        with private_directory(RUN_DIRECTORY, parent=directory) as proof:
            values = {name: read_private(directory if name == "ledger.json" else proof, name, limit)
                      for name, limit in HISTORY_FILES.items()}
        values[".lock"] = read_private(directory, ".lock", 4096)
        return values

    return snapshot


def fingerprints(snapshot):
    return {name: digest(raw) for name, raw in snapshot.items()}


def historical_report(snapshot):
    """Bind the saved report, consumed reservation, balances, and sidecar."""
    from ds_dc import dc04b, dc04b_permit as permit, quality_lab as lab, recovery
    from ds_dc.finance import Ledger, Stopped

    report = strict_object(snapshot["report.json"], "historical_report_invalid")
    state = strict_object(snapshot["ledger.json"], "historical_ledger_invalid")
    require(digest(snapshot["report.json"]) == ACCEPTED_REPORT, "historical_report_digest_mismatch")
    require(snapshot["actual-request.sha256"] == (ACTUAL_PAYLOAD + "\n").encode(),
            "historical_actual_payload_mismatch")
    require(all(report.get(key) == value for key, value in {
        "schema": "ds-dc-04b-quality-report/1", "task": "DS-DC-04B", "status": "completed",
        "candidate_status": "needs_support", "derivative_copy": True, "response_capture": "private_raw",
        "observed_model_alias": MODEL, "finish_reason": "stop", "contract_digest": permit.CONTRACT_DIGEST,
        "expert_score": "NOT RUN",
    }.items()) and report.get("question") == {"id": lab.QUESTION_ID, "text": lab.QUESTION},
            "historical_report_scope_mismatch")
    require(all(report["provenance"].get(key) == value for key, value in {
        "commit": BASELINE, "site_commit": permit.SITE, "manifest_sha256": permit.MANIFEST,
        "logical_wire_sha256": permit.WIRE, "logical_payload_sha256": permit.PAYLOAD,
        "source_registry_sha256": permit.REGISTRY, "actual_payload_sha256": ACTUAL_PAYLOAD,
        "prompt_version": HISTORICAL_PROMPT, "provider_model": MODEL, "request_mode": "live_native",
        "ordered_pdf_sha256": [sha for sha, _, _ in permit.FILES],
    }.items()) and report["A"]["candidate_sha256"] == CANDIDATE and report["A"]["version"] == CONTRACT,
            "historical_report_scope_mismatch")
    events = state.get("dc04b_events")
    require(isinstance(events, list) and len(events) == 2
            and events[1] == {"kind": "report_saved", "digest": ACCEPTED_REPORT},
            "historical_report_event_mismatch")
    try:
        reserved = events[0]
        approval = reserved["permit"]
        permit_sha = recovery.fingerprint(approval)
        require(reserved == {"kind": "reserved", "permit_sha": permit_sha, "permit": approval}
                and state["runs"][permit.RUN] == permit_sha, "historical_reservation_mismatch")
        require(all(approval.get(key) == value for key, value in {
            "head": BASELINE, "wire": permit.WIRE, "manifest": permit.MANIFEST,
            "logical_payload": permit.PAYLOAD, "registry": permit.REGISTRY,
            "question": lab.QUESTION_ID, "request_id": lab.REQUEST_ID,
            "approval": permit.OWNER_APPROVAL, "contract_digest": permit.CONTRACT_DIGEST,
            "expires": permit.EXPIRES, "limits": permit.LIMITS, "operations": [4, 80, 1, 0, 0, 0],
        }.items()), "historical_reservation_mismatch")
        _, incident = permit.original_history(state)
        require(approval.get("incident") == incident, "historical_cal_incident_mismatch")
        operations = permit.operations()
        rows = state["operations"]
        require({key for key, row in rows.items() if row.get("run") == permit.RUN} == set(operations)
                and all(all(rows[key].get(field) == value for field, value in expected.items())
                        and rows[key].get("profile") == "owner"
                        and rows[key].get("campaign") == recovery.CAMPAIGN
                        and rows[key].get("state") == "settled" for key, expected in operations.items()),
                "historical_operations_mismatch")
        # The historical audit only reads the supplied state. Its Ledger
        # instance belongs to disposable scratch space, never the real ledger.
        with TemporaryDirectory(prefix="dc04b-r1-audit-") as temporary:
            financial, costs, chat, _ = dc04b.audit(Ledger(Path(temporary) / "ledger"), state)
        require(financial == report["financial"] and costs == report["telemetry"]["cost_micro_usd"]
                and chat.get("finish_reason") == "stop" and chat.get("observed_model_alias") == MODEL,
                "historical_financial_mismatch")
        bindings = {sha: rows[permit.CHAT + "/upload/" + sha]["provider_binding"] for sha, _, _ in permit.FILES}
        require(all(binding["account"] == approval["account"] and binding["project"] == approval["project"]
                    and binding["bytes"] == size for sha, _, size in permit.FILES for binding in (bindings[sha],)),
                "historical_binding_mismatch")
    except (AttributeError, KeyError, TypeError, Stopped):
        raise ReplayError("historical_ledger_invalid") from None
    private_values = [approval["account"], approval["project"], *[binding["id"] for binding in bindings.values()]]
    return report, bindings, private_values


def checkout_head(stage, expected):
    from ds_dc import quality_lab as lab

    repo = Path.cwd().resolve()
    require(Path(lab.__file__).resolve().parents[1] == repo, "replay_checkout_mismatch")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True, timeout=20).stdout.strip()
    if stage == "baseline":
        require(head == BASELINE and expected in {None, BASELINE}, "replay_checkout_mismatch")
    else:
        require(isinstance(expected, str) and re.fullmatch("[0-9a-f]{40}", expected)
                and head == expected != BASELINE, "replay_checkout_mismatch")
        require(subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, head], cwd=repo,
                               capture_output=True, timeout=20).returncode == 0, "replay_checkout_mismatch")
    return head


def execute_pipeline(site, cache, report, candidate, bindings, private_values):
    import httpx
    from ds_dc import dc04b, dc04b_permit as permit, quality_lab as lab
    from ds_dc.context import TOKENIZER_NAME, TOKENIZER_SHA
    from ds_dc.corpus import encoded
    from ds_dc.evidence_answer import strict_json
    from ds_dc.evidence_integration import MockReply, OfflineConsultant
    from ds_dc.finance import Stopped
    from ds_dc.prep import load
    from ds_dc.quality_report import build_report

    with (cache / TOKENIZER_NAME).open("rb") as tokenizer:
        require(digest(tokenizer.read(10_000_001)) == TOKENIZER_SHA, "historical_tokenizer_mismatch")
    try:
        entries, dossiers, _ = load(site, cache)
        plan = lab.prepare_materials(entries, dossiers, cache, BASELINE)
        dc04b.check_plan(plan, BASELINE)
        require(plan.wire_bytes == 14984, "historical_wire_size_mismatch")
    except (OSError, ValueError, subprocess.SubprocessError):
        raise ReplayError("historical_dossier_or_wire_invalid") from None
    try:
        payload = lab.bind_payload(plan, bindings, max(binding["created"] for binding in bindings.values()))
        # Preparing a request object yields the accepted HTTP library's JSON
        # bytes without opening a client, transport, or socket.
        actual = httpx.Request("POST", "https://invalid.invalid/", json=payload).content
        require(digest(actual) == ACTUAL_PAYLOAD and lab.normalizes_to_preflight(actual, plan, bindings),
                "historical_actual_payload_mismatch")
    except (KeyError, TypeError, Stopped):
        raise ReplayError("historical_binding_mismatch") from None
    packet = strict_json(candidate)
    require(isinstance(packet, dict) and packet.get("version") == CONTRACT
            and packet.get("request_id") == lab.REQUEST_ID and packet.get("wire_identity") == permit.WIRE,
            "historical_candidate_identity_mismatch")

    def replay(logical_payload):
        require(encoded(logical_payload) == plan.logical_payload, "historical_wire_replay_mismatch")
        return MockReply(candidate)

    with OfflineConsultant(entries, dossiers, cache, replay) as advisor:
        result = advisor.ask(lab.QUESTION, request_id=lab.REQUEST_ID)
        require(advisor.mock_calls == 1
                and result["diagnostics"].get("provider_operations") == 0
                and result["diagnostics"].get("wire_identity") == permit.WIRE
                and result["diagnostics"].get("registry_fingerprint") == permit.REGISTRY,
                "historical_wire_replay_mismatch")
    telemetry = {"private_values": private_values}
    provenance = report["provenance"] | {"question_id": lab.QUESTION_ID, "source_registry": plan.registry.sources}
    derived = build_report(question=lab.QUESTION, provenance=provenance, candidate=candidate,
                           result=result, telemetry=telemetry)
    require(derived["A"]["candidate_sha256"] == CANDIDATE, "historical_candidate_digest_mismatch")
    return derived


def original_projection(candidate):
    return {
        key: [{field: value for field, value in row.items() if field not in {"verification", "publication"}}
              for row in rows]
        if key in {"claims", "evidence_extracts"} else rows
        for key, rows in candidate.items()
    }


def on_manual(location):
    return (location.get("sha256") == MANUAL
            and location.get("page") == 60 and location.get("revision") == "ЕСАН.426469.012РЭ, 203-01")


def verified_claim(claim, *, repaired):
    expected_status = "supported" if repaired else "semantic_pending"
    kind, coordinates = EXPECTED_ROLES[claim["id"]]
    verification = claim.get("verification", {})
    locations = verification.get("locations", [])
    if (claim.get("kind") != kind or verification.get("technical_status") != expected_status
            or verification.get("relation_verified") is not repaired
            or not all(verification.get(key) is True for key in (
                "schema_valid", "evidence_verified", "applicability_verified", "source_identity_verified"))
            or len(locations) != len(coordinates)
            or {(loc.get("row"), loc.get("column")) for loc in locations} != coordinates
            or not all(on_manual(loc) and loc.get("table") == 1
                       and loc.get("source") == "S4-8bbb36390626b1be" for loc in locations)):
        return False
    if not repaired:
        return verification.get("reason_codes") == ["unproved_modality_subject_or_condition"]
    normalization = verification.get("normalization", {})
    return (normalization.get("status") == "normalized"
            and set(normalization.get("verified_fields", ()))
            == {"subject", "value", "unit", "comparator", "qualifier", "condition"}
            and all(normalization.get(key) for key in ("input_form", "transformation", "reason")))


def technical_criteria(derived, *, repaired):
    claims = derived["A"]["claims"]
    return ([row.get("id") for row in claims] == list(EXPECTED_ROLES)
            and all(verified_claim(row, repaired=repaired) for row in claims))


def utility_criteria(derived):
    answer = derived["B"]
    actions = answer.get("documented_actions", [])
    facts = {item for fact in answer.get("verified_facts", []) for item in fact["claim_ids"]}
    claims = {claim["id"]: claim for claim in derived["A"]["claims"]}
    if (answer.get("status") not in {"partial", "reference"} or answer.get("export_status") != "available"
            or not isinstance(answer.get("answer"), str) or not set(EXPECTED_PAIRS.values()) <= facts
            or len(actions) != len(EXPECTED_PAIRS)
            or {action.get("claim_id"): action.get("cause_claim_id") for action in actions} != EXPECTED_PAIRS
            or answer.get("unresolved") != [derived["question"]["text"]]
            or any(claim.get("verification", {}).get("covered_parts") for claim in claims.values())):
        return False
    for action in actions:
        claim = claims.get(action["claim_id"])
        cause = claims.get(action["cause_claim_id"])
        safety = action.get("safety_conditions", [])
        citations = action.get("citations", [])
        text = action.get("text") or ""
        if (not claim or not cause or not all(verified_claim(row, repaired=True) for row in (claim, cause))
                or claim["publication"] != "published_as_documented_conditional_action"
                or len(safety) != 3
                or not all(isinstance(rule, str) and rule.strip() and rule in answer["answer"] for rule in safety)
                or len(set(safety)) != 3 or text not in answer["answer"]
                or any(value not in text for value in (claim["value"], cause["value"], cause["condition"]))
                or not citations or not all(on_manual(loc) for loc in citations)
                or {(loc.get("row"), loc.get("column")) for loc in citations if loc.get("table") == 1}
                != EXPECTED_ROLES[action["claim_id"]][1]
                or not any("bbox" in loc and "table" not in loc for loc in citations)):
            return False
    return True


def publish(directory, name, value, *, raw=False):
    # Publish a fresh mode-0600 artifact without overwriting an existing file.
    with NamedTemporaryFile("wb", dir=directory) as staged:
        payload = value if raw else (json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n").encode()
        staged.write(payload)
        staged.flush()
        os.link(staged.name, directory / name)


def run(stage, ledger, work, expected_commit):
    try:
        require(work.resolve() == work.absolute() and not work.resolve().is_relative_to(ledger.resolve()),
                "unsafe_replay_output")
        with private_directory(work):
            pass
    except (OSError, ReplayError, RuntimeError):
        print(json.dumps({"status": "FAIL", "failure_code": "unsafe_replay_output"}))
        return 2

    criteria = {"R1-03": "BLOCKED", "R1-04": "BLOCKED"}
    integrity = {"baselines": {"accepted_commit": BASELINE, "accepted_report_sha256": ACCEPTED_REPORT,
                               "actual_payload_sha256": ACTUAL_PAYLOAD, "candidate_sha256": CANDIDATE},
                 "historical_report_verified": False, "historical_actual_payload_verified": False,
                 "baseline_projection_reproduced": False,
                 "original_candidate_digest_verified": False, "candidate_projection_unchanged": False,
                 "ledger_immutable": None, "private_history_immutable": None}
    status, code = "FAIL", "offline_replay_internal_error"
    try:
        with private_directory(work) as artifacts, historical_lock(ledger) as snapshot:
            starting = snapshot()
            initial_digests = fingerprints(starting)
            try:
                report, bindings, private_values = historical_report(starting)
                integrity["historical_report_verified"] = True
                if stage == "baseline":
                    candidate = extract_candidate(starting["native-response.bin"], CANDIDATE, report["telemetry"])
                else:
                    handoff = strict_object(read_private(artifacts, BASELINE_HANDOFF, 2_000_000,
                                                         missing_code="baseline_replay_missing"),
                                            "baseline_replay_invalid")
                    require(handoff.get("history") == initial_digests and handoff.get("commit") == BASELINE,
                            "private_history_changed")
                    candidate = read_private(artifacts, CANDIDATE_HANDOFF, 512 * 1024,
                                             missing_code="baseline_replay_missing")
                    require(digest(candidate) == CANDIDATE, "historical_candidate_digest_mismatch")
                integrity["original_candidate_digest_verified"] = True
                head = checkout_head(stage, expected_commit)
                source, cache = os.getenv("SATURN_SOURCE"), os.getenv("DS_DC_CACHE")
                if not (source and cache and Path(source).is_dir() and Path(cache).is_dir()):
                    raise ReplayError("historical_dossier_missing", "BLOCKED")
                derived = execute_pipeline(Path(source), Path(cache), report, candidate, bindings,
                                           [str(ledger), *private_values])
                integrity["historical_actual_payload_verified"] = True
            finally:
                # Compare current bytes even if an independent check failed.
                try:
                    final_digests = fingerprints(snapshot())
                except (OSError, ReplayError):
                    integrity["private_history_immutable"] = False
                    raise ReplayError("private_history_changed") from None
                integrity["ledger_immutable"] = final_digests["ledger.json"] == initial_digests["ledger.json"]
                integrity["private_history_immutable"] = final_digests == initial_digests
                require(integrity["private_history_immutable"], "private_history_changed")

            if stage == "baseline":
                require(derived["A"] == report["A"] and derived["B"] == report["B"]
                        and technical_criteria(derived, repaired=False), "baseline_projection_mismatch")
                publish(work, CANDIDATE_HANDOFF, candidate, raw=True)
                publish(work, BASELINE_HANDOFF, {
                    "commit": head, "history": initial_digests, "A": derived["A"], "B": derived["B"],
                })
                return 0

            require(handoff["A"] == report["A"] and handoff["B"] == report["B"],
                    "baseline_projection_mismatch")
            integrity["baseline_projection_reproduced"] = True
            require(original_projection(derived["A"]) == original_projection(handoff["A"]),
                    "historical_candidate_projection_mismatch")
            integrity["candidate_projection_unchanged"] = True
            supported = technical_criteria(derived, repaired=True)
            utility = utility_criteria(derived)
            criteria = {"R1-03": "PASS" if supported else "FAIL", "R1-04": "PASS" if utility else "FAIL"}
            publish(work, "ab-before-after.json", {
                "schema": "ds-dc-04b-r1-replay/1", "question": report["question"], "expert_score": "NOT RUN",
                "A": original_projection(derived["A"]), "B_before": handoff["B"], "B_after": derived["B"],
                "verification_before": [{"id": row["id"], "publication": row["publication"],
                                         "verification": row["verification"]} for row in handoff["A"]["claims"]],
                "verification_after": [{"id": row["id"], "publication": row["publication"],
                                        "verification": row["verification"]} for row in derived["A"]["claims"]],
                "historical": {"telemetry": report["telemetry"], "financial": report["financial"],
                               "provenance": report["provenance"], "response_capture": "private_raw",
                               "finish_reason": "stop"},
                "new": {"cost_micro_usd": 0, "paid_requests": 0, "upload": 0, "chat": 0, "status": 0,
                        "delete": 0, "retry": 0, "key_prompts": 0, "live": "LIVE_NOT_RUN"},
                "grades": {"technical": criteria["R1-03"], "utility": criteria["R1-04"],
                           "published_pairs": len(derived["B"].get("documented_actions", [])),
                           "coverage_status": derived["B"]["status"]},
                "checkouts": {"before": BASELINE, "after": head},
            })
            status = "PASS" if supported and utility else "FAIL"
            code = None if status == "PASS" else "r1_utility_failed" if supported else "r1_relations_failed"
    except ReplayError as error:
        status, code = error.status, str(error)
        if status == "FAIL":
            criteria["R1-03"] = "FAIL"
    except (AssertionError, KeyError, OSError, ValueError, RecursionError, TypeError, subprocess.SubprocessError):
        criteria["R1-03"] = "FAIL"

    publish(work, "replay-checks.json", {"status": status, "failure_code": code, "criteria": criteria})
    publish(work, "integrity.json", integrity)
    print(json.dumps({"status": status, "failure_code": code}))
    return {"PASS": 0, "FAIL": 2, "BLOCKED": 3}[status]


def main():
    # The orchestrator executes this same script by absolute path while changing
    # cwd between two pinned checkouts. Give the selected checkout import priority.
    sys.path.insert(0, str(Path.cwd().resolve()))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("baseline", "r1"), required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--commit")
    options = parser.parse_args()
    return run(options.stage, options.private_root, options.artifacts, options.commit)


if __name__ == "__main__":
    raise SystemExit(main())
