#!/usr/bin/env python3
"""DS-LV-02/P6-TEXT read-only 1-call file-list diagnostic.
--self-test: ZERO NETWORK. --check-target: exactly ONE GET /files.
No upload, model call, delete, retries, or raw file IDs in stdout.
"""
import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT = Path.home() / "ds-consult-validation"
LOG = ROOT / "logs"
PREV = LOG / "ds-lv-02-p6-text-redacted.json"
JOURNAL = LOG / "ds-lv-02-p6-text-private-id.json"
MARKER = LOG / "ds-lv-02-p6-text-list-diagnostic-attempted.marker"
REPORT = LOG / "ds-lv-02-p6-text-list-diagnostic-redacted.json"
URL = "https://api.deepseek.com/files?limit=1000&order=desc&purpose=text_recognition"
MAX_BYTES = 2000000

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def inspect_list(http_status, obj, target):
    result = {"list_http_status": http_status, "target_file_listed": None,
              "list_has_more": None, "records_returned": None,
              "absence_gate": "INCONCLUSIVE"}
    if http_status != 200 or not isinstance(obj, dict) or obj.get("error") or obj.get("object") != "list":
        return result
    records = obj.get("data")
    has_more = obj.get("has_more")
    if not isinstance(records, list) or not isinstance(has_more, bool):
        return result
    result["records_returned"] = len(records)
    result["list_has_more"] = has_more
    target_present = any(isinstance(f, dict) and f.get("id") == target for f in records)
    result["target_file_listed"] = target_present
    if target_present:
        result["absence_gate"] = "FAIL_TARGET_STILL_LISTED"
    elif has_more:
        result["absence_gate"] = "INCONCLUSIVE_PAGINATED_LIST"
    else:
        result["absence_gate"] = "PASS_TARGET_NOT_IN_EXHAUSTIVE_LIST"
    return result

def local_state():
    if not PREV.is_file() or not JOURNAL.is_file():
        raise ValueError("MISSING_P6_TEXT_LOCAL_EVIDENCE")
    prior = json.loads(PREV.read_text(encoding="utf-8"))
    priv = json.loads(JOURNAL.read_text(encoding="utf-8"))
    fid = priv.get("file_id")
    if not isinstance(fid, str) or not fid.startswith("file-api-"):
        raise ValueError("INVALID_PRIVATE_FILE_ID")
    if priv.get("purpose") != "text_recognition":
        raise ValueError("UNEXPECTED_PURPOSE")
    if hashlib.sha256(fid.encode("utf-8")).hexdigest() != prior.get("file_id_sha256"):
        raise ValueError("FILE_ID_MISMATCH")
    if not (prior.get("deletion_acknowledged") is True
            and prior.get("deletion_verified_absent") is False
            and prior.get("delete_http_status") == 200
            and prior.get("verify_get_http_status") == 400):
        raise ValueError("UNEXPECTED_PRIOR_FILE_STATE")
    return fid

def selftest():
    target = "file-api-local-test"
    base = {"object":"list", "has_more":False,
            "data":[{"id":"file-api-other","purpose":"text_recognition"}]}
    assert inspect_list(200, base, target)["absence_gate"] == "PASS_TARGET_NOT_IN_EXHAUSTIVE_LIST"
    assert inspect_list(200, {**base,"data":[{"id":target}]}, target)["absence_gate"] == "FAIL_TARGET_STILL_LISTED"
    assert inspect_list(200, {**base,"has_more":True}, target)["absence_gate"] == "INCONCLUSIVE_PAGINATED_LIST"
    assert inspect_list(400, None, target)["absence_gate"] == "INCONCLUSIVE"
    assert inspect_list(200, {"error":{"code":"test"}}, target)["absence_gate"] == "INCONCLUSIVE"
    assert inspect_list(200, {"object":"list","data":[]}, target)["absence_gate"] == "INCONCLUSIVE"
    print("DS-LV-02 P6 FILE-LIST DIAGNOSTIC SELF-TEST: PASS")
    print("NETWORK REQUESTS: 0 | API COST: $0")

def paid_metadata_read():
    os.umask(0o077)
    if MARKER.exists() or REPORT.exists():
        raise SystemExit("STOP: file-list diagnostic already attempted. NO RETRY.")
    try:
        file_id = local_state()
    except Exception as error:
        raise SystemExit("STOP: local precondition " + type(error).__name__)
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    if input("One extra read-only GET under approved P6 budget. Type P6-LIST-APPROVED: ") != "P6-LIST-APPROVED":
        raise SystemExit("STOP: approval not entered.")
    key = getpass.getpass("DeepSeek API key (hidden, WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: empty key.")
    fd = os.open(str(MARKER), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("P6-TEXT one list GET reserved. No retries.\n")
    result = {
        "test_id":"DS-LV-02-P6-TEXT-LIST-CHECK",
        "purpose":"text_recognition",
        "observed_target_file_id_sha256":hashlib.sha256(file_id.encode("utf-8")).hexdigest(),
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "http_requests_attempted":0,
        "list_http_status":None, "target_file_listed":None,
        "list_has_more":None,"records_returned":None,
        "absence_gate":"INCONCLUSIVE", "actual_billing_usd":None,
        "raw_file_ids_logged":False, "error_type":None
    }
    started=time.monotonic()
    try:
        request = urllib.request.Request(URL, method="GET",
            headers={"Authorization":"Bearer "+key})
        result["http_requests_attempted"]=1
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=45) as response:
            status=response.status
            payload=response.read(MAX_BYTES+1)
        if len(payload)>MAX_BYTES:
            raise ValueError("RESPONSE_TOO_LARGE")
        obj=json.loads(payload.decode("utf-8"))
        result.update(inspect_list(status, obj, file_id))
    except urllib.error.HTTPError as e:
        result["list_http_status"]=e.code
        result["error_type"]="HTTPError"
    except Exception as e:
        result["error_type"]=type(e).__name__
    finally:
        key=None
        request=None
        file_id=None
        result["latency_ms"]=int((time.monotonic()-started)*1000)
        REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(REPORT, 0o600)
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:
        selftest()
    elif sys.argv[1:]==["--check-target"]:
        paid_metadata_read()
    else:
        raise SystemExit("Usage: script.py --self-test | --check-target. Only run check after accepted offline preflight.")
