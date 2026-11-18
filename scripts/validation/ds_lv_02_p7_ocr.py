#!/usr/bin/env python3
"""DS-LV-02/P7: single synthetic page, direct OCR API, no Files storage.
--self-test: offline ONLY, $0. --execute-once: exactly ONE provider POST.
Uses P6-pinned local synthetic PDF, strict id/hash, exclusive attempted marker.
No retries, no redirects, no production/private Saturn documents.
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
import uuid

ROOT=Path.home() / "ds-consult-validation"
FIXTURE=ROOT / "fixtures" / "ds-lv-02-p6-synthetic.pdf"
FIXTURE_SHA="069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286"
LOG=ROOT / "logs"
MARKER=LOG / "ds-lv-02-p7-ocr-attempted.marker"
REPORT=LOG / "ds-lv-02-p7-ocr-redacted.json"
OCR_URL="https://api.deepseek.com/v1/tools/ocr"
OCR_PURPOSE="text_recognition"
MAX_BYTES=2_000_000
EXPECTED=("FENIX-17","12.4","TX-731","ORBIT-5","6.8","RB-204")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def pinned_pdf():
    data=FIXTURE.read_bytes()
    if hashlib.sha256(data).hexdigest()!=FIXTURE_SHA:
        raise ValueError("SYNTHETIC_FIXTURE_SHA256_MISMATCH")
    if not data.startswith(b"%PDF-1.") or data.count(b"/Type /Page ")!=1:
        raise ValueError("SYNTHETIC_FIXTURE_NOT_SINGLE_PAGE")
    if not (b"FENIX-17" in data and b"ORBIT-5" in data):
        raise ValueError("FIXTURE_SENTINELS_MISSING")
    return data

def multipart(pdf):
    boundary="DSLV02P7"+uuid.uuid4().hex
    parts=bytearray()
    parts.extend((f'--{boundary}\r\n'
                  'Content-Disposition: form-data; name="purpose"\r\n\r\n'
                  f'{OCR_PURPOSE}\r\n').encode())
    parts.extend((f'--{boundary}\r\n'
                  'Content-Disposition: form-data; name="file"; filename="ds-lv-02-p7-synthetic.pdf"\r\n'
                  'Content-Type: application/pdf\r\n\r\n').encode())
    parts.extend(pdf)
    parts.extend(f'\r\n--{boundary}--\r\n'.encode())
    return bytes(parts),"multipart/form-data; boundary="+boundary

def evaluate(status,doc):
    result={
        "http_status":status,"api_error_present":None,
        "ocr_object":None,"purpose_observed":None,
        "page_count":None,"pages_count":None,
        "page_indices":[],"page_finish_reasons":[],
        "ocr_chars":0,"ocr_sha256":None,
        "ocr_preview":"","contains_layout_tokens":False,
        "expected_terms_found":{},"all_expected_terms_found":False,
        "usage":{},"provider_invoice_usd":None,
        "estimated_success_page_cost_usd":None,
        "status":"INCONCLUSIVE"
    }
    if not isinstance(doc,dict):
        result["api_error_present"]=True
        result["status"]="FAIL_NONOBJECT_JSON"
        return result
    result["api_error_present"]=bool(doc.get("error"))
    if status!=200 or result["api_error_present"]:
        result["status"]="FAIL_HTTP_OR_ERROR_JSON"
        return result
    result["ocr_object"]=doc.get("object")
    result["purpose_observed"]=doc.get("purpose")
    result["page_count"]=doc.get("page_count")
    pages=doc.get("pages")
    if not isinstance(pages,list):
        result["status"]="INCONCLUSIVE_PAGES_MISSING"
        return result
    result["pages_count"]=len(pages)
    if len(pages)!=1 or doc.get("page_count")!=1 or doc.get("object")!="ocr.result" or doc.get("purpose")!=OCR_PURPOSE:
        result["status"]="INCONCLUSIVE_UNEXPECTED_RESPONSE_CONTRACT"
        return result
    pg=pages[0]
    if not isinstance(pg,dict) or pg.get("index")!=0 or not isinstance(pg.get("text"),str):
        result["status"]="INCONCLUSIVE_PAGE_CONTENT"
        return result
    result["page_indices"]=[pg["index"]]
    result["page_finish_reasons"]=[pg.get("finish_reason")]
    extracted=pg["text"]
    result["ocr_chars"]=len(extracted)
    result["ocr_sha256"]=hashlib.sha256(extracted.encode("utf-8")).hexdigest()
    result["ocr_preview"]=extracted[:520]
    result["contains_layout_tokens"]=("<｜ref｜>" in extracted or "<｜box｜>" in extracted)
    result["expected_terms_found"]={term:(term in extracted) for term in EXPECTED}
    result["all_expected_terms_found"]=all(result["expected_terms_found"].values())
    usage=doc.get("usage") or {}
    if isinstance(usage,dict):
        result["usage"]={k:v for k,v in usage.items()
                          if k in ("input_tokens","output_tokens","total_tokens") and isinstance(v,int)}
    if pg.get("finish_reason")!="stop":
        result["status"]="PARTIAL_OCR_TRUNCATED_OR_UNFINISHED"
    elif not extracted.strip():
        result["status"]="INCONCLUSIVE_EMPTY_OCR"
    else:
        result["status"]="OCR_PAGE_RETURNED_REVIEW_NEEDED"
        result["estimated_success_page_cost_usd"]=0.000225
    return result

def self_test():
    pdf=pinned_pdf()
    body,header=multipart(pdf)
    assert body.count(b'name="purpose"')==1
    assert body.count(b'name="file"')==1
    assert b'name="purpose"\r\n\r\ntext_recognition' in body
    assert b"FENIX-17" in body and b"ORBIT-5" in body
    assert header.startswith("multipart/form-data; boundary=")
    good={
        "id":"ocr-synthetic","object":"ocr.result","purpose":"text_recognition",
        "page_count":1,"pages":[{"index":0,"text":"Device FENIX-17; Capacity 12.4 L; Code TX-731. Device ORBIT-5; Capacity 6.8 L; Code RB-204.",
                                 "finish_reason":"stop"}],
        "usage":{"input_tokens":300,"output_tokens":70,"total_tokens":370}
    }
    one=evaluate(200,good)
    assert one["status"]=="OCR_PAGE_RETURNED_REVIEW_NEEDED" and one["all_expected_terms_found"]
    assert one["estimated_success_page_cost_usd"]==0.000225
    assert evaluate(200,{"error":{"code":"synthetic"}})["status"]=="FAIL_HTTP_OR_ERROR_JSON"
    assert evaluate(200,{**good,"page_count":2})["status"]=="INCONCLUSIVE_UNEXPECTED_RESPONSE_CONTRACT"
    truncated=evaluate(200,{**good,"pages":[{**good["pages"][0],"finish_reason":"length"}]})
    assert truncated["status"]=="PARTIAL_OCR_TRUNCATED_OR_UNFINISHED"
    missing=evaluate(200,{**good,"pages":[{**good["pages"][0],"text":"FENIX-17","finish_reason":"stop"}]})
    assert not missing["all_expected_terms_found"]
    print("DS-LV-02 P7 OCR OFFLINE SELF-TEST: PASS")
    print("FIXTURE SHA256:",FIXTURE_SHA)
    print("NETWORK REQUESTS: 0 | API COST: $0")

def execute():
    os.umask(0o077)
    LOG.mkdir(parents=True, exist_ok=True, mode=0o700)
    if MARKER.exists() or REPORT.exists():
        raise SystemExit("STOP: P7 OCR already attempted; no re-runs.")
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    try:
        pdf=pinned_pdf()
    except Exception as err:
        raise SystemExit("STOP: invalid pinned local synthetic PDF: "+type(err).__name__)
    key=getpass.getpass("DeepSeek API key (hidden, WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: empty API key.")
    fd=os.open(str(MARKER),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        f.write("P7 single OCR POST attempt reserved; do not retry.\n")
    report={
        "test_id":"DS-LV-02-P7-OCR",
        "purpose_requested":OCR_PURPOSE,
        "fixture_sha256":FIXTURE_SHA,
        "fixture_size_bytes":len(pdf),
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "http_requests_attempted":0,
        "max_http_requests":1,
        "file_uploaded_to_Files_API":False,
        "external_url":OCR_URL,
        "actual_billing_usd":None,
        "status":"INCONCLUSIVE",
        "error_type":None
    }
    started=time.monotonic()
    try:
        body,typ=multipart(pdf)
        request=urllib.request.Request(OCR_URL,data=body,method="POST",
                                       headers={"Authorization":"Bearer "+key,"Content-Type":typ})
        report["http_requests_attempted"]=1
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=185) as res:
                http_status=res.status
                raw=res.read(MAX_BYTES+1)
        except urllib.error.HTTPError as error:
            report["http_status"]=error.code
            report["status"]="FAIL_HTTP"
        else:
            if len(raw)>MAX_BYTES:
                raise ValueError("RESPONSE_TOO_LARGE")
            doc=json.loads(raw.decode("utf-8"))
            report.update(evaluate(http_status,doc))
    except Exception as err:
        report["error_type"]=type(err).__name__
        report["status"]="BLOCKED_TRANSPORT_OR_RESPONSE"
    finally:
        key=None
        request=None
        report["latency_ms"]=int((time.monotonic()-started)*1000)
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        os.chmod(REPORT,0o600)
        print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:
        self_test()
    elif sys.argv[1:]==["--execute-once"]:
        execute()
    else:
        raise SystemExit("Usage: p7_ocr.py --self-test OR --execute-once (only after OFFLINE preflight acceptance)")
