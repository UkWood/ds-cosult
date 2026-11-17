# DS-LV-02/P2 — Controlled Direct Search API

**Дата:** 2026-11-17  
**Статус:** **OWNER GO EXERCISED — ONE SEARCH EXECUTED / P2 ACCEPTED PASS**  
**Budget:** $0.01 USD as owner-approved organizational spending limit. Not a provider-enforced hard cap.  
**Authority:** user replied «Согласованно продолжай» after explicit proposal for one DS-LV-02/P2 request, max $0.01. P3–P9 NOT AUTHORIZED.

## Official contract
`POST https://api.deepseek.com/v1/tools/search`. Bearer DeepSeek API key.
```json
{"query":"DeepSeek API Search Fetch site:api-docs.deepseek.com","count":1,"need_content":false}
```
Documentation: https://api-docs.deepseek.com/api/search/ , https://api-docs.deepseek.com/guides/search/ , https://api-docs.deepseek.com/quick_start/pricing/.

A successful nonempty Search API call is billed $0.75/1,000 = **$0.00075** at the published rate; no LLM tokens, no Fetch or file parsing. A failed call or an empty `results` array is not billed per official guide. Billing remains unverified without account reconciliation.

## Execution (separate Linux/WSL validation, one logical step at a time)
- Source file: `scripts/validation/ds_lv_02_p2_search.py` in this Draft PR.
- Fetch from an **immutable commit SHA**, syntax preflight, inspect and record local script SHA256 before any API call.
- Run only after preflight. Interactive `getpass`; no echo, `.env`, key in shell/history/chat.
- Unique atomic `ds-lv-02-p2-attempted.marker` and `ds-lv-02-p2-redacted.json` stop any re-run. On HTTP timeout/error: STOP, no retry. No redirect allowed.
- Print only one redacted result (HTTP status; result count; title, URL, short snippet, authority, rank, latency, computed charge estimate). Do not copy raw payload or any secret.
- The Search response is **untrusted retrieval**, not authoritative technical evidence until source is verified separately.

## Acceptance
`PASS`: HTTP 200, no `error`, exactly 1 result, valid HTTP(S) URL, and empty content when `need_content=false`.
`PARTIAL_EMPTY_RESULTS`: HTTP 200 with zero results, not billed per documentation.
`PARTIAL_REVIEW_REQUIRED`: nonstandard result (invalid URL, unexpected content).
`FAIL/BLOCKED`: other errors, malformed response or non-200; never retry without another GO.

**NO AUTO P3 / WEB TOOL / OCR / PDF UPLOAD / DS-02 / MERGE / PRODUCTION.**

## Execution outcome, 2026-11-17
Performed one authorized Search POST at 19:00:23 UTC: HTTP 200, 1 result, 862 ms, estimated charge $0.00075 (not independently billed). Acceptance report: `../acceptance/DS-LV-02-P2-ARCHITECTURE-ACCEPTANCE.md`; redacted evidence `../evidence/DS-LV-02-P2-RESULT.json`. **No more P2 calls authorized.**
