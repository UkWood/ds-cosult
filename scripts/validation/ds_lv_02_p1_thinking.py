#!/usr/bin/env python3
"""DS-LV-02 / P1: one approved DeepSeek thinking-only smoke request.

No web tools, no uploads, no retries, no raw reasoning output.
Never pass secrets via shell arguments, chat, files or GitHub.
"""
import datetime
import getpass
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

os.umask(0o077)
root = Path.home() / "ds-consult-validation" / "logs"
root.mkdir(mode=0o700, parents=True, exist_ok=True)
report_path = root / "ds-lv-02-p1-redacted.json"
if report_path.exists():
    raise SystemExit("BLOCKED: P1 report already exists. Never rerun automatically.")

key = getpass.getpass("DeepSeek API key (hidden, local terminal only): ")
if not key.strip():
    raise SystemExit("BLOCKED: empty API key")

payload = {
    "model": "deepseek-flash",
    "thinking": {"type": "enabled"},
    "messages": [
        {"role": "user", "content": "Что больше: 9.11 или 9.8? Ответь только числом."}
    ],
    "max_tokens": 512,
    "stream": False,
}
request = urllib.request.Request(
    "https://api.deepseek.com/chat/completions",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    },
    method="POST",
)
result = {
    "test_id": "DS-LV-02-P1",
    "authorization": "OWNER_GO_2026-11-17_ONE_CALL_USD_0.01",
    "gateway": "direct",
    "requested_model": "deepseek-flash",
    "thinking_requested": "enabled",
    "reasoning_effort": "default_high",
    "max_tokens": 512,
    "tools_declared": False,
    "requests_attempted": 0,
    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "actual_billing_usd": None,
}
start = time.monotonic()
try:
    result["requests_attempted"] = 1
    with urllib.request.urlopen(request, timeout=60) as response:
        result["http_status"] = response.status
        body = json.load(response)
    result["api_error_present"] = bool(body.get("error"))
    result["response_id"] = body.get("id")
    result["observed_model"] = body.get("model")
    choices = body.get("choices") or []
    choice = choices[0] if choices else {}
    message = choice.get("message") or {}
    answer = (message.get("content") or "").strip()
    reasoning = message.get("reasoning_content") or ""
    result["finish_reason"] = choice.get("finish_reason")
    result["answer_preview"] = answer[:120]
    result["reasoning_content_present"] = bool(reasoning)
    result["reasoning_char_count"] = len(reasoning)
    usage = body.get("usage") or {}
    result["usage"] = usage
    input_n = usage.get("prompt_tokens")
    output_n = usage.get("completion_tokens")
    if isinstance(input_n, int) and isinstance(output_n, int):
        result["conservative_peak_model_cost_estimate_usd"] = round(
            0.30 * input_n / 1_000_000 + 1.20 * output_n / 1_000_000, 8
        )
    # No reasoning text is printed or persisted.
    expected = answer.replace(",", ".")
    if (result["http_status"] == 200
            and not result["api_error_present"]
            and result["observed_model"] == "deepseek-flash"
            and result["finish_reason"] == "stop"
            and expected == "9.8"
            and result["reasoning_content_present"]):
        result["status"] = "PASS"
    else:
        result["status"] = "PARTIAL_REVIEW_REQUIRED"
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
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(report_path, 0o600)
    print(json.dumps(result, ensure_ascii=False, indent=2))
