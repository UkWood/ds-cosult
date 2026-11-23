"""Recorded financial decision and narrowly scoped ledger admission for DC-04B."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from . import recovery
from .context import OUTPUT
from .finance import OWNER, RATES, Ledger
from .native import MODEL_CONTEXT, ORIGIN, PAGE_PRICE, PARSE_TTL, PURPOSE
from .quality_lab import ALIAS, QUESTION_ID, REQUEST_ID, VERSION, require

BASELINE = "e1ca91cfc467565662c2b421a11a726840171b8d"
MANIFEST = recovery.MANIFEST
SITE = "084d759487bfab6e111549c9b5469711ac5fc13e"
WIRE = "ef96558d67deda9a090471a2d6947a12e11a7cce81f77fec4cbe983eaf3f9735"
PAYLOAD = "bdc21ea15355867a2a26ea85ae6c4326a08650676e2f692b0624c31ea9025e60"
REGISTRY = "8bbb36390626b1bed726994b9f0be039e934db8df0d01d29c6653716f1585fe7"
FILES = (
    ("bf07da30d1221f61a3ecdde5b40f542b90ca2a646c5dc6019997326a2c570148", 2, 167325),
    ("496ddc2786b8fb2cdfd8970947fadde6b7a045e7d86e20737f2ef694425d5890", 8, 392090),
    ("030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a", 65, 3024578),
    ("959f515c588ea8758cae0ccfdd17efaf396b31c84c4315e1b195c745d59db5db", 5, 230917),
)
RUN = "dc04b-q01-n"
CHAT = f"{recovery.CAMPAIGN}/{RUN}/{REQUEST_ID}"
LIMITS = dict(budget=500_000, normal=0, extended=1, chats=1, pages=80, upload=4,
              status=0, delete=0, calibration=1)
CHAT_RESERVE = 482_000
OWNER_APPROVAL = "8304643f0458f1045426e410bc54905a925a5ceacd01ca17d8839caa3b268479"
REVIEWED_AT = 1795383240
EXPIRES = REVIEWED_AT + 86_400
EVIDENCE = {
    "quick_start/pricing/": "b61db7d97374d37819b4dcdd41e86aa2d6bfa4d50bf059e700327727a4462e02",
    "api/create-chat-completion/": "0e36b6cd7edf17d59e61bc5588b58cd440237aac9a57d86552a6a87ea1c7416d",
    "api/create-file/": "a2d2e7a13c6ba0d1ff179fbafaf9458d6edf55e8c1b219984949159ad6b2bbe4",
    "guides/document_parsing/": "600befff8c42fee41d6ade23df1a1a676cca479de284bdc7476f1b3293ece0e0",
    "guides/thinking_mode/": "1fb7208ceb7a8aebbd6549cf158649b78414b606bb7dc9b134884e92156009d9",
}
LABEL = re.compile(r"[A-Za-z0-9_.-]{1,80}")


def contract():
    return dict(reviewed_at=REVIEWED_AT, expires=EXPIRES, model_alias=ALIAS, model_version=VERSION,
                origin=ORIGIN, context_max=MODEL_CONTEXT, max_tokens=OUTPUT,
                rates=RATES.copy(), purpose=PURPOSE, ttl=PARSE_TTL, thinking="enabled",
                reasoning_effort="high", response_format="json_object", stream=False, tools=False,
                retry=0, redirect=0, billable_bound=None, evidence={
                    "https://api-docs.deepseek.com/" + route: digest for route, digest in EVIDENCE.items()})


CONTRACT_DIGEST = "24728f1d4d3845da73905d10417bab2933e4497c5a98bd681a6d0164a63c2bd2"


def terms(now):
    require(OWNER_APPROVAL == "8304643f0458f1045426e410bc54905a925a5ceacd01ca17d8839caa3b268479",
            "financial_authorization_missing")
    require(recovery.fingerprint(contract()) == CONTRACT_DIGEST and REVIEWED_AT <= now < EXPIRES,
            "contract_unreviewed_or_expired")


def operations():
    return {CHAT + "/upload/" + sha: dict(kind="upload", reserve=pages * PAGE_PRICE, pages=pages)
            for sha, pages, _ in FILES} | {
        CHAT: dict(kind="calibration", slot="extended", reserve=CHAT_RESERVE)}


def open_ledger(path):
    path = Path(path)
    try:
        for item in (path, path / ".lock", path / "ledger.json"):
            stat = item.lstat()
            require(not item.is_symlink() and stat.st_uid == os.getuid() and not (stat.st_mode & 0o077),
                    "ledger_path_invalid")
        require(path.is_dir() and (path / "ledger.json").is_file() and (path / ".lock").is_file(),
                "ledger_path_invalid")
    except OSError:
        require(False, "ledger_path_invalid")
    return Ledger(path)


def original_history(state):
    rows = recovery.original_rows(state)
    require(set(rows) == {recovery.ORIGINAL_CHAT, *recovery.ORIGINAL_UPLOADS}, "incident_history_mismatch")
    chat = rows[recovery.ORIGINAL_CHAT]
    failed = rows[recovery.ORIGINAL_UPLOAD]
    require(chat.get("kind") == "calibration" and chat.get("slot") == "extended"
            and chat["state"] == "cancelled" and chat["reserve"] == 330_000
            and failed["state"] == "unknown" and "cost" not in failed
            and failed["reserve"] == recovery.HOLD, "incident_history_mismatch")
    for key, pages in recovery.ORIGINAL_UPLOADS.items():
        row = rows[key]
        require(row["pages"] == pages and row["reserve"] == pages * PAGE_PRICE and row["kind"] == "upload"
                and row["state"] == ("unknown" if key == recovery.ORIGINAL_UPLOAD else "cancelled"),
                "incident_history_mismatch")
    require(all(row["run"] == chat["run"] and row["campaign"] == recovery.CAMPAIGN
                and row["profile"] == "owner" for row in rows.values()), "incident_history_mismatch")

    events = state.get("recovery_events", [])
    require(isinstance(events, list) and len(events) == 2, "incident_history_mismatch")
    authorization, consumption = events
    auth = authorization.get("authorization", {})
    event_sha = recovery.fingerprint(auth)
    recovered = state["operations"].get(recovery.RECOVERY_CHAT, {})
    permit_sha = chat.get("permit_sha")
    recovered_sha = recovered.get("permit_sha")
    require(isinstance(permit_sha, str) and recovery.SHA.fullmatch(permit_sha)
            and isinstance(recovered_sha, str) and recovery.SHA.fullmatch(recovered_sha)
            and authorization.get("kind") == "authorized" and authorization.get("authorization_sha") == event_sha
            and consumption == dict(kind="consumed", authorization_sha=event_sha,
                                    operation=recovery.RECOVERY_CHAT, permit_sha=recovered_sha)
            and all(auth.get(key) == value for key, value in dict(
                incident=recovery.INCIDENT, original_operation=recovery.ORIGINAL_UPLOAD,
                original_permit_sha=permit_sha, original_head=recovery.ORIGINAL_HEAD,
                original_operations_sha=recovery.fingerprint(rows), classification="C",
                held_micro_usd=recovery.HOLD, upload_attempts=1, page_attempts=65,
                accepted_residual_risk=True, wire_sha256=recovery.Q01_WIRE, manifest_sha256=recovery.MANIFEST,
                recovery_operation=recovery.RECOVERY_CHAT).items())
            and all(isinstance(auth.get(field), str) and pattern.fullmatch(auth[field]) for field, pattern in (
                ("archived_ledger_sha", recovery.SHA), ("account_scope", recovery.SHA), ("head", recovery.HEAD)))
            and auth["head"] != recovery.ORIGINAL_HEAD
            and state["runs"].get(chat["run"]) == permit_sha
            and state["runs"].get(recovered.get("run")) == recovered_sha
            and recovered.get("calibration_scope") == auth["account_scope"]
            and recovered.get("state") == "settled" and recovered.get("kind") == "calibration"
            and recovered.get("campaign") == recovery.CAMPAIGN and recovered.get("profile") == "owner",
            "incident_history_mismatch")
    return auth, dict(original_operation=recovery.ORIGINAL_UPLOAD,
                      original_operations_digest=recovery.fingerprint(rows),
                      original_operation_digest=recovery.fingerprint(failed),
                      recovery_events_digest=recovery.fingerprint(events))


def read_archive_file(path, *, readonly=False):
    stat = path.lstat()
    require(not path.is_symlink() and path.is_file() and stat.st_uid == os.getuid()
            and not stat.st_mode & (0o277 if readonly else 0o077), "incident_archive_mismatch")
    return path.read_bytes()


def confirm_archive(state, archive, campaign_root=None):
    """Compare the shared ledger against the previously sealed incident evidence."""
    auth, _ = original_history(state)
    try:
        raw = read_archive_file(archive / "ledger.json", readonly=True)
        archived = json.loads(raw)
        prior = json.loads(read_archive_file(archive / "go-Q01.json", readonly=True))
        independent = json.loads(read_archive_file(archive.parent / "CAL-INC-01-authorization.json"))
        expect = recovery.authorization_payload(archived, raw, prior, auth["head"], auth["owner"])
        require(independent == expect == auth and recovery.original_rows(archived) == recovery.original_rows(state),
                "incident_archive_mismatch")

        consumed = state["recovery_events"][1]
        recovered = state["operations"][recovery.RECOVERY_CHAT]
        candidates = dict.fromkeys([campaign_root or archive.parent, archive.parent])
        for root in candidates:
            path = root / "go-Q01-recovery.json"
            if not path.is_file():
                continue
            go = json.loads(read_archive_file(path))
            if (recovery.fingerprint(go) == consumed["permit_sha"]
                    and go["recovery_authorization_sha"] == consumed["authorization_sha"]
                    and go["run"] == recovered["run"] and go["kind"] == "controlled_calibration"
                    and go["cal_id"] == "Q01" and go["head"] == auth["head"]
                    and recovery.scope(go, auth["head"]) == auth["account_scope"]):
                break
        else:
            require(False, "incident_archive_mismatch")

        prefix = recovery.RECOVERY_CHAT + "/upload/"
        uploads = {key: row for key, row in state["operations"].items() if key.startswith(prefix)}
        expected_pages = {prefix + key.rsplit("/", 1)[-1]: pages for key, pages in recovery.ORIGINAL_UPLOADS.items()}
        require(set(uploads) == set(expected_pages) and all(
            row["kind"] == "upload" and row["state"] == "settled" and row["run"] == recovered["run"]
            and row["campaign"] == recovery.CAMPAIGN and row["profile"] == "owner"
            and row["pages"] == expected_pages[key] and row["reserve"] == row["cost"] == row["pages"] * PAGE_PRICE
            for key, row in uploads.items()), "incident_archive_mismatch")
        return prior["account"], prior["project"]
    except (OSError, KeyError, ValueError, TypeError):
        require(False, "incident_archive_mismatch")


def canonical_ledger():
    expected = Path.home() / ".local/state/ds-dc02/ledger"
    require(expected.resolve() == Path.home().resolve() / ".local/state/ds-dc02/ledger",
            "ledger_path_invalid")
    return expected


def labels(state):
    return {(row["account"], row["project"]) for row in state["bindings"].values()
            if all(isinstance(row.get(key), str) and LABEL.fullmatch(row[key])
                   for key in ("account", "project"))}


def admit(state):
    require(not state.get("dc04b_events") and RUN not in state["runs"]
            and not any(key.startswith(CHAT) for key in state["operations"]), "dc04b_already_reserved")
    original_history(state)
    active = []
    for key, row in state["operations"].items():
        require(row["state"] in {"reserved", "inflight", "unknown", "settled", "cancelled"},
                "ledger_invalid")
        require(key == recovery.ORIGINAL_UPLOAD or row["state"] not in {"unknown", "inflight", "reserved"},
                "provider_unknown")
        if row["state"] != "cancelled" and row.get("campaign") == recovery.CAMPAIGN:
            require(all(type(n) is int and n >= 0 for n in (row["reserve"], row.get("cost", 0), row.get("pages", 0)))
                    and (row["state"] != "settled" or "cost" in row), "ledger_invalid")
            active.append(row)

    used = dict(budget=sum(map(Ledger.accounted, active)) + OWNER["reserve_disabled"],
                pages=sum(row.get("pages", 0) for row in active),
                chats=sum(row["kind"] in {"normal", "extended", "calibration"} for row in active))
    for kind in ("upload", "status", "delete", "calibration", "normal", "extended"):
        used[kind] = sum(row["kind"] == kind or row.get("slot") == kind for row in active)
    require(all(used[key] + cap <= OWNER[key] for key, cap in LIMITS.items()), "campaign_budget_exhausted")
    return recovery.fingerprint(state)


def make_permit(state, basis, head, principal, now, account_project=None):
    terms(now)
    require(recovery.HEAD.fullmatch(head) and head != BASELINE, "head_mismatch")
    require(recovery.SHA.fullmatch(principal), "account_scope_mismatch")
    require(admit(state) == basis, "ledger_changed")
    auth, incident = original_history(state)
    chat = state["operations"][recovery.ORIGINAL_CHAT]
    matches = []
    candidates = [account_project] if account_project is not None else sorted(labels(state))
    for account, project in candidates:
        scope = dict(account=account, project=project, key_sha256=principal)
        if (recovery.scope(scope, auth["head"]) == auth["account_scope"]
                and recovery.scope(scope, recovery.ORIGINAL_HEAD) == chat["calibration_scope"]):
            matches.append((account, project))
    require(len(matches) == 1, "account_scope_mismatch")
    account, project = matches[0]
    scope = dict(account=account, project=project, key_sha256=principal)
    return dict(incident=incident, approval=OWNER_APPROVAL, ledger_basis=basis, head=head, question=QUESTION_ID,
                wire=WIRE, manifest=MANIFEST, logical_payload=PAYLOAD, registry=REGISTRY,
                request_id=REQUEST_ID, contract_digest=CONTRACT_DIGEST, expires=EXPIRES,
                account=account, project=project, principal=principal, account_scope=recovery.scope(scope, head),
                operations=[4, 80, 1, 0, 0, 0],
                limits=LIMITS.copy())


def issue(state, basis, head, key, now, account_project=None):
    return make_permit(state, basis, head, sha256(key.encode()).hexdigest(), now, account_project)


def validate_reservation(state, permit, run, permit_sha, now, limits, ops, *, public, campaign, recovery_route):
    require(not public and not recovery_route and run == RUN and campaign == recovery.CAMPAIGN
            and limits == LIMITS and ops == operations() and permit_sha == recovery.fingerprint(permit)
            and isinstance(permit.get("head"), str) and isinstance(permit.get("principal"), str),
            "permit_mismatch")
    expected = make_permit(state, permit["ledger_basis"], permit["head"], permit["principal"], now,
                           (permit["account"], permit["project"]))
    require(permit == expected, "permit_mismatch")
    return dict(kind="reserved", permit_sha=permit_sha, permit=permit)


def reserve(ledger, state, permit, now):
    ledger.reserve(state, RUN, recovery.fingerprint(permit), "owner", now, LIMITS, operations(),
                   campaign=recovery.CAMPAIGN, dc04b_permit=permit)
