#!/usr/bin/env python3
"""DS-LV-02/P3. One *separately authorised* direct DeepSeek URL-read request.

--self-test uses synthetic, offline JSON only and incurs ZERO charges.
Normal execution has no retries; key is captured via getpass and never logged.
"""
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

API = "https://api.deepseek.com/chat/completions"
TARGET = "https://example.com/"
MAX_BYTES = 1_000_000

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def evaluate(data, http_status):
    """Emit only safe, bounded evidence. Never serialize raw tool metadata."""
    out = {
        "http_status": http_status,
        "api_error_present": bool(data.get("error")),
        "model_observed": data.get("model"),
        "finish_reason": None,
        "answer_preview": None,
        "url_read_invoked": False,
        "url_read_completed": False,
        "url_read_call_count": 0,
        "unexpected_tool_call_count": 0,
        "read_calls": [],
        "annotations": [],
        "usage": {},
        "billed_tool_fetch": None,
        "billed_tool_search": None,
        "estimated_peak_cost_usd": None,
        "result": "INCONCLUSIVE",
    }
    choices = data.get("choices") or []
    choice = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    if not isinstance(message, dict):
        message = {}
    answer = str(message.get("content") or "").strip()
    out["answer_preview"] = answer[:160]
    out["finish_reason"] = choice.get("finish_reason")
    calls = []
    for step in (message.get("server_tool_calls") or []):
        if isinstance(step, dict):
            for call in (step.get("calls") or []):
                if isinstance(call, dict):
                    calls.append(call)
    for call in calls[:12]:
        action = call.get("action") or {}
        if not isinstance(action, dict):
            action = {}
        page = call.get("page") or {}
        if not isinstance(page, dict):
            page = {}
        url = str(page.get("url") or action.get("url") or "")
        url_host = urllib.parse.urlparse(url).hostname
        is_read = call.get("type") == "deepseek_read_url" and call.get("kind") == "read_link"
        if not is_read:
            out["unexpected_tool_call_count"] += 1
            continue
        out["url_read_invoked"] = True
        out["url_read_call_count"] += 1
        target_match = url_host in ("example.com", "www.example.com")
        completed = call.get("status") == "completed"
        out["read_calls"].append({
            "type": "deepseek_read_url",
            "kind": "read_link",
            "status": call.get("status"),
            "target_host_match": target_match,
            "page_title": str(page.get("title") or "")[:100],
            "signature_present": bool(call.get("signature")),
            "error_code": str((call.get("error") or {}).get("code") or "")[:80] if isinstance(call.get("error"), dict) else None,
        })
        if completed and target_match and bool(call.get("signature")):
            out["url_read_completed"] = True
    if len(calls) > 12:
        out["unrecorded_tool_call_count"] = len(calls) - 12
    for a in (message.get("annotations") or [])[:8]:
        if not isinstance(a, dict):
            continue
        u = a.get("url_citation") or {}
        if isinstance(u, dict):
            out["annotations"].append({
                "type": a.get("type"),
                "domain": urllib.parse.urlparse(str(u.get("url") or "")).hostname,
                "title": str(u.get("title") or "")[:100],
            })
    usage = data.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if isinstance(usage.get(k), int):
            out["usage"][k] = usage[k]
    stu = usage.get("server_tool_use") or {}
    if not isinstance(stu, dict):
        stu = {}
    for k in ("tool_fetch", "tool_search", "web_fetch_requests"):
        if isinstance(stu.get(k), int):
            out["usage"][k] = stu[k]
    out["billed_tool_fetch"] = stu.get("tool_fetch") if isinstance(stu.get("tool_fetch"), int) else None
    out["billed_tool_search"] = stu.get("tool_search") if isinstance(stu.get("tool_search"), int) else None
    if isinstance(usage.get("prompt_tokens"), int) and isinstance(usage.get("completion_tokens"), int) and out["billed_tool_fetch"] is not None:
        out["estimated_peak_cost_usd"] = round(
            0.30 * usage["prompt_tokens"] / 1_000_000
            + 1.20 * usage["completion_tokens"] / 1_000_000
            + 0.00075 * out["billed_tool_fetch"]
            + 0.00075 * (out["billed_tool_search"] or 0),
            8
        )
    if out["api_error_present"]:
        out["result"] = "FAIL_API_ERROR"
    elif http_status != 200 or not choices or not answer:
        out["result"] = "FAIL_RESPONSE"
    elif out["unexpected_tool_call_count"]:
        out["result"] = "PARTIAL_SCOPE_VIOLATION"
    elif not out["url_read_invoked"]:
        out["result"] = "INCONCLUSIVE_TOOL_NOT_INVOKED"
    elif not out["url_read_completed"]:
        out["result"] = "PARTIAL_READ_NOT_CONFIRMED"
    elif out["finish_reason"] != "stop" or out["model_observed"] != "deepseek-flash":
        out["result"] = "PARTIAL_MODEL_OR_FINISH"
    elif "example domain" not in answer.casefold():
        out["result"] = "PARTIAL_ANSWER_MISMATCH"
    else:
        out["result"] = "PASS"
    return out


def self_test():
    sample = {
        "model": "deepseek-flash",
        "choices": [{
            "finish_reason": "stop",
            "message": {
                "content": "Example Domain",
                "server_tool_calls": [{
                    "calls": [{
                        "type": "deepseek_read_url",
                        "kind": "read_link",
                        "action": {"type": "read_link", "url": TARGET},
                        "status": "completed",
                        "page": {"url": TARGET, "title": "Example Domain"},
                        "signature": "SYNTHETIC_TEST_ONLY",
                    }]
                }]
            }
        }],
        "usage": {
            "prompt_tokens": 120, "completion_tokens": 28, "total_tokens": 148,
            "server_tool_use": {"tool_fetch": 1, "tool_search": 0}
        }
    }
    ok = evaluate(sample, 200)
    assert ok["result"] == "PASS" and ok["url_read_completed"]
    sample["choices"][0]["message"].pop("server_tool_calls")
    assert evaluate(sample, 200)["result"] == "INCONCLUSIVE_TOOL_NOT_INVOKED"
    assert evaluate({"error": {"code": "synthetic"}}, 200)["result"] == "FAIL_API_ERROR"
    print("DS-LV-02 P3 OFFLINE SELF-TEST: PASS")
    print("NETWORK REQUESTS: 0 | API COST: $0")


def execute():
    os.umask(0o077)
    root = Path.home() / "ds-consult-validation" / "logs"
    root.mkdir(mode=0o700, exist_ok=True, parents=True)
    report = root / "ds-lv-02-p3-redacted.json"
    marker = root / "ds-lv-02-p3-attempted.marker"
    if report.exists() or marker.exists():
        raise SystemExit("STOP: P3 previously attempted or reported. NO RETRY.")
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    key = getpass.getpass("DeepSeek API key (hidden, WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: no key entered; no request.")
    payload = {
        "model": "deepseek-flash",
        "thinking": {"type": "disabled"},
        "tools": [{"type": "deepseek_read_url"}],
        "messages": [{
            "role": "user",
            "content": "Открой https://example.com/ и назови точный заголовок H1 на английском. Прочитай именно эту страницу; не угадывай и не обращайся к поиску."
        }],
        "max_tokens": 256,
        "stream": False,
    }
    req = urllib.request.Request(
        API,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    result = {
        "test_id": "DS-LV-02-P3",
        "authorization": "P3_BUDGET_OWNER_GO_REQUIRED_BEFORE_EXECUTION",
        "gateway": "direct",
        "model_requested": "deepseek-flash",
        "thinking_requested": "disabled",
        "tools_declared": ["deepseek_read_url"],
        "target_url": TARGET,
        "max_tokens": 256,
        "http_requests_attempted": 0,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "actual_billing_usd": None,
    }
    try:
        fd = os.open(str(marker), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit("STOP: attempted.marker exists. No rerun.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("DS-LV-02 P3: single attempt reserved. No retry without new GO.\n")
    start = time.monotonic()
    try:
        result["http_requests_attempted"] = 1
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(req, timeout=50) as resp:
            http_status = resp.status
            raw = resp.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("response_too_large")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("non_dict_json_response")
        result.update(evaluate(data, http_status))
    except urllib.error.HTTPError as err:
        result["http_status"] = err.code
        result["result"] = "BLOCKED_HTTP_ERROR"
    except Exception as err:
        result["result"] = "BLOCKED_TRANSPORT_OR_RESPONSE"
        result["error_type"] = type(err).__name__
    finally:
        key = None
        req = None
        result["latency_ms"] = round((time.monotonic() - start) * 1000)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(report, 0o600)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 1:
        execute()
    else:
        raise SystemExit("Usage: script.py [--self-test] (never pass API key as argument)")
