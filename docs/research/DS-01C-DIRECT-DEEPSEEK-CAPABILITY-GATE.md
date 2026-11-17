# DS-01C — Direct DeepSeek API Capability & Conformance Gate v0.1

**Дата:** 2026-11-17  
**Статус:** BASE CHAT, THINKING basic, standalone Search, native URL Reading, non-thinking native Web Search, and thinking+search `deep_search` capabilities проверены; standalone Fetch and other tools UNTESTED; каждый платный вызов требует отдельного GO.  
**Источник:** официальная документация `api-docs.deepseek.com`.

## Endpoint matrix
| Capability | Native DeepSeek route / contract | Doc status | Runtime |
|---|---|---|---|
| OpenAI-compatible chat | `POST https://api.deepseek.com/chat/completions` | DOCUMENTED | **PASS LV-API-01** |
| Flash | model `deepseek-flash` (V4.1-Flash-1017 по документации) | DOCUMENTED | **PASS: alias observed `deepseek-flash` only** |
| Thinking | `thinking: {"type":"enabled"}` | DOCUMENTED | **PASS: DS-LV-02/P1; reasoning_tokens=65** |
| Web search | `tools:[{"type":"deepseek_web_search"}]` | DOCUMENTED | **P4 PASS WITH REVIEW NOTES; 1 completed call / 3 billed searches, citations** |
| Deep thinking search | thinking + web tool | DOCUMENTED | UNTESTED |
| URL read | `tools:[{"type":"deepseek_read_url"}]` | DOCUMENTED | **P3 PASS with fixture/language review notes; 1 read_link, 1 billed tool_fetch** |
| Managed Search & Fetch | `POST /v1/tools/search`, `POST /v1/tools/fetch` | DOCUMENTED | **Search: P2 PASS (HTTP 200, 1 result); Fetch: UNTESTED** |
| PDF / Word / PPT | `POST /files`, `purpose=text_recognition` or `rich_layout_recognition` | DOCUMENTED | UNTESTED |
| PDF file reference | user content part `{"type":"file","file_id":"..."}` | DOCUMENTED | UNTESTED |
| OCR independent | `POST /v1/tools/ocr` | DOCUMENTED | UNTESTED |
| Safety | `safety_check` as documented for public apps | DOCUMENTED | UNTESTED |
| Multi-turn continuity | pass relevant provider content blocks unchanged | DOCUMENTED | UNTESTED |

## Test suite (no execution authorization)
| ID | Test | PASS condition |
|---|---|---|
| DSAPI-01 | Auth / short chat | model, finish, usage, latency, redacted raw response captured |
| DSAPI-02 | Model alias check | observed model and version policy recorded; no invented pinning |
| DSAPI-03 | Thinking on/off | output behavior and reasoning metadata confirmed for actual account |
| DSAPI-04 | Web tool | server tool actually invoked vs merely declared; citations and retrieval logged |
| DSAPI-05 | Deep thinking search | multi-step search confirmed by actual tool blocks |
| DSAPI-06 | URL reading | URL from last user message read as intended, if tool actually called |
| DSAPI-07 | Search/Fetch raw APIs | returned content and real URL validated, separate from model search |
| DSAPI-08 | File input, text | original PDF SHA-256, upload purpose, file ID, parsing success, page mapping |
| DSAPI-09 | File rich layout | figure detection and interpretation checked against original page visually |
| DSAPI-10 | OCR | page-by-page output mapped to original, compare text/rich modes |
| DSAPI-11 | Multi-turn | source blocks and prior referents preserved without fabricated facts |
| DSAPI-12 | Safety/cost/errors | budget, retention, API errors, retry, safe redaction handled |

## Requirements
- Secret via local environment `DEEPSEEK_API_KEY`, never send to GitHub or ChatGPT.
- Tests on public/synthetic fixtures until data transfer rights confirmed.
- Actual pricing and API quotas verified before paid usage; previous estimates cannot be taken as guaranteed.
- No tool-call success inferred from merely sending the tool in `tools`.
- Preserve compare A/B/C0 parity: model, thinking, effective token limits, source set (for controlled mode), run timestamps.
- Code/validation sessions only with scoped owner authorization.
- Safety and privacy independent of direct provider: native tools are not a substitute for evidence verifier.

## Gate semantics
`PASS` with reproducible evidence; `PARTIAL` if incomplete provenance; `FAIL`; `UNTESTED`. No automatic transition to DS-02. AI Tunnel tests retained as superseded historical documents.
