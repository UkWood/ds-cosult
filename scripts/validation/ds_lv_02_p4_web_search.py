#!/usr/bin/env python3
"""DS-LV-02/P4 controlled DeepSeek native web-search validation.
--self-test is offline, FREE and requires no API key.
Normal mode requires SEPARATE numeric paid GO. Exactly one HTTP attempt, no retries.
"""
import datetime
import getpass
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENDPOINT = "https://api.deepseek.com/chat/completions"
QUESTION = ("Используй веб-поиск и найди официальный анонс DeepSeek от 13 ноября 2026 года "
            "о новых возможностях API, включая Search и Fetch. Ответь по-русски: "
            "назови две возможности, дату и ссылку на официальный источник. "
            "Если поиск не выполнился, прямо скажи об этом. Не выдумывай ссылки.")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def domain(url):
    try:
        p = urllib.parse.urlparse(str(url or ""))
        return p.hostname if p.scheme in ("https", "http") else None
    except (TypeError, ValueError):
        return None


def evaluate(doc, status):
    """Separate capability, citation trace and answer correctness."""
    out = {
        "http_status": status, "api_error_present": bool(doc.get("error")),
        "model_observed": doc.get("model"), "finish_reason": None,
        "answer_preview": "", "answer_has_cyrillic": False,
        "search_tool_invoked": False, "search_calls_total": 0,
        "search_calls_completed": 0, "search_queries_total": 0,
        "unexpected_tool_calls": 0, "search_call_observations": [],
        "source_urls": [], "citation_urls": [], "citation_source_overlap": False,
        "usage": {}, "billed_tool_search": None, "billed_tool_fetch": None,
        "estimated_peak_cost_usd": None,
        "tool_gate": "INCONCLUSIVE", "citation_gate": "NOT_VERIFIED",
        "factual_answer_gate": "NEEDS_SOURCE_REVIEW", "status": "INCONCLUSIVE"
    }
    choices = doc.get("choices") or []
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    msg = choice.get("message") or {}
    if not isinstance(msg, dict):
        msg = {}
    out["finish_reason"] = choice.get("finish_reason")
    answer = msg.get("content") if isinstance(msg.get("content"), str) else ""
    out["answer_preview"] = answer[:480]
    out["answer_has_cyrillic"] = any("\u0400" <= c <= "\u052f" for c in answer)
    urls = []
    steps = msg.get("server_tool_calls") or []
    for step in steps if isinstance(steps, list) else []:
        if not isinstance(step, dict):
            continue
        for call in (step.get("calls") or []):
            if not isinstance(call, dict):
                continue
            action = call.get("action") or {}
            if not isinstance(action, dict):
                action = {}
            valid = (call.get("type") == "deepseek_web_search"
                     and call.get("kind") == "search"
                     and action.get("type") == "search")
            if not valid:
                out["unexpected_tool_calls"] += 1
                continue
            out["search_tool_invoked"] = True
            out["search_calls_total"] += 1
            queries = action.get("queries") or []
            out["search_queries_total"] += len(queries) if isinstance(queries, list) else 0
            if call.get("status") == "completed":
                out["search_calls_completed"] += 1
            sources = call.get("sources") or []
            for src in sources if isinstance(sources, list) else []:
                if isinstance(src, dict) and domain(src.get("url")):
                    urls.append(str(src["url"]))
            if len(out["search_call_observations"]) < 10:
                out["search_call_observations"].append({
                    "status": call.get("status"),
                    "query_count": len(queries) if isinstance(queries, list) else None,
                    "source_count": len(sources) if isinstance(sources, list) else None,
                    "error_code": (call.get("error") or {}).get("code") if isinstance(call.get("error"), dict) else None
                })
    out["source_urls"] = list(dict.fromkeys(urls))[:8]
    annotations = msg.get("annotations") or []
    for ann in annotations[:12] if isinstance(annotations, list) else []:
        if not isinstance(ann, dict):
            continue
        c = ann.get("url_citation") or {}
        if ann.get("type") == "url_citation" and isinstance(c, dict) and domain(c.get("url")):
            out["citation_urls"].append(str(c["url"])[:1500])
    out["citation_source_overlap"] = bool(set(out["citation_urls"]) & set(urls))
    usage = doc.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if isinstance(usage.get(k), int):
            out["usage"][k] = usage[k]
    server_use = usage.get("server_tool_use") or {}
    if not isinstance(server_use, dict):
        server_use = {}
    for k in ("tool_search", "tool_fetch", "web_search_requests", "web_fetch_requests"):
        if isinstance(server_use.get(k), int):
            out["usage"][k] = server_use[k]
    out["billed_tool_search"] = server_use.get("tool_search") if isinstance(server_use.get("tool_search"), int) else None
    out["billed_tool_fetch"] = server_use.get("tool_fetch") if isinstance(server_use.get("tool_fetch"), int) else None
    if all(isinstance(x, int) for x in (
            usage.get("prompt_tokens"), usage.get("completion_tokens"),
            out["billed_tool_search"], out["billed_tool_fetch"])):
        out["estimated_peak_cost_usd"] = round(
            (usage["prompt_tokens"] * 0.30 + usage["completion_tokens"] * 1.20) / 1000000
            + 0.00075 * (out["billed_tool_search"] + out["billed_tool_fetch"]), 8)
    if status != 200 or out["api_error_present"]:
        out["tool_gate"] = "FAIL_API"
    elif not out["search_tool_invoked"]:
        out["tool_gate"] = "INCONCLUSIVE_NOT_INVOKED"
    elif not out["search_calls_completed"] or not out["source_urls"]:
        out["tool_gate"] = "PARTIAL_NO_COMPLETED_SEARCH_SOURCE"
    elif out["unexpected_tool_calls"]:
        out["tool_gate"] = "PARTIAL_UNEXPECTED_TOOLS"
    else:
        out["tool_gate"] = "PASS"
    out["citation_gate"] = "PASS" if out["citation_source_overlap"] else "NOT_VERIFIED"
    out["status"] = out["tool_gate"]
    if out["tool_gate"] == "PASS" and (
            out["finish_reason"] != "stop" or out["model_observed"] != "deepseek-flash" or not answer):
        out["status"] = "PARTIAL_MODEL_OR_ANSWER"
    return out


def self_test():
    fixture = {
        "model": "deepseek-flash",
        "choices": [{"finish_reason": "stop", "message": {
            "content": "13 ноября 2026 года: Search и Fetch.",
            "annotations": [{"type": "url_citation", "url_citation": {
                "url": "https://api-docs.deepseek.com/news/news261113/"}}],
            "server_tool_calls": [{"calls": [{
                "type": "deepseek_web_search", "kind": "search",
                "action": {"type": "search", "queries": ["DeepSeek release"]},
                "status": "completed",
                "sources": [{"url": "https://api-docs.deepseek.com/news/news261113/"}]
            }]}]
        }}],
        "usage": {"prompt_tokens": 200, "completion_tokens": 50,
                  "total_tokens": 250, "server_tool_use": {"tool_search": 1, "tool_fetch": 0}}
    }
    a = evaluate(fixture, 200)
    assert a["tool_gate"] == "PASS" and a["citation_gate"] == "PASS"
    assert a["estimated_peak_cost_usd"] == 0.00087
    fixture["choices"][0]["message"]["server_tool_calls"] = []
    b = evaluate(fixture, 200)
    assert b["tool_gate"] == "INCONCLUSIVE_NOT_INVOKED"
    fixture["choices"][0]["message"]["server_tool_calls"] = [{"calls": [{
        "type": "deepseek_web_search", "kind": "search",
        "action": {"type": "search", "queries": ["test"]}, "status": "completed",
        "sources": [{"url": "https://another.example.org/page"}]}]}]
    c = evaluate(fixture, 200)
    assert c["tool_gate"] == "PASS" and c["citation_gate"] == "NOT_VERIFIED"
    assert c["factual_answer_gate"] == "NEEDS_SOURCE_REVIEW"
    assert evaluate({"error": {"message": "test"}}, 200)["tool_gate"] == "FAIL_API"
    print("DS-LV-02 P4 OFFLINE SELF-TEST: PASS")
    print("NETWORK REQUESTS: 0 | API COST: $0")


def run_paid():
    os.umask(0o077)
    folder = Path.home() / "ds-consult-validation" / "logs"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    report = folder / "ds-lv-02-p4-redacted.json"
    marker = folder / "ds-lv-02-p4-attempted.marker"
    if marker.exists() or report.exists():
        raise SystemExit("STOP: prior P4 attempt/report exists. NO RETRY.")
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    key = getpass.getpass("DeepSeek API key (hidden, local WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: empty key; no request sent.")
    body = {"model": "deepseek-flash", "thinking": {"type": "disabled"},
            "tools": [{"type": "deepseek_web_search"}],
            "messages": [{"role": "user", "content": QUESTION}],
            "max_tokens": 400, "stream": False}
    request = urllib.request.Request(
        ENDPOINT, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    result = {
        "test_id": "DS-LV-02-P4",
        "authorization": "P4_NUMERIC_BUDGET_GO_REQUIRED_BEFORE_PAID_RUN",
        "gateway": "direct", "requested_model": "deepseek-flash",
        "thinking_requested": "disabled", "declared_tools": ["deepseek_web_search"],
        "max_tokens": 400, "http_requests_attempted": 0,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "actual_billing_usd": None
    }
    try:
        fd = os.open(str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit("STOP: P4 attempted.marker exists.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("DS-LV-02/P4 single attempt reserved. No retry without new GO.\n")
    start = time.monotonic()
    try:
        result["http_requests_attempted"] = 1
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as resp:
            http_status = resp.status
            raw = resp.read(1000001)
        if len(raw) > 1000000:
            raise ValueError("response_too_large")
        doc = json.loads(raw.decode("utf-8"))
        if not isinstance(doc, dict):
            raise ValueError("response_not_object")
        result.update(evaluate(doc, http_status))
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["status"] = "BLOCKED_HTTP_ERROR"
    except Exception as exc:
        result["status"] = "BLOCKED_TRANSPORT_OR_RESPONSE"
        result["error_type"] = type(exc).__name__
    finally:
        key = None
        request = None
        result["latency_ms"] = round((time.monotonic() - start) * 1000)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(report, 0o600)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 1:
        run_paid()
    else:
        raise SystemExit("Usage: script.py [--self-test]. Never pass keys as argv.")
