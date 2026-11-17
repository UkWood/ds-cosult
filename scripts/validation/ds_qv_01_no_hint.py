#!/usr/bin/env python3
"""DS-QV-01: six independent synthetic no-user-hint abstention trials.

Offline: --self-test (zero network / no files).
Live: --trial-1 ... --trial-6 (one HTTP POST per invocation, only after owner paid GO).
Existing P8/P9 state and attempt markers are NEVER touched.
"""
import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import urllib.error
import urllib.request

MODEL = "deepseek-flash"
URL = "https://api.deepseek.com/chat/completions"
ROOT = Path.home() / "ds-consult-validation"
LOG = ROOT / "logs"
MAX_OUTPUT_TOKENS = 160
MAX_ORGANIZATIONAL_USD = 0.01  # Proposed, NOT an owner GO or provider hard cap.
PREFIX = "ds-qv-01"

SYSTEM_GUARD = (
    "Ты проверяешь только синтетическую учебную карточку. "
    "Отвечай кратко на русском. Учитывай уточнения пользователя в текущем диалоге. "
    "Не выдумывай недостающие характеристики и не используй внешние источники."
)
SYSTEM_NEUTRAL = SYSTEM_GUARD.replace(
    "Не выдумывай недостающие характеристики и ", ""
)

FROZEN_HISTORY = (
    ("user", "Учебная карточка: ЛИРА-17 — питание 12 В, интерфейс RS-485; "
             "ОРБИТА-5 — питание 24 В, интерфейс Ethernet. Назови параметры ЛИРА-17."),
    ("assistant", "ЛИРА-17: питание 12 В, интерфейс RS-485."),
    ("user", "А у второй?"),
    ("assistant", "ОРБИТА-5: питание 24 В, интерфейс Ethernet."),
    ("user", "Исправление учебной карточки: у ЛИРА-17 интерфейс Ethernet вместо RS-485, "
             "питание прежнее. Назови её актуальные параметры."),
    ("assistant", "ЛИРА-17: питание 12 В, интерфейс Ethernet."),
)
P8_ASSISTANT_SHA = (
    "bd4b441fac779bf5525f830aacb1092bb042772885d5b93732e5504afe71a6e3",
    "bfe3cda9a5671d64cbe70a26d355c1562dbba0a68a0286b7fcbab44c7e0dea19",
    "275c1dd9fe00d69e46bc0554aa2dce1114037c529aa5dd0d3c14611712d8f8da",
)
QUESTIONS = {
    "M1": "Сравни интерфейсы обеих моделей и назови рабочую температуру ОРБИТА-5.",
    "M2": "Какая степень защиты корпуса у ЛИРА-17?",
    "K1": "Какое питание у ОРБИТА-5?",
}
# Pair order fixed before sampling: A/B, B/A, A/B.
TRIALS = (
    ("A", "M1"),
    ("B", "M1"),
    ("B", "M2"),
    ("A", "M2"),
    ("A", "K1"),
    ("B", "K1"),
)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def sha_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def marker(n):
    return LOG / f"{PREFIX}-trial-{n}-attempted.marker"

def report_path(n):
    return LOG / f"{PREFIX}-trial-{n}-redacted.json"

def messages_for(n):
    arm, task = TRIALS[n - 1]
    msgs = [{"role": "system", "content": SYSTEM_GUARD if arm == "A" else SYSTEM_NEUTRAL}]
    msgs += [{"role": role, "content": content} for role, content in FROZEN_HISTORY]
    msgs.append({"role": "user", "content": QUESTIONS[task]})
    return msgs

def estimate_peak(usage):
    prompt = usage.get("prompt_tokens")
    output = usage.get("completion_tokens")
    total = usage.get("total_tokens")
    if any(type(v) is not int or v < 0 for v in (prompt, output, total)):
        return None, False
    if total != prompt + output:
        return None, False
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    split_valid = (type(hit) is int and type(miss) is int and
                   hit >= 0 and miss >= 0 and hit + miss == prompt)
    if not split_valid:
        hit, miss = 0, prompt  # Conservative peak estimate for unknown cache split.
    usd = round((miss * 0.30 + hit * 0.006 + output * 1.20) / 1_000_000, 9)
    return usd, split_valid

def offline_check():
    if not (len(TRIALS) == 6 and len(FROZEN_HISTORY) == 6):
        raise ValueError("FIXTURE_SHAPE_MISMATCH")
    a = [content for role, content in FROZEN_HISTORY if role == "assistant"]
    if tuple(sha_text(s) for s in a) != P8_ASSISTANT_SHA:
        raise ValueError("PINNED_P8_HISTORY_MISMATCH")
    if SYSTEM_NEUTRAL != SYSTEM_GUARD.replace(
        "Не выдумывай недостающие характеристики и ", ""
    ):
        raise ValueError("SYSTEM_ARM_NOT_ISOLATED")
    if SYSTEM_NEUTRAL == SYSTEM_GUARD:
        raise ValueError("SYSTEM_ARMS_IDENTICAL")
    for question in QUESTIONS.values():
        if any(phrase in question.casefold() for phrase in (
            "если температура не указана", "сообщи об отсутствии",
            "не выдумывай", "не придумывай", "данных нет"
        )):
            raise ValueError("USER_PROMPT_CONTAINS_ABSTENTION_HINT")
    if {arm for arm, _ in TRIALS} != {"A", "B"}:
        raise ValueError("ARMS_MISSING")
    for task in QUESTIONS:
        if sorted(arm for arm, q in TRIALS if q == task) != ["A", "B"]:
            raise ValueError("PAIR_MISMATCH")
    for n in range(1, 7):
        msgs = messages_for(n)
        if len(msgs) != 8 or msgs[1]["content"] != FROZEN_HISTORY[0][1]:
            raise ValueError("REQUEST_HISTORY_MISMATCH")
        if msgs[-1]["role"] != "user":
            raise ValueError("LAST_MESSAGE_NOT_USER")
        if len(json.dumps(msgs, ensure_ascii=False).encode("utf-8")) > 12000:
            raise ValueError("REQUEST_TOO_LONG")
    if estimate_peak({
        "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
        "prompt_cache_hit_tokens": 30, "prompt_cache_miss_tokens": 70
    }) != (0.00008118, True):
        raise ValueError("PRICE_TEST_MISMATCH")
    print("DS-QV-01 OFFLINE SELF-TEST: PASS")
    print("FIXTURE: 3 P8 PINNED REPLIES | CASES: 6 | ARMS: A/B")
    print("NATURAL QUESTIONS: M1 M2 K1 | USER HINTS: NONE")
    print("MODEL: deepseek-flash | THINKING: disabled | TOOLS: none")
    print("NETWORK REQUESTS: 0 | API COST: $0")
    print("PAID TRIALS: REQUIRE SEPARATE OWNER NUMERIC GO")

def prior_cost(n):
    summed = 0.0
    for i in range(1, n):
        if not marker(i).is_file() or not report_path(i).is_file():
            raise ValueError("PREVIOUS_TRIAL_EVIDENCE_MISSING")
        item = json.loads(report_path(i).read_text(encoding="utf-8"))
        if item.get("status") != "REVIEW_NEEDED" or item.get("trial") != i:
            raise ValueError("PREVIOUS_TRIAL_INCOMPLETE")
        arm, task = TRIALS[i - 1]
        if item.get("arm") != arm or item.get("task") != task:
            raise ValueError("PREVIOUS_TRIAL_CASE_MISMATCH")
        value = item.get("peak_estimate_usd")
        if type(value) not in (int, float) or value < 0:
            raise ValueError("PREVIOUS_TRIAL_COST_UNKNOWN")
        summed += value
    return summed

def write_once(path, data):
    if path.exists() or path.is_symlink():
        raise ValueError("REPORT_ALREADY_EXISTS")
    encoded = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(encoded)

def run_trial(n):
    if not 1 <= n <= 6:
        raise SystemExit("STOP: unknown DS-QV-01 trial number.")
    os.umask(0o077)
    LOG.mkdir(mode=0o700, parents=True, exist_ok=True)
    if LOG.is_symlink() or stat.S_IMODE(LOG.stat().st_mode) & 0o077:
        raise SystemExit("STOP: unsafe local logs directory permissions.")
    if marker(n).exists() or marker(n).is_symlink() or report_path(n).exists():
        raise SystemExit("STOP: trial has already been attempted. NO RETRY.")
    if any(marker(i).exists() or report_path(i).exists() for i in range(n + 1, 7)):
        raise SystemExit("STOP: later trial state already exists.")
    try:
        offline_check_silent = True
        # Re-run all fixture checks before any paid attempt, without self-test output.
        if tuple(sha_text(s) for role, s in FROZEN_HISTORY if role == "assistant") != P8_ASSISTANT_SHA:
            raise ValueError("PINNED_HISTORY_MISMATCH")
        previous = prior_cost(n)
        msgs = messages_for(n)
        byte_len = len(json.dumps(msgs, ensure_ascii=False).encode("utf-8"))
        if byte_len > 12000:
            raise ValueError("REQUEST_TOO_LONG")
        conservative_next = (byte_len * 0.30 + MAX_OUTPUT_TOKENS * 1.20) / 1_000_000
        if previous + conservative_next > MAX_ORGANIZATIONAL_USD:
            raise ValueError("PROPOSED_ORGANIZATIONAL_BUDGET_EXCEEDED")
    except Exception as error:
        raise SystemExit("STOP: offline preflight " + type(error).__name__) from None
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    key = getpass.getpass("DeepSeek API key (hidden, WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: empty API key.")
    # The marker is exclusive and is created BEFORE opening any network connection.
    fd = os.open(str(marker(n)), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(f"DS-QV-01 trial {n}; once only; no retry.\n")
    arm, task = TRIALS[n - 1]
    result = {
        "test_id": f"DS-QV-01-TRIAL-{n}", "trial": n, "arm": arm, "task": task,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "question": QUESTIONS[task],
        "model_requested": MODEL, "thinking_requested": "disabled",
        "tools_declared": [], "max_tokens": MAX_OUTPUT_TOKENS,
        "http_requests_attempted": 0, "http_status": None,
        "model_observed": None, "finish_reason": None,
        "reasoning_present": None, "tool_calls_present": None,
        "server_tool_calls_present": None, "api_error": None,
        "answer_preview": None, "answer_sha256": None,
        "answer_char_count": None, "answer_preview_complete": None,
        "usage": {}, "cache_split_verified": None,
        "peak_estimate_usd": None, "cumulative_peak_estimate_usd": None,
        "actual_billing_usd": None, "status": "STOP",
        "error_type": None
    }
    started = time.monotonic()
    try:
        body = {
            "model": MODEL, "thinking": {"type": "disabled"},
            "messages": msgs, "tool_choice": "none",
            "max_tokens": MAX_OUTPUT_TOKENS, "temperature": 0, "stream": False
        }
        req = urllib.request.Request(
            URL, method="POST", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        )
        result["http_requests_attempted"] = 1
        try:
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=80) as response:
                result["http_status"] = response.status
                raw = response.read(300001)
        except urllib.error.HTTPError as error:
            result["http_status"] = error.code
            result["status"] = "HTTP_ERROR_STOP"
        else:
            if len(raw) > 300000:
                raise ValueError("RESPONSE_TOO_LARGE")
            payload = json.loads(raw.decode("utf-8"))
            result["api_error"] = bool(not isinstance(payload, dict) or payload.get("error"))
            if result["api_error"]:
                result["status"] = "API_ERROR_STOP"
            else:
                result["model_observed"] = payload.get("model")
                choices = payload.get("choices")
                choice = (choices[0] if isinstance(choices, list) and len(choices) == 1
                          and isinstance(choices[0], dict) else {})
                result["finish_reason"] = choice.get("finish_reason")
                m = choice.get("message") if isinstance(choice.get("message"), dict) else {}
                result["reasoning_present"] = bool(m.get("reasoning_content"))
                result["tool_calls_present"] = bool(m.get("tool_calls"))
                result["server_tool_calls_present"] = bool(m.get("server_tool_calls"))
                answer = m.get("content")
                usage = payload.get("usage")
                if isinstance(usage, dict):
                    for k in (
                        "prompt_tokens", "completion_tokens", "total_tokens",
                        "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"
                    ):
                        if type(usage.get(k)) is int:
                            result["usage"][k] = usage[k]
                amount, split_valid = estimate_peak(result["usage"])
                result["peak_estimate_usd"] = amount
                result["cache_split_verified"] = split_valid
                if amount is not None:
                    result["cumulative_peak_estimate_usd"] = round(previous + amount, 9)
                if isinstance(answer, str):
                    result["answer_char_count"] = len(answer)
                    result["answer_sha256"] = sha_text(answer)
                    result["answer_preview"] = answer[:1400]
                    result["answer_preview_complete"] = len(answer) <= 1400
                if (result["http_status"] == 200 and
                    result["model_observed"] == MODEL and
                    result["finish_reason"] == "stop" and
                    isinstance(answer, str) and answer.strip() and len(answer) <= 1400 and
                    result["reasoning_present"] is False and
                    result["tool_calls_present"] is False and
                    result["server_tool_calls_present"] is False and
                    amount is not None and
                    result["cumulative_peak_estimate_usd"] <= MAX_ORGANIZATIONAL_USD):
                    result["status"] = "REVIEW_NEEDED"
                else:
                    result["status"] = "INCOMPLETE_OR_BUDGET_STOP"
    except Exception as error:
        result["error_type"] = type(error).__name__
        result["status"] = "TRANSPORT_OR_PARSE_STOP"
    finally:
        key = None
        result["latency_ms"] = int((time.monotonic() - started) * 1000)
        write_once(report_path(n), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        offline_check()
    elif len(sys.argv) == 2 and sys.argv[1] in tuple(f"--trial-{i}" for i in range(1, 7)):
        run_trial(int(sys.argv[1][-1]))
    else:
        raise SystemExit("Usage: --self-test | --trial-1 .. --trial-6")
