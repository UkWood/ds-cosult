#!/usr/bin/env python3
"""DS-LV-02/P5 -- deep thinking + native web search, ONE controlled attempt.
--self-test: offline synthetic tests only, no key, network, or cost.
--execute-after-owner-go: PAID, do not use without separate numeric approval.
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

API_URL = "https://api.deepseek.com/chat/completions"
QUESTION = (
    "Найди в официальной документации DeepSeek подтверждение двух положений: "
    "(1) при thinking enabled инструмент deepseek_web_search может искать и открывать "
    "страницы по ходу рассуждения; (2) Search и Fetch тарифицируются отдельно. "
    "Сопоставь источники, ответь кратко по-русски и дай ссылки на официальные страницы. "
    "Не предполагай достоверность без проверки. Ограничь число поисков и открытий страниц."
)
MAX_TOKENS = 1536
MAX_RESPONSE_BYTES = 4_000_000

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def safe_url(value):
    """Public URL only, strip query/fragment/credentials; safe for public diagnostics."""
    try:
        x = urllib.parse.urlsplit(str(value or ""))
        if x.scheme not in ("https", "http") or not x.hostname:
            return None
        host = x.hostname.lower()
        return urllib.parse.urlunsplit((x.scheme.lower(), host, x.path or "/", "", ""))[:750]
    except (TypeError, ValueError):
        return None

def rate_estimate(usage, tool_use):
    """Price estimate, never a verified provider invoice or a hard cap."""
    if not all(isinstance(usage.get(k), int) for k in ("prompt_tokens", "completion_tokens")):
        return None
    if not all(isinstance(tool_use.get(k), int) for k in ("tool_search", "tool_fetch")):
        return None
    image_searches = tool_use.get("tool_image_search", 0)
    if not isinstance(image_searches, int):
        return None
    prompt = usage["prompt_tokens"]
    output = usage["completion_tokens"]
    hit = usage.get("prompt_cache_hit_tokens")
    if not isinstance(hit, int):
        detail = usage.get("prompt_tokens_details") or {}
        hit = detail.get("cached_tokens") if isinstance(detail, dict) else 0
    if not isinstance(hit, int) or not 0 <= hit <= prompt:
        hit = 0
    miss = prompt - hit
    tool_cost = (tool_use["tool_search"] + tool_use["tool_fetch"] + image_searches) * .00075
    return {
        "peak_estimate_usd": round(miss * .30 / 1e6 + hit * .006 / 1e6 +
                                   output * 1.20 / 1e6 + tool_cost, 8),
        "offpeak_estimate_usd": round(miss * .15 / 1e6 + hit * .003 / 1e6 +
                                      output * .60 / 1e6 + tool_cost, 8),
        "interpretation": "Published rates only, not actual billing or maximum exposure"
    }

def evaluate(doc, http_status):
    """Never serialize raw reasoning, signatures, raw tool payloads, or API keys."""
    out = {
        "http_status": http_status, "api_error_present": bool(doc.get("error")),
        "requested_model": "deepseek-flash", "model_observed": doc.get("model"),
        "thinking_requested": "enabled", "reasoning_effort_requested": "low",
        "reasoning_text_logged": False,
        "reasoning_present": False, "reasoning_char_count": 0,
        "reasoning_tokens": None,
        "finish_reason": None, "answer_preview": "", "answer_char_count": 0,
        "answer_has_cyrillic": False, "answer_sha256": None,
        "tool_steps": 0, "deep_search_call_count": 0,
        "action_counts": {"search": 0, "open_page": 0, "find_in_page": 0},
        "completed_action_counts": {"search": 0, "open_page": 0, "find_in_page": 0},
        "search_query_count": 0, "unexpected_call_count": 0,
        "reported_search_sources_count": 0, "source_urls": [], "citation_urls": [],
        "citation_span_checks": [], "citation_source_overlap": False,
        "usage": {}, "billed_tool_search": None, "billed_tool_fetch": None,
        "billed_tool_image_search": None, "tool_usage_reported": False,
        "price_estimate": None,
        "thinking_gate": "INCONCLUSIVE", "search_gate": "INCONCLUSIVE",
        "citation_gate": "NOT_VERIFIED", "factual_answer_gate": "NEEDS_SOURCE_REVIEW",
        "language_gate": "NOT_EVALUATED", "status": "INCONCLUSIVE"
    }
    choices = doc.get("choices") or []
    c = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    msg = c.get("message") or {}
    if not isinstance(msg, dict):
        msg = {}
    answer = msg.get("content") if isinstance(msg.get("content"), str) else ""
    out["finish_reason"] = c.get("finish_reason")
    out["answer_preview"] = answer[:400]
    out["answer_char_count"] = len(answer)
    out["answer_sha256"] = hashlib.sha256(answer.encode("utf-8")).hexdigest() if answer else None
    out["answer_has_cyrillic"] = any("\u0400" <= ch <= "\u052f" for ch in answer)
    out["language_gate"] = "LIKELY_RUSSIAN" if out["answer_has_cyrillic"] else "REVIEW"
    reasoning_parts = []
    if isinstance(msg.get("reasoning_content"), str):
        reasoning_parts.append(msg["reasoning_content"])
    steps = msg.get("server_tool_calls") or []
    sources = []
    if not isinstance(steps, list):
        steps = []
    out["tool_steps"] = len(steps)
    for step in steps:
        if not isinstance(step, dict):
            continue
        if isinstance(step.get("reasoning_content"), str):
            reasoning_parts.append(step["reasoning_content"])
        calls = step.get("calls") or []
        for call in calls if isinstance(calls, list) else []:
            if not isinstance(call, dict):
                continue
            action = call.get("action") or {}
            if not isinstance(action, dict):
                action = {}
            a = action.get("type")
            if (call.get("type") != "deepseek_web_search" or
                    call.get("kind") != "deep_search" or
                    a not in out["action_counts"]):
                out["unexpected_call_count"] += 1
                continue
            out["deep_search_call_count"] += 1
            out["action_counts"][a] += 1
            if call.get("status") == "completed":
                out["completed_action_counts"][a] += 1
            if a == "search":
                queries = action.get("queries") or []
                if isinstance(queries, list):
                    out["search_query_count"] += len(queries)
                found = call.get("sources") or []
                if isinstance(found, list):
                    out["reported_search_sources_count"] += len(found)
                    for s in found:
                        if isinstance(s, dict):
                            url = safe_url(s.get("url"))
                            if url:
                                sources.append(url)
            elif a in ("open_page", "find_in_page"):
                page = call.get("page") or {}
                page_url = page.get("url") if isinstance(page, dict) else None
                url = safe_url(page_url or action.get("url"))
                if url:
                    sources.append(url)
    out["reasoning_char_count"] = sum(len(x) for x in reasoning_parts)
    out["reasoning_present"] = out["reasoning_char_count"] > 0
    unique_sources = list(dict.fromkeys(sources))
    out["source_urls"] = unique_sources[:16]
    annotations = msg.get("annotations") or []
    if not isinstance(annotations, list):
        annotations = []
    cited = []
    for a in annotations[:30]:
        if not isinstance(a, dict) or a.get("type") != "url_citation":
            continue
        cit = a.get("url_citation") or {}
        if not isinstance(cit, dict):
            continue
        url = safe_url(cit.get("url"))
        if not url:
            continue
        cited.append(url)
        i, j = cit.get("start_index"), cit.get("end_index")
        valid_span = isinstance(i, int) and isinstance(j, int) and 0 <= i < j <= len(answer)
        if len(out["citation_span_checks"]) < 12:
            out["citation_span_checks"].append(bool(valid_span))
    out["citation_urls"] = list(dict.fromkeys(cited))[:16]
    out["citation_source_overlap"] = bool(set(unique_sources) & set(cited))
    usage = doc.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    for k in ("prompt_tokens", "completion_tokens", "total_tokens",
              "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"):
        if isinstance(usage.get(k), int):
            out["usage"][k] = usage[k]
    detail = usage.get("completion_tokens_details") or {}
    if isinstance(detail, dict) and isinstance(detail.get("reasoning_tokens"), int):
        out["reasoning_tokens"] = detail["reasoning_tokens"]
    if isinstance(out["reasoning_tokens"], int) and out["reasoning_tokens"] > 0:
        out["reasoning_present"] = True
    tool_use = usage.get("server_tool_use") or {}
    if not isinstance(tool_use, dict):
        tool_use = {}
    out["tool_usage_reported"] = bool(tool_use)
    for k, dst in (("tool_search","billed_tool_search"),
                   ("tool_fetch","billed_tool_fetch"),
                   ("tool_image_search","billed_tool_image_search")):
        if isinstance(tool_use.get(k), int):
            out[dst] = tool_use[k]
    out["price_estimate"] = rate_estimate(usage, tool_use)
    if http_status != 200 or out["api_error_present"]:
        out["status"] = "FAIL_API_RESPONSE"
    elif not out["reasoning_present"]:
        out["status"] = "INCONCLUSIVE_THINKING_NOT_OBSERVED"
    elif out["completed_action_counts"]["search"] == 0:
        out["status"] = "INCONCLUSIVE_SEARCH_NOT_COMPLETED"
    elif not out["source_urls"]:
        out["status"] = "PARTIAL_NO_RETRIEVED_SOURCE"
    elif out["unexpected_call_count"] > 0:
        out["status"] = "PARTIAL_UNEXPECTED_TOOL_ACTION"
    elif out["finish_reason"] != "stop" or not answer:
        out["status"] = "PARTIAL_TRUNCATED_OR_EMPTY_ANSWER"
    elif not out["citation_source_overlap"]:
        out["status"] = "PARTIAL_CITATION_NOT_VERIFIED"
    else:
        out["status"] = "PASS_CAPABILITY_ONLY"
    out["thinking_gate"] = "PASS" if out["reasoning_present"] else "INCONCLUSIVE"
    out["search_gate"] = "PASS" if out["completed_action_counts"]["search"] > 0 else "INCONCLUSIVE"
    out["citation_gate"] = "PASS_STRUCTURAL_ONLY" if out["citation_source_overlap"] else "NOT_VERIFIED"
    return out, answer

def offline_test():
    good = {
        "model": "deepseek-flash",
        "choices": [{"finish_reason":"stop", "message":{
            "content": "По официальным источникам тариф указан отдельно.",
            "reasoning_content": "SYNTHETIC_REASONING_NOT_REAL",
            "annotations":[{"type":"url_citation","url_citation":{
                "url":"https://api-docs.deepseek.com/quick_start/pricing/",
                "start_index":0,"end_index":20}}],
            "server_tool_calls":[
                {"index":0,"reasoning_content":"synthetic step","calls":[{
                    "type":"deepseek_web_search","kind":"deep_search",
                    "action":{"type":"search","queries":["DeepSeek pricing tools"]},
                    "status":"completed","sources":[{"url":"https://api-docs.deepseek.com/quick_start/pricing/"}]
                }]},
                {"index":1,"reasoning_content":"","calls":[{
                    "type":"deepseek_web_search","kind":"deep_search",
                    "action":{"type":"open_page","url":"https://api-docs.deepseek.com/quick_start/pricing/"},
                    "status":"completed",
                    "page":{"url":"https://api-docs.deepseek.com/quick_start/pricing/","title":"Pricing"}
                }]}
            ]
        }}],
        "usage":{
            "prompt_tokens":400,"completion_tokens":100,"total_tokens":500,
            "prompt_cache_hit_tokens":100,
            "completion_tokens_details":{"reasoning_tokens":40},
            "server_tool_use":{"tool_search":1,"tool_fetch":1}
        }
    }
    first, answer = evaluate(good, 200)
    assert first["status"] == "PASS_CAPABILITY_ONLY", first
    assert first["reasoning_present"] and first["reasoning_tokens"] == 40
    assert first["action_counts"]["open_page"] == 1
    assert first["price_estimate"]["peak_estimate_usd"] == .0017106
    assert first["citation_span_checks"] == [True]
    good["choices"][0]["message"].pop("server_tool_calls")
    miss, _ = evaluate(good, 200)
    assert miss["status"] == "INCONCLUSIVE_SEARCH_NOT_COMPLETED"
    good["choices"][0]["message"]["server_tool_calls"] = []
    good["choices"][0]["message"]["reasoning_content"] = ""
    good["usage"]["completion_tokens_details"]["reasoning_tokens"] = 0
    no_think, _ = evaluate(good, 200)
    assert no_think["status"] == "INCONCLUSIVE_THINKING_NOT_OBSERVED"
    assert evaluate({"error":{"code":"synthetic"}}, 200)[0]["status"] == "FAIL_API_RESPONSE"
    assert safe_url("https://example.com/path?token=secret#frag") == "https://example.com/path"
    print("DS-LV-02 P5 OFFLINE SELF-TEST: PASS")
    print("NETWORK REQUESTS: 0 | API COST: $0")

def paid_once():
    os.umask(0o077)
    folder = Path.home() / "ds-consult-validation" / "logs"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = folder / "ds-lv-02-p5-attempted.marker"
    report = folder / "ds-lv-02-p5-redacted.json"
    answer_file = folder / "ds-lv-02-p5-answer-only-private.txt"
    if marker.exists() or report.exists() or answer_file.exists():
        raise SystemExit("STOP: P5 has a previous attempt or report. NO RETRY.")
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: use an interactive WSL terminal.")
    confirmed = input("P5 must have separate numeric OWNER GO. Type EXACTLY P5-APPROVED to proceed: ")
    if confirmed != "P5-APPROVED":
        raise SystemExit("STOP: no P5 owner confirmation entered; request not sent.")
    key = getpass.getpass("DeepSeek API key (hidden, local WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: no key entered; request not sent.")
    body = {
        "model":"deepseek-flash",
        "thinking":{"type":"enabled"},
        "reasoning_effort":"low",
        "tools":[{"type":"deepseek_web_search"}],
        "messages":[{"role":"user","content":QUESTION}],
        "max_tokens":MAX_TOKENS,
        "stream":False
    }
    request = urllib.request.Request(API_URL,
        data=json.dumps(body,ensure_ascii=False).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},
        method="POST")
    result = {
        "test_id":"DS-LV-02-P5",
        "owner_go_verified_by_script":False,
        "authorization_reference":"Requires separate explicit numerical owner GO in project docs",
        "gateway":"direct","model_requested":"deepseek-flash",
        "http_requests_attempted":0,
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool_declared":["deepseek_web_search"],
        "thinking_requested":"enabled","reasoning_effort_requested":"low",
        "max_tokens":MAX_TOKENS,"actual_billing_usd":None
    }
    fd = os.open(str(marker), os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        f.write("P5 single request attempt reserved. No retry without new owner GO.\n")
    start = time.monotonic()
    try:
        result["http_requests_attempted"] = 1
        with urllib.request.build_opener(NoRedirect()).open(request,timeout=100) as r:
            http_status=r.status
            raw=r.read(MAX_RESPONSE_BYTES+1)
        if len(raw)>MAX_RESPONSE_BYTES:
            raise ValueError("response_too_large")
        data=json.loads(raw.decode("utf-8"))
        if not isinstance(data,dict):
            raise ValueError("non_object_response")
        checks, answer = evaluate(data,http_status)
        result.update(checks)
        if answer:
            answer_file.write_text(answer,encoding="utf-8")
            os.chmod(answer_file,0o600)
            result["local_full_answer_available"]=True
        else:
            result["local_full_answer_available"]=False
    except urllib.error.HTTPError as e:
        result["http_status"]=e.code
        result["status"]="BLOCKED_HTTP_ERROR"
    except Exception as e:
        result["status"]="BLOCKED_TRANSPORT_OR_RESPONSE"
        result["error_type"]=type(e).__name__
    finally:
        key=None
        request=None
        result["latency_ms"]=round((time.monotonic()-start)*1000)
        report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        os.chmod(report,0o600)
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:
        offline_test()
    elif sys.argv[1:]==["--execute-after-owner-go"]:
        paid_once()
    else:
        raise SystemExit("Safe usage: script.py --self-test. Paid mode is LOCKED until separate owner GO.")
