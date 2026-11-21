"""Offline authorization for CAL-INC-01. This entry point has no provider transport."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess

from .corpus import encoded

INCIDENT = "CAL-INC-01"
ORIGINAL_HEAD = "a5f3012e1fb9798848914a0f00908524981475c4"
Q01_WIRE = "7498d9920faf9cf25dfbf461c0bc64a75701089423a1c142c1b45cb85e9b9afd"
MANIFEST = "13fd98159f05809c019dd11a522b1c87fff3faebc505621bde7318880e3051f9"
CAMPAIGN = "dc02-live"
ORIGINAL_CHAT = CAMPAIGN + "/calibration/" + Q01_WIRE
ORIGINAL_UPLOADS = {
    ORIGINAL_CHAT + "/upload/030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a": 65,
    ORIGINAL_CHAT + "/upload/496ddc2786b8fb2cdfd8970947fadde6b7a045e7d86e20737f2ef694425d5890": 8,
    ORIGINAL_CHAT + "/upload/959f515c588ea8758cae0ccfdd17efaf396b31c84c4315e1b195c745d59db5db": 5,
    ORIGINAL_CHAT + "/upload/bf07da30d1221f61a3ecdde5b40f542b90ca2a646c5dc6019997326a2c570148": 2,
}
ORIGINAL_UPLOAD = next(iter(ORIGINAL_UPLOADS))
RECOVERY_CHAT = ORIGINAL_CHAT + "/recovery/" + INCIDENT
HOLD = 14625
SHA = re.compile(r"[0-9a-f]{64}")
HEAD = re.compile(r"[0-9a-f]{40}")


def fingerprint(value):
    return sha256(encoded(value).encode()).hexdigest()


def scope(permit, head):
    return fingerprint([permit["account"], permit["project"], permit["key_sha256"], MANIFEST, head])


def original_rows(state):
    return {key: row for key, row in state["operations"].items()
            if key == ORIGINAL_CHAT or key.startswith(ORIGINAL_CHAT + "/upload/")}


def validate_original(state, permit):
    rows = original_rows(state)
    prior = rows[ORIGINAL_CHAT]
    failed = rows[ORIGINAL_UPLOAD]
    uploads = {key: row for key, row in rows.items() if key != ORIGINAL_CHAT}
    permit_sha = fingerprint(permit)
    if (set(state["operations"]) != set(rows) or set(state["runs"]) != {permit["run"]}
            or state["bindings"]
            or permit["kind"] != "controlled_calibration" or permit["cal_id"] != "Q01"
            or permit["head"] != ORIGINAL_HEAD or permit["manifest_sha"] != MANIFEST
            or permit["wire_sha256"] != Q01_WIRE or permit["accepted_residual_risk"] is not True
            or state["runs"].get(permit["run"]) != permit_sha or prior.get("permit_sha") != permit_sha
            or prior.get("calibration_scope") != scope(permit, ORIGINAL_HEAD)
            or prior.get("kind") != "calibration" or prior["state"] != "cancelled"
            or prior.get("slot") != "extended" or prior.get("reserve") != 330_000
            or {key: row["pages"] for key, row in uploads.items()} != ORIGINAL_UPLOADS
            or any(row["kind"] != "upload" or row["reserve"] != row["pages"] * 225
                   for row in uploads.values())
            or sum(row["state"] == "cancelled" for row in uploads.values()) != 3
            or any(row["run"] != permit["run"] or row["campaign"] != CAMPAIGN or row["profile"] != "owner"
                   for row in rows.values())
            or failed["state"] != "unknown" or failed["pages"] != 65
            or failed["reserve"] != HOLD or "cost" in failed):
        raise ValueError("recovery_original_mismatch")
    return rows


def authorization_payload(state, archived_ledger, original_permit, head, owner):
    rows = validate_original(state, original_permit)
    if (not isinstance(owner, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", owner)
            or not HEAD.fullmatch(head) or head == ORIGINAL_HEAD):
        raise ValueError("invalid_recovery_authorization")
    return dict(incident=INCIDENT, original_operation=ORIGINAL_UPLOAD,
                original_permit_sha=fingerprint(original_permit), original_head=ORIGINAL_HEAD,
                archived_ledger_sha=sha256(archived_ledger).hexdigest(),
                original_operations_sha=fingerprint(rows), classification="C",
                held_micro_usd=HOLD, upload_attempts=1, page_attempts=65,
                account_scope=scope(original_permit, head), owner=owner,
                accepted_residual_risk=True, head=head, wire_sha256=Q01_WIRE,
                manifest_sha256=MANIFEST, recovery_operation=RECOVERY_CHAT)


def authorize(ledger, authorization, original_permit, archived_ledger, head):
    from .finance import Stopped

    with ledger.transaction(maintain=False) as state:
        if state.get("recovery_events"):
            raise Stopped("recovery_already_authorized")
        expected = authorization_payload(state, archived_ledger, original_permit, head,
                                         authorization.get("owner"))
        if (encoded(authorization) != encoded(expected) or json.loads(archived_ledger) != state
                or ledger.file.read_bytes() != archived_ledger
                or Path(original_permit["ledger_path"]) != ledger.path.resolve()):
            raise ValueError("invalid_recovery_authorization")
        auth_sha = fingerprint(expected)
        state["recovery_events"] = [dict(kind="authorized", authorization_sha=auth_sha, authorization=expected)]
        ledger.save(state)
        return auth_sha


def matching_event(state, authorization_sha, permit, head):
    from .finance import Stopped

    events = state.get("recovery_events", [])
    if not events or events[0]["authorization_sha"] != authorization_sha:
        raise Stopped("recovery_not_authorized")
    event = events[0]
    auth = event["authorization"]
    if (fingerprint(auth) != authorization_sha or auth["head"] != head
            or auth["account_scope"] != scope(permit, head)
            or auth["original_operations_sha"] != fingerprint(original_rows(state))):
        raise Stopped("recovery_authorization_mismatch")
    return events


def main():
    from .finance import Ledger

    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("ledger", "authorization", "archived-ledger", "archived-go"):
        parser.add_argument("--" + flag, required=True, type=Path)
    args = parser.parse_args()
    try:
        for path in (args.archived_ledger, args.archived_go, args.authorization):
            if (path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077):
                raise ValueError("recovery_inputs_must_be_private")
        for path in (args.archived_ledger, args.archived_go):
            if path.stat().st_mode & 0o200:
                raise ValueError("recovery_archive_must_be_read_only")
        ledger = Ledger(args.ledger)
        if not ledger.file.is_file() or ledger.file.is_symlink() or args.archived_ledger.samefile(ledger.file):
            raise ValueError("recovery_requires_existing_ledger_and_separate_archive")
        repo = Path(__file__).resolve().parents[1]
        if subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"]):
            raise ValueError("recovery_requires_clean_head")
        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        print(authorize(ledger, json.loads(args.authorization.read_text()),
                        json.loads(args.archived_go.read_text()), args.archived_ledger.read_bytes(), head))
    except (OSError, KeyError, TypeError, ValueError, subprocess.CalledProcessError):
        parser.exit(1, "Recovery authorization rejected. Preserve original evidence.\n")


if __name__ == "__main__":
    main()
