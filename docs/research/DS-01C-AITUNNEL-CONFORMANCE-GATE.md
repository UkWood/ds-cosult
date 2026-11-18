# DS-01C — AI Tunnel Provider Conformance Gate v0.1

> **HISTORICAL / SUPERSEDED.** Это неактивное задание. Использовать [Direct DeepSeek Capability Gate](DS-01C-DIRECT-DEEPSEEK-CAPABILITY-GATE.md).


**Status:** TEST DESIGN ONLY — NO AUTHORIZED API EXECUTION.  
**Date:** 2026-11-17.  
**Dependencies:** owner-supplied secure local key, approved ruble budget, provider policy and non-sensitive test payloads.

## Purpose
Before starting DS-02, establish which requested AI Tunnel capabilities really work for `deepseek-v4.1-flash` or a pinned version. Do not equate OpenAI wire format with feature identity.

## Reproducibility prerequisites
- Header only from local environment secret `AITUNNEL_API_KEY`; avoid values in stdout, report, PR.
- Gateway base `https://api.aitunnel.ru/v1`.
- Identify exact backend model/route and downstream provider; pin eligible provider when available; prevent hidden fallbacks.
- `provider.require_parameters:true` where appropriate. Tests that fail to enforce support are not positive confirmations.
- Capture request/response metadata, redacted log, timing, prompt/completion token counts and billed `usage.cost_rub`.
- Test corpus public/approved; no Core/GT leak.

## Sequential cases
| ID | Action | Acceptance evidence |
|---|---|---|
| AT-01 | Authenticated `GET /v1/models` and public catalog | Actual model ID, restrictions, pricing snapshot; no key disclosure |
| AT-02 | Minimal short chat completion | Successful content, observed model ID, request ID, usage, latency |
| AT-03 | Pinned-model attempt | Version-specific model availability; if unavailable choose and document fixed alternative, do not substitute invisibly |
| AT-04 | Reasoning toggle / capabilities | Record effective support and observable metadata, not mere HTTP status |
| AT-05 | Function tool-call | Correct structured tool call, argument validity, multi-round continuation |
| AT-06 | Gateway `aitunnel:web_search` | Actual search invocation (`usage.server_tool_use` if supplied), citations checked; distinguish enabled vs invoked |
| AT-07 | Provider pin / fallback / strict parameter policy | Downstream provider identifies; incompatible parameter yields explicit failure rather than silent ignored setting |
| AT-08 | Gateway PDF text | Public small pinned PDF, page provenance checked, record native vs gateway OCR/other parser |
| AT-09 | Gateway PDF table / figure | Independently evaluated diagram/table; no conclusion on OCR accuracy without physical-page review |
| AT-10 | Continuation and referents | Multi-round context preservation on exact provider/model without unexpected switch |
| AT-11 | Cost/budget diagnostics | Actual billed rubles, error 402 handling, per-key budget; no manual tariff guess |
| AT-12 | Failure modes | Network timeout, 4xx, server error, empty reply, invalid JSON, incomplete output, tool failure; fail closed |

Native DeepSeek `deepseek_web_search` / `deepseek_read_url` passthrough is NOT part of positive gateway contract until independently documented/proven; safe diagnostic probe may be proposed as separate extension, not assumed.

## Gate results
- `PASS`: request, observed response, provider identity and objective expectation captured.
- `PARTIAL`: basic functionality works, but provenance/tool reasoning missing; exclude affected tests from strict comparative claims.
- `FAIL`: no usable capability.
- `UNTESTED`: insufficient auth/budget/permission; not equivalent to fail or pass.
A/ B/ C0 variants cannot run as approved comparison if same effective model/provider and thinking settings cannot be proven.

## Blockers
- No actual API key supplied: no authenticated call.
- No ruble spending cap adopted.
- Public repository: hidden benchmark and private source documents may not be committed or transmitted.
- PDF bytes SHA-256 and physical page GT missing.

## Next action
Create a *separate, narrow, approved* coding/validation assignment (after owner approval) for AT-01..AT-12, store only redacted proof; do not start full DS-02 harness or production.
