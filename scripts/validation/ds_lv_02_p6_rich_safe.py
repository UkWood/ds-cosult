#!/usr/bin/env python3
"""DS-LV-02/P6-RICH safe continuation after independent P6-TEXT cleanup acceptance.
Offline --self-test is free. --execute-rich: at most upload+chat+delete+complete
file list (4 HTTP), no retry. Original P6-TEXT code and reports remain immutable.
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
import urllib.parse
import urllib.request
import uuid

ROOT = Path.home() / "ds-consult-validation"
FIXTURE_SHA = "069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286"
QUESTION = ("Из приложенного документа выпиши устройства с ёмкостями и кодами. "
            "Отдельно назови цвета и число геометрических фигур, если они действительно видны. "
            "Если рисунок недоступен, прямо скажи об этом. Ответь кратко на русском.")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def fixture_bytes():
    cmds = [
        "0 0 0 rg",
        "BT /F1 17 Tf 72 730 Td (DS-P6-SYNTHETIC-2026) Tj ET",
        "BT /F1 11 Tf 72 699 Td (SYNTHETIC DEMO - NO PRIVATE INFORMATION) Tj ET",
        "BT /F1 12 Tf 72 660 Td (Device FENIX-17; Capacity 12.4 L; Code TX-731) Tj ET",
        "BT /F1 12 Tf 72 635 Td (Device ORBIT-5; Capacity 6.8 L; Code RB-204) Tj ET",
        "BT /F1 11 Tf 72 596 Td (Graphic: an unlabeled colored shape is below.) Tj ET",
        "1 0 0 rg 72 430 90 90 re f",
        "0 0 1 rg 220 430 90 90 re f",
        "0 0 0 rg BT /F1 10 Tf 72 390 Td (END OF SYNTHETIC FIXTURE) Tj ET",
    ]
    stream = "\n".join(cmds).encode("ascii")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    for idx, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for n in offsets:
        out += f"{n:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Root 1 0 R /Size {len(objs)+1} >>\nstartxref\n{xref}\n%%EOF\n".encode()
    assert hashlib.sha256(out).hexdigest() == FIXTURE_SHA
    return out

def save_fixture():
    path = ROOT / "fixtures" / "ds-lv-02-p6-synthetic.pdf"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = fixture_bytes()
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError("Fixture mismatch, refusing overwrite/upload")
    if not path.exists():
        path.write_bytes(data)
    os.chmod(path, 0o600)
    return path

def multipart(pdf, purpose):
    boundary = "DSLV02P6" + uuid.uuid4().hex
    fields = [
        ("purpose", purpose),
        ("expires_after[anchor]", "created_at"),
        ("expires_after[seconds]", "3600"),
    ]
    body = bytearray()
    for name, value in fields:
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="ds-lv-02-p6-synthetic.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode())
    body.extend(pdf)
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    return bytes(body), "multipart/form-data; boundary=" + boundary

def request_json(method, url, key, payload=None, content_type=None, timeout=60):
    headers = {"Authorization": "Bearer " + key}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            status, data = response.status, response.read(2_000_001)
    except urllib.error.HTTPError as err:
        return {"http_status": err.code, "error_type": "HTTPError"}
    if len(data) > 2_000_000:
        return {"http_status": status, "error_type": "response_too_large"}
    try:
        doc = json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeError):
        return {"http_status": status, "error_type": "invalid_json"}
    return {"http_status": status, "document": doc}

def checked(response, stage):
    if response["http_status"] != 200:
        raise RuntimeError(stage + "_HTTP_" + str(response["http_status"]))
    doc = response.get("document")
    if not isinstance(doc, dict) or doc.get("error"):
        raise RuntimeError(stage + "_ERROR_JSON")
    return doc

def write_private(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(path, 0o600)

def offline_test():
    pdf = fixture_bytes()
    assert len(pdf) == 1031 and pdf.startswith(b"%PDF-1.4")
    assert pdf.count(b"/Type /Page ") == 1
    assert b"FENIX-17" in pdf and b"ORBIT-5" in pdf
    assert b"1 0 0 rg" in pdf and b"0 0 1 rg" in pdf
    payload, header = multipart(pdf, "text_recognition")
    assert payload.find(b'name="purpose"') < payload.find(b'name="file"')
    assert b'name="expires_after[seconds]"\r\n\r\n3600' in payload
    assert "boundary=" in header
    assert checked({"http_status":200,"document":{"id":"file-api-test"}}, "UPLOAD")["id"] == "file-api-test"
    try:
        checked({"http_status":200,"document":{"error":{"code":"synthetic"}}}, "UPLOAD")
    except RuntimeError:
        pass
    else:
        raise AssertionError("top-level error inside HTTP 200 must fail")
    save_fixture()
    prior = {"test_id":"DS-LV-02-P6-TEXT","delete_http_status":200,
             "deletion_acknowledged":True,"verify_get_http_status":400,
             "deletion_verified_absent":False,"file_id_sha256":"a"*64,
             "expires_at_reported":1794951296}
    diagnostic = {"test_id":"DS-LV-02-P6-TEXT-LIST-CHECK",
                  "http_requests_attempted":1,
                  "observed_target_file_id_sha256":"a"*64,
                  "list_http_status":200,"target_file_listed":False,
                  "list_has_more":False,"records_returned":0,
                  "absence_gate":"PASS_TARGET_NOT_IN_EXHAUSTIVE_LIST",
                  "timestamp_utc":"2026-11-17T20:52:28+00:00"}
    assert valid_previous_cleanup(prior, diagnostic)
    assert not valid_previous_cleanup(prior, {**diagnostic,"list_has_more":True})
    assert not valid_previous_cleanup(prior, {**diagnostic,"observed_target_file_id_sha256":"b"*64})
    assert not valid_previous_cleanup(prior, {**diagnostic,"timestamp_utc":"2026-11-17T22:00:00+00:00"})
    assert complete_file_list_absence({"object":"list","data":[],"has_more":False},"target") == (True,0,False)
    assert complete_file_list_absence({"object":"list","data":[{"id":"target"}],"has_more":False},"target") == (False,1,False)
    assert complete_file_list_absence({"object":"list","data":[],"has_more":True},"target") == (False,0,True)
    assert complete_file_list_absence({"object":"list","data":["invalid"],"has_more":False},"target") == (False,1,False)
    print("DS-LV-02 P6 RICH SAFE OFFLINE SELF-TEST: PASS")
    print("FIXTURE SHA256:", FIXTURE_SHA)
    print("NETWORK REQUESTS: 0 | API COST: $0")


def valid_previous_cleanup(prior, diagnostic):
    """Read-only gate over original P6-TEXT and the separate full list check."""
    if not (isinstance(prior, dict) and isinstance(diagnostic, dict)):
        return False
    if prior.get("test_id") != "DS-LV-02-P6-TEXT":
        return False
    if prior.get("deletion_acknowledged") is not True or prior.get("delete_http_status") != 200:
        return False
    if prior.get("verify_get_http_status") != 400 or prior.get("deletion_verified_absent") is not False:
        return False
    if diagnostic.get("test_id") != "DS-LV-02-P6-TEXT-LIST-CHECK":
        return False
    fid_hash = prior.get("file_id_sha256")
    if not isinstance(fid_hash, str) or len(fid_hash) != 64 or diagnostic.get("observed_target_file_id_sha256") != fid_hash:
        return False
    if not (diagnostic.get("list_http_status") == 200
            and diagnostic.get("http_requests_attempted") == 1
            and diagnostic.get("records_returned") == 0
            and diagnostic.get("target_file_listed") is False
            and diagnostic.get("list_has_more") is False
            and diagnostic.get("absence_gate") == "PASS_TARGET_NOT_IN_EXHAUSTIVE_LIST"):
        return False
    expiry = prior.get("expires_at_reported")
    ts = diagnostic.get("timestamp_utc")
    if not isinstance(expiry, int) or not isinstance(ts, str):
        return False
    try:
        observed = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return observed.tzinfo is not None and observed.timestamp() < expiry
    except ValueError:
        return False


def complete_file_list_absence(listing, file_id):
    """Return (absence, size, paginated): unknown/malformed list is never PASS."""
    if not isinstance(listing, dict) or listing.get("object") != "list":
        return False, None, None
    files, more = listing.get("data"), listing.get("has_more")
    if not isinstance(files, list) or not isinstance(more, bool):
        return False, None, None
    if not all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in files):
        return False, len(files), more
    if more:
        return False, len(files), more
    return not any(x["id"] == file_id for x in files), len(files), False

def execute(variant):
    os.umask(0o077)
    folder = ROOT / "logs"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = folder / ("ds-lv-02-p6-" + variant + "-attempted.marker")
    report = folder / ("ds-lv-02-p6-" + variant + "-redacted.json")
    journal = folder / ("ds-lv-02-p6-" + variant + "-private-id.json")
    if any(x.exists() for x in (marker, report, journal)):
        raise SystemExit("STOP: P6 " + variant + " already attempted. NO RETRY.")
    if variant != "rich":
        raise SystemExit("STOP: only P6-RICH may execute in this corrected script.")
    previous = folder / "ds-lv-02-p6-text-redacted.json"
    diagnostic = folder / "ds-lv-02-p6-text-list-diagnostic-redacted.json"
    if not previous.is_file() or not diagnostic.is_file():
        raise SystemExit("STOP: first P6-TEXT evidence and independent list diagnostic are both required.")
    previous_status = json.loads(previous.read_text(encoding="utf-8"))
    diagnostic_status = json.loads(diagnostic.read_text(encoding="utf-8"))
    if not valid_previous_cleanup(previous_status, diagnostic_status):
        raise SystemExit("STOP: P6-TEXT cleanup not independently accepted before file expiry.")
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    fixture = save_fixture()
    if hashlib.sha256(fixture.read_bytes()).hexdigest() != FIXTURE_SHA:
        raise SystemExit("STOP: fixture SHA mismatch")
    if input("Owner P6-P9 general GO documented. Enter P6-APPROVED: ") != "P6-APPROVED":
        raise SystemExit("STOP: local confirmation declined.")
    key = getpass.getpass("DeepSeek API key (hidden, WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: empty key; no network requests.")
    fd = os.open(str(marker), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("P6 " + variant + " reserved: do not retry.\n")
    purpose = "text_recognition" if variant == "text" else "rich_layout_recognition"
    result = {
        "test_id":"DS-LV-02-P6-" + variant.upper(),
        "purpose":purpose, "fixture_sha256":FIXTURE_SHA,
        "fixture_bytes":len(fixture.read_bytes()),
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "max_http_requests":4, "http_requests_attempted":0,
        "upload_http_status":None, "chat_http_status":None,
        "delete_http_status":None, "verify_get_http_status":None,
        "deletion_acknowledged":False, "deletion_verified_absent":False,
        "file_id_sha256":None,
        "expires_after_seconds_requested":3600, "expires_at_reported":None,
        "chat_model_observed":None, "finish_reason":None,
        "answer_preview":None, "usage":{},
        "estimated_peak_cost_usd":None, "actual_billing_usd":None,
        "status":"ERROR", "error_type":None,
    }
    file_id = None
    started = time.monotonic()
    try:
        data, content_type = multipart(fixture.read_bytes(), purpose)
        result["http_requests_attempted"] += 1
        response = request_json("POST", "https://api.deepseek.com/files",
                                key, data, content_type, timeout=260)
        result["upload_http_status"] = response["http_status"]
        uploaded = checked(response, "UPLOAD")
        file_id = uploaded.get("id")
        if not isinstance(file_id, str) or not file_id.startswith("file-api-") or uploaded.get("purpose") != purpose:
            raise RuntimeError("UPLOAD_UNEXPECTED_FILE_OBJECT")
        write_private(journal, {"file_id":file_id,"purpose":purpose,"fixture_sha256":FIXTURE_SHA})
        result["file_id_sha256"] = hashlib.sha256(file_id.encode("utf-8")).hexdigest()
        result["expires_at_reported"] = uploaded.get("expires_at") if isinstance(uploaded.get("expires_at"), int) else None
        if result["expires_at_reported"] is None:
            raise RuntimeError("UPLOAD_EXPIRY_NOT_ACKNOWLEDGED")
        body = {
            "model":"deepseek-flash", "thinking":{"type":"disabled"},
            "messages":[{"role":"user","content":[
                {"type":"file","file_id":file_id},
                {"type":"text","text":QUESTION}]}],
            "max_tokens":300,"stream":False
        }
        result["http_requests_attempted"] += 1
        response = request_json("POST", "https://api.deepseek.com/chat/completions",
                                key, json.dumps(body, ensure_ascii=False).encode("utf-8"),
                                "application/json", timeout=90)
        result["chat_http_status"] = response["http_status"]
        chat = checked(response, "CHAT")
        result["chat_model_observed"] = chat.get("model")
        choices = chat.get("choices") or []
        choice = choices[0] if isinstance(choices, list) and choices else {}
        result["finish_reason"] = choice.get("finish_reason")
        answer = (choice.get("message") or {}).get("content") or ""
        result["answer_preview"] = answer[:650] if isinstance(answer, str) else None
        usage = chat.get("usage") or {}
        result["usage"] = {k:usage[k] for k in ("prompt_tokens","completion_tokens","total_tokens") if isinstance(usage.get(k),int)}
        if all(k in result["usage"] for k in ("prompt_tokens","completion_tokens")):
            result["estimated_peak_cost_usd"] = round(0.000225 +
                result["usage"]["prompt_tokens"] * 0.30 / 1_000_000 +
                result["usage"]["completion_tokens"] * 1.20 / 1_000_000,8)
        result["status"] = ("FILE_AND_CHAT_RETURNED_REVIEW_NEEDED"
                            if result["finish_reason"] == "stop" and isinstance(answer, str) and answer.strip()
                            else "PARTIAL_CHAT_OR_OUTPUT")
    except Exception as error:
        result["error_type"] = type(error).__name__
        result["status"] = "BLOCKED"
    finally:
        if file_id:
            url = "https://api.deepseek.com/files/" + urllib.parse.quote(file_id, safe="")
            try:
                result["http_requests_attempted"] += 1
                response = request_json("DELETE", url, key, timeout=45)
                result["delete_http_status"] = response["http_status"]
                deleted = checked(response, "DELETE")
                result["deletion_acknowledged"] = deleted.get("deleted") is True and deleted.get("id") == file_id
            except Exception:
                result["deletion_acknowledged"] = False
            if result["deletion_acknowledged"]:
                try:
                    result["http_requests_attempted"] += 1
                    response = request_json(
                        "GET",
                        "https://api.deepseek.com/files?limit=1000&order=desc&purpose=rich_layout_recognition",
                        key, timeout=45)
                    result["verify_get_http_status"] = response["http_status"]
                    if response["http_status"] == 200:
                        listing = checked(response, "FILE_LIST")
                        absence, count, paginated = complete_file_list_absence(listing, file_id)
                        result["deletion_verified_absent"] = absence
                        result["verify_list_records_count"] = count
                        result["verify_list_has_more"] = paginated
                except Exception:
                    pass
            if not result["deletion_acknowledged"]:
                result["status"] = "STOP_FILE_DELETE_UNCONFIRMED"
            elif not result["deletion_verified_absent"]:
                result["status"] = "STOP_DELETION_VERIFICATION_UNCONFIRMED"
        else:
            result["unknown_file_id_possible_after_timeout"] = True
        result["latency_ms"] = int((time.monotonic()-started)*1000)
        write_private(report, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        offline_test()
    elif sys.argv[1:] == ["--execute-rich"]:
        execute("rich")
    else:
        raise SystemExit("Usage: script.py --self-test OR --execute-rich (only after accepted offline preflight)")
