# DS-LV-02/P4 — Native Web Search (Proposal Only)

**Date:** 2026-11-17  
**Status:** **PROPOSED — NO OWNER GO / NO PAID EXECUTION**

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
