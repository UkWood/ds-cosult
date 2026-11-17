# DS-LV-02/P3 — Native URL Reading Conformance (Proposal Only)

**Дата:** 2026-11-17  
**Статус:** **PROPOSED — NO OWNER GO / NO PAID EXECUTION**
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
