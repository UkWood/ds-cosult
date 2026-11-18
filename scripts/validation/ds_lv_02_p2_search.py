#!/usr/bin/env python3
"""DS-LV-02/P2: ONE authorized DeepSeek standalone Search call. No retries."""
import datetime
import getpass
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

URL = "https://api.deepseek.com/v1/tools/search"
QUERY = "DeepSeek API Search Fetch site:api-docs.deepseek.com"
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

os.umask(0o077)
folder = Path.home() / "ds-consult-validation" / "logs"
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
report = folder / "ds-lv-02-p2-redacted.json"
marker = folder / "ds-lv-02-p2-attempted.marker"
if report.exists() or marker.exists():
    raise SystemExit("STOP: P2 was already attempted/reported. NO RETRY.")
if not (sys.stdin.isatty() and sys.stderr.isatty()):
    raise SystemExit("STOP: use an interactive WSL terminal.")
key = getpass.getpass("DeepSeek API key (hidden, terminal only): ")
if not key.strip():
    raise SystemExit("STOP: empty key; no request made.")

payload = {"query": QUERY, "count": 1, "need_content": False}
req = urllib.request.Request(
    URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    method="POST",
)
result = {
    "test_id": "DS-LV-02-P2",
    "authorization": "OWNER_GO_2026-11-17_ONE_SEARCH_USD_0.01",
    "provider": "direct DeepSeek",
    "endpoint": URL,
    "query": QUERY,
    "count": 1, "need_content": False,
    "http_requests_attempted": 0,
    "model_invoked": False, "fetch_invoked": False,
    "files_uploaded": False,
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "result_count": None, "search_results": [],
    "estimated_search_charge_usd": None,
    "actual_billing_usd": None,
    "status": "NOT_EXECUTED",
}
try:
    fd = os.open(str(marker), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    raise SystemExit("STOP: attempt marker already exists.")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("DS-LV-02 P2 one-attempt guard: NEVER delete to retry without new GO.\n")
start = time.monotonic()
try:
    result["http_requests_attempted"] = 1
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=40) as response:
        result["http_status"] = response.status
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("response_too_large")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("unexpected_json")
    result["api_error_present"] = bool(data.get("error"))
    items = data.get("results")
    if result["api_error_present"]:
        result["status"] = "FAIL_API_ERROR"
    elif not isinstance(items, list):
        result["status"] = "FAIL_MISSING_RESULTS"
    elif not items:
        result["result_count"] = 0
        result["estimated_search_charge_usd"] = 0.0
        result["status"] = "PARTIAL_EMPTY_RESULTS"
    else:
        result["result_count"] = len(items)
        for item in items[:1]:
            if not isinstance(item, dict):
                raise ValueError("malformed_result")
            link = str(item.get("url") or "")
            u = urllib.parse.urlparse(link)
            valid = u.scheme in ("https", "http") and bool(u.hostname)
            result["search_results"].append({
                "title": str(item.get("title") or "")[:220],
                "url": link[:1500],
                "valid_url": valid,
                "domain": u.hostname or "",
                "snippet_preview": str(item.get("snippet") or "")[:240],
                "rerank_score": item.get("rerank_score"),
                "authority": item.get("authority"),
                "date": item.get("date"),
                "returned_content_empty": item.get("content") == "",
            })
        ok = (result["http_status"] == 200 and len(items) == 1
              and result["search_results"][0]["valid_url"]
              and result["search_results"][0]["returned_content_empty"])
        result["status"] = "PASS" if ok else "PARTIAL_REVIEW_REQUIRED"
        result["estimated_search_charge_usd"] = 0.00075
except urllib.error.HTTPError as e:
    result["http_status"] = e.code
    result["status"] = "BLOCKED_HTTP_ERROR"
except Exception as e:
    result["status"] = "BLOCKED_TRANSPORT_OR_RESPONSE"
    result["error_type"] = type(e).__name__
finally:
    key = None
    req = None
    result["latency_ms"] = round((time.monotonic() - start) * 1000)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(report, 0o600)
    print(json.dumps(result, ensure_ascii=False, indent=2))
