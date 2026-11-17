# DS-LV-02/P4 — Native Web Search (Proposal Only)

**Date:** 2026-11-17  
**Status:** **P4 scope owner approved / offline preparation allowed; paid execution NOT AUTHORIZED until a numeric budget is confirmed**

## Goal
Test model-controlled `deepseek_web_search` through direct Chat Completions in `deepseek-flash` with thinking disabled. This is **not** the already verified standalone Search API (`POST /v1/tools/search`) and **not** P3 `deepseek_read_url`.

## Scope
- Exact endpoint `POST https://api.deepseek.com/chat/completions`; `thinking.type=disabled`, `tools:[{"type":"deepseek_web_search"}]`, `stream=false`.
- Public, time-scoped official-doc query; e.g. "Найди официальный анонс DeepSeek от 13 ноября 2026 года о доступности Search/Fetch через API; приведи источник и дату". No proprietary data or hidden Core/GT.
- `max_tokens` bounded to 320–512; 1 HTTP POST; no automatic retry/redirect; hidden getpass; no uploaded files.
- PASS requires **real** `message.server_tool_calls` for search with successful status plus grounded public official result + annotation/citation; declaring tools or naming a URL without actual search => INCONCLUSIVE.
- Inspect actual per-request `usage.server_tool_use.tool_search/tool_fetch`, model tokens, time, error even at HTTP 200, reason, and observed model.
- Known finding from P3: content/structure/linguistic correctness must be evaluated **separately** from tool invocation; never substring-only PASS.

## Cost risk and authorization
A single Chat Completions request may trigger more than one server-side search and/or fetch. Price estimation using single search at $0.00075 is **not a hard upper bound**. Confirm limits/price on execution day, document risk and explicitly agree allowed HTTP requests and spend cap before actual call. Do **not** assume P3's one-call/$0.01 GO applies to P4.

## No automatic escalation
No P4 execution without new owner authorization; P5..P9, DS-02 code, Pilot/Core, Merge and production remain unauthorized.

## Owner continuation and precise limit gate — 2026-11-17

Владелец ответил «Разрешаю» на предложение продолжить P4, в котором была названа необходимость **отдельного GO с бюджетом**, но не была указана конкретная сумма. Поэтому решение интерпретируется как согласование **scope и бесплатной подготовки**, а не как разрешение выполнить неизвестные по стоимости серверные операции.

Предлагаемый денежный лимит **$0.01 USD организационный, не hard cap**; не выполнять платный P4 до явного подтверждения **один HTTP POST и $0.01 USD** с пониманием, что внутри может выполняться более одного billable Search/Fetch.

Official 2026-11-17: https://api-docs.deepseek.com/guides/web_tools/ , https://api-docs.deepseek.com/quick_start/pricing/ . Non-thinking web tool invocation: `message.server_tool_calls[].calls[].{type:"deepseek_web_search",kind:"search",action:{type:"search",queries:[...]},status:"completed",sources:[...]}`. Citations: `message.annotations[].url_citation`. Billed search count `usage.server_tool_use.tool_search`; multiple queries in one tool call billed separately. Search / Fetch unit $0.00075; Flash peak input $0.30/1M and output $1.20/1M.

One synthetic public question regarding the DeepSeek official 13 Nov 2026 release, no hidden Core/GT. Bounded `max_tokens=400`, `thinking=disabled`, only `deepseek_web_search`, 1 HTTP request, no auto retry, no redirect, no file uploads. `tool_choice` cannot force the tool.

**Linux validation**: `scripts/validation/ds_lv_02_p4_web_search.py --self-test` is offline, makes 0 network calls and costs $0. Real execution (without flag) needs separately confirmed numeric GO. The script records independently: actual search invocation / completed calls, citation overlap, safe model answer preview, language indicator, counted and billed Search/Fetch operations; answer accuracy stays pending human source review, never substring-graded. Exclusive attempt marker locks P4 after any first request.

P5..P9 NOT AUTHORIZED. No Merge/DS-02/production.

## WSL Offline Preflight Acceptance — 2026-11-17
Owner-provided output: `--self-test` PASS; `NETWORK REQUESTS: 0 | API COST: $0`; `py_compile` clean; local script SHA256 `c10bd4a6b22aedb74f059a1d089c089e6686f70c6b247c993b315bd2710ba0bd`. Source `../evidence/DS-LV-02-P4-OFFLINE-PREFLIGHT.md`. This establishes offline script readiness **only**. **P4 paid call not authorized until explicit numeric owner GO of 1 POST / $0.01 USD with server-side billing risk acknowledgement**.
