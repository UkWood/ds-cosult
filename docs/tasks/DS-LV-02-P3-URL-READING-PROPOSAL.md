# DS-LV-02/P3 — Native URL Reading Conformance (Proposal Only)

**Дата:** 2026-11-17  
**Статус:** **P3 SCOPE AGREED BY OWNER — OFFLINE PREFLIGHT APPROVED; PAID GO REQUIRES EXPLICIT NUMERIC LIMIT**
**Основание:** DS-LV-02/P2 standalone Search PASS; следующее качественно иное свойство — **model-directed URL reading**.

## Goal

Проверить, может ли `deepseek-flash` с нативным инструментом `deepseek_read_url` самостоятельно прочитать содержимое конкретного публичного URL и ответить с подтверждаемым фрагментом. Эта проверка НЕ тождественна standalone Search API или Fetch API.

## Model request (design, do not execute yet)

```json
{
  "model":"deepseek-flash",
  "thinking":{"type":"disabled"},
  "tools":[{"type":"deepseek_read_url"}],
  "messages":[{"role":"user","content":"Открой https://example.com/ и назови заголовок H1, указанный на странице. Не используй другие сайты."}],
  "max_tokens":256,
  "stream":false
}
```

`POST https://api.deepseek.com/chat/completions`. Public, synthetic/neutral webpage. The model decides whether to actually invoke the tool: `tools declared` ≠ `tool invoked`. DeepSeek docs state `tool_choice` **cannot name** `deepseek_read_url`, and the URL must occur in the user message. Do not force the tool. Use only URL reading, no `deepseek_web_search`.

Expected page H1 at preparation: `Example Domain`; verify from actual retrieval, not model guess. Answer alone may be guessed. Positive proof: **actual server_tool_calls** with read/fetch action and URL `example.com`, successful tool status, answer fidelity and any references/annotations. If tool was declared but not invoked: `INCONCLUSIVE`, not PASS.

## Execution control (requires separate owner decision)

Propose **at most 1 HTTP request**, `max_tokens=256`, `thinking=disabled`, no retry, no redirects, hidden `getpass`, protected local attempted.marker and redacted JSON. Need preflight refresh of API docs, limits, token/tool charges and actual budget.

**Cost:** provider may charge model input/output tokens plus a page Fetch operation (official published Fetch $0.75/1,000); number of server operations not guaranteed hard-capped merely by one HTTP call. **No authorized spending limit and no permission to execute** this proposed P3.

Do not log raw page text, tool encrypted payload, API key or hidden reasoning. Only structured redacted evidence/usage/billing estimate, URL and verified title.

## Approval request

Architecture Session A may request specific OWNER GO for P3 after presenting estimated costs and residual server-tool billing risks. Existing P2 GO is exhausted and **must not carry over**. No autonomous start of P3.

Official primary source: https://api-docs.deepseek.com/guides/web_tools/ (URL Reading / Chat Completions API sections).

## Preparation after user consent (2026-11-17)

Владелец ответил «Согласовано продолжай» на предложение P3, но предыдущая формулировка не указывала конкретной суммы бюджета. Поэтому это согласие принято как разрешение подготовить и проверить **бесплатный P3 preflight**, а не как утверждение денежного потолка. **Платный вызов до отдельного подтверждения суммы не выполнять.**

- Proposed limit: **one HTTP POST / $0.01 USD**; этот лимит должен быть принят владельцем явно.
- Peak Flash tariff: input cache miss $0.30 / 1M; output $1.20 / 1M. Fetch tool: $0.75 per 1,000 successful page fetches. Один fetch + 500 prompt tokens + 256 output tokens оценивается в ~$0.0012072 по пиковым тарифам; это **estimate not hard cap**. Дополнительные tool calls могут стоить денег даже при одном HTTP.
- Test fixture: `https://example.com/`, current title `Example Domain` (visually verified via public web); answer alone cannot prove real read.
- Only tool declared: `deepseek_read_url`. No `tool_choice`, no `deepseek_web_search`, thinking disabled.
- `server_tool_calls[].calls[].{type,kind,status,action.url,page.title,signature}` must prove `type=deepseek_read_url`, `kind=read_link`, `status=completed`, same host, signature present. Raw signature and reasoning NEVER logged.
- Track `usage.server_tool_use.tool_fetch` for billed tool operations (not `web_fetch_requests`), tokens, estimated vs actual billing.
- Official URL reading docs https://api-docs.deepseek.com/guides/web_tools/ ; pricing https://api-docs.deepseek.com/quick_start/pricing/.
- Offline script in `scripts/validation/ds_lv_02_p3_url_read.py`, `--self-test` performs three synthetic checks with **0 network requests**.
- On execution a persistent `logs/ds-lv-02-p3-attempted.marker` is created atomically. Never retry after any outcome without new owner authorisation.
- Do not publish closed Core/GT. No Merge, no DS-02, no production. P4..P9 not authorized.

### Linux/WSL staged handoff
First download the script from a pinned commit, compile it with Python, run `--self-test`, compute SHA-256, and return output. **Do not execute the script without `--self-test` until the numeric spending limit is separately confirmed.**

## Offline preflight update — PASS
WSL client report: `python3 -m py_compile` completed, `--self-test` PASS, network requests 0 and API cost $0, script SHA-256 `1de63e655bc84c19fce73076442280946ff099d06d5b3ae8898b4a8cd8fc26e2`. See `../evidence/DS-LV-02-P3-OFFLINE-PREFLIGHT.md`. **Paid P3 STILL NOT AUTHORIZED.**
