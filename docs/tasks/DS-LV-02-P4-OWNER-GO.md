# DS-LV-02/P4 — Explicit Owner GO for Native DeepSeek Web Search

**Дата:** 2026-11-17  
**Статус:** **OWNER GO EXERCISED — 1 PAID HTTP POST / P4 ACCEPTED WITH REVIEW NOTES**  
**Бюджет:** **$0.01 USD**, организационный лимит, не enforced hard cap DeepSeek.  
**Основание:** пользователь ответил «Подтверждаю» на точный вопрос: «Подтверждаете GO для одного платного вызова P4 с организационным лимитом $0,01 USD, учитывая, что один запрос может инициировать несколько оплачиваемых Search/Fetch-операций и лимит не гарантирован технически?»

## Allowed scope

- 1 `POST https://api.deepseek.com/chat/completions` with `model=deepseek-flash`, `thinking.type=disabled`, `tools:[{"type":"deepseek_web_search"}]`, `max_tokens=400`, `stream=false`.
- Exactly one user prompt about official public DeepSeek November 13, 2026 announcement and Search/Fetch, in Russian.
- Script pinned before owner GO: `scripts/validation/ds_lv_02_p4_web_search.py`, commit `33a784c1f3f526a77226bfe2d26ab30e535fe3d1`; script Git blob `5d69736f7282a3b72ff87b1dbe1840969398850b`. Local SHA-256 reported `c10bd4a6b22aedb74f059a1d089c089e6686f70c6b247c993b315bd2710ba0bd`. Local `py_compile` and `--self-test` PASS; network 0/cost $0.
- Input key is locally hidden via `getpass`, never uploaded to repository or sent to chat.
- No retry, no redirect, no other tools, no private materials, no file upload. Local exclusive `attempted.marker` prevents reruns after one attempt, even on HTTP error/timeout.
- Read-only source validation after P4, if necessary, without calling DeepSeek again.

## Billing hazard acknowledged

One outer HTTP request may trigger several server-side `tool_search` / `tool_fetch` billed units, which **cannot be forced under $0.01 by this script**. Published per Search/Fetch operation price at setup: $0.00075, plus model token costs; actual billing unknown until account-level reconciliation. The user was informed of residual risk in the approval question and confirmed.

## Acceptance policy

- **Tool capability:** inspect `message.server_tool_calls[].calls[]`; `deepseek_web_search`, completed status, nonempty search results. Tool declared but not invoked => INCONCLUSIVE.
- **Citation:** compare `message.annotations[].url_citation` to search sources; no fabricated citation.
- **Factual correctness:** independent public official release verification; do not auto-mark based on substring match. 
- **Language:** reply should be in Russian; deviations noted separately.
- **Usage:** model tokens and `usage.server_tool_use.tool_search/tool_fetch` (billed operations), estimated vs actual spend separated.

## Pre-execution evidence

`docs/evidence/DS-LV-02-P4-OFFLINE-PREFLIGHT.md` — accepted as offline-only, 0 network/0 provider cost.

**P4 is NOT YET EXECUTED.** After one invocation, this GO is exhausted regardless of outcome. P5..P9 remain NOT AUTHORIZED; no merge, no DS-02, no production, no hidden Core/GT, no changes to NEW RAG or Saturn-Main-Site.

## Actual execution (2026-11-17 19:40:03 UTC)
One owner-approved paid POST was used, HTTP 200, 3 billable search operations, 0 fetch, 9696 model tokens, latency 3638 ms; estimated peak $0.0054315, off-peak cache-miss $0.00384075; actual billed amount unknown. Acceptance `../acceptance/DS-LV-02-P4-ARCHITECTURE-ACCEPTANCE.md`. **No P4 authorization remains.**
