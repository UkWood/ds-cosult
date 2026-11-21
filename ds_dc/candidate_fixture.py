"""Private, offline Q01 CandidateAnswer export and pinned import."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from .corpus import encoded
from .recovery import Q01_WIRE, RECOVERY_CHAT
from .runtime import CandidateAnswer, Claim, Locator

LIMIT = 100_000
SENSITIVE = re.compile(
    r"file-api-|\[redacted |authorization\s*[:=]|bearer\s+|api[_ -]?key\s*[:=]|"
    r"\b(?:sk-|ghp_|github_pat_)[\w-]{12,}|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|"
    r"https?://|[\x00-\x08\x0b-\x1f\x7f]", re.I)


def decode(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    return json.loads(data, object_pairs_hook=unique)


def read_candidate(path, limit=LIMIT):
    with path.open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise ValueError("fixture_too_large")
    return data


def validate_export(candidate):
    def check_fields(obj, fields, lists=()):
        if not isinstance(obj, dict) or not set(obj) <= fields:
            raise ValueError("unexpected_candidate_fields")
        for key, value in obj.items():
            if key in lists and isinstance(value, list) and len(value) <= 32:
                continue
            if not (isinstance(value, str) or key == "revision" and value is None
                    or key == "page" and type(value) is int):
                raise ValueError("unexpected_candidate_type")
            if isinstance(value, str) and (SENSITIVE.search(value) or len(value) > 9_000):
                raise ValueError("potential_private_content")

    check_fields(candidate, CandidateAnswer.__required_keys__, ("claims", "unresolved"))
    if any(key in candidate and not isinstance(candidate[key], list) for key in ("claims", "unresolved")):
        raise ValueError("unexpected_candidate_type")
    for part in candidate.get("unresolved", []):
        if not isinstance(part, str) or len(part) > 1_200 or SENSITIVE.search(part):
            raise ValueError("potential_private_content")
    for claim in candidate.get("claims", []):
        check_fields(claim, Claim.__required_keys__, ("locators",))
        if not isinstance(claim.get("locators", []), list):
            raise ValueError("unexpected_candidate_type")
        for loc in claim.get("locators", []):
            check_fields(loc, Locator.__required_keys__ | {"field_path"})


def export_receipt(receipt, path):
    if receipt.get("wire_sha256") != Q01_WIRE or receipt.get("finish_reason") != "stop":
        raise ValueError("not_q01_recovery_receipt")
    candidate = receipt.get("candidate")
    validate_export(candidate)
    raw = receipt.get("raw_draft")
    if raw is not None and (not isinstance(raw, str) or encoded(decode(raw)) != encoded(candidate)):
        raise ValueError("raw_candidate_mismatch")
    data = (raw if raw is not None else encoded(candidate)).encode("utf-8")
    if len(data) > LIMIT:
        raise ValueError("fixture_too_large")
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as file:
        file.write(data)
    return hashlib.sha256(data).hexdigest()


def load_candidate(path, sha256):
    data = read_candidate(path)
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("fixture_sha_mismatch")
    candidate = decode(data.decode("utf-8"))
    validate_export(candidate)
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--ledger", type=Path, help="Existing private ledger.json, read only.")
    source.add_argument("--receipt", type=Path, help="Private calibration_result object.")
    parser.add_argument("--output", type=Path, required=True, help="New file, reviewed locally before sharing.")
    args = parser.parse_args()
    try:
        path = args.ledger or args.receipt
        if path.is_symlink() or path.stat().st_mode & 0o077:
            raise ValueError("private_source_required")
        source = decode(read_candidate(path, 16_000_000))
        if args.ledger:
            row = source["operations"][RECOVERY_CHAT]
            if row["state"] != "settled":
                raise ValueError("not_settled")
            source = row["calibration_result"]
        print(export_receipt(source, args.output))
    except (OSError, KeyError, TypeError, ValueError, RecursionError):
        parser.exit(1, "Export refused. Review the private source locally.\n")


if __name__ == "__main__":
    main()
