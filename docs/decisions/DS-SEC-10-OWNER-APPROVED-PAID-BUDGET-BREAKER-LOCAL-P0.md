# DS-SEC-10 — Owner-Approved Global USD Breaker: Paid P1/P2 Blocked, Verified Local P0 Available

**Date:** 2026-11-18  
**Status:** **OWNER ACCEPTED — authoritative resolution of DS-EC-AR-02 / R1-CR05 (IMPORTANT)**  
**Project:** DS-консультант, existing Draft PR #1, `UkWood/ds-cosult`  
**Owner's exact decision:** «Утверждаю вариант A для R1-CR05: при исчерпании глобального USD-бюджета блокировать платные P1/P2, но разрешать защищённые локальные ответы P0 в пределах всех установленных ограничений. Зафиксируй решение и подготовь комплект к повторной независимой приёмке.»

## 1. Normative decision and precedence

**When the operator's global DeepSeek-paid USD day/month budget is exhausted or its risk reserve breaker is open, no new paid P1/P2 inference may be dispatched, but fully verified, entirely local P0 source-bound answers MAY be served** under every existing independent visitor/session/day/series/CPU/concurrency/security and private audit guard.

This is **no longer a proposal**. It supersedes the earlier open-owner-choice notes in DS-EC-03 §10.5, DS-EC-05 §13.3, and AR-T21 of the R1 fixture design. It clarifies the global-money-denial wording in previous DS-SEC-07/09 without changing their accepted per-IP **20 questions per operator-calendar day** or earlier decisions. Source and model acceptance requirements remain as before.

This authorization applies **only to model-paid USD exhaustion**. It is **not** permission to continue any operation after a separate server safety/CPU/infrastructure budget breaker or security incident requires the whole chatbot to stop. If the operator intentionally disables local technical service for an independent safety or resource incident, such a higher-priority non-monetary breaker may deny P0.

## 2. Route-specific expected behavior

| Situation | P0 deterministic source-grounded route | P1 LLM interpretation or P2 LLM answer-plan |
|---|---|---|
| Global paid USD budget has sufficient unreserved allowance | Allowed under normal IP/day/series/source/audit controls | Allowed only after full ProviderDispatchGuard, token and cost preflight, atomic monetary reservation |
| Global paid USD day/month budget exhausted or unknown (fail-closed for paid inference) | **Allowed** if a source-complete verified local answer can be produced safely, without any provider call or paid tool | **BLOCKED**, 0 new provider dispatch intent / POST and 0 provider-cost reservation |
| Exactly one or more required needs can be answered locally, others require model | A **source-verified partial** is allowed only if contract permits independent partial coverage and it clearly marks unresolved needs; one accepted visitor question | Paid P1/P2 blocked; never invent completion or silently issue model/tool request |
| No safe local answer/clarification can be produced without P1/P2 | No technical claim is emitted. Static service/support message; **not admitted** and no user question debit | Blocked as above |
| Daily visitor quota exhausted, 11th consecutive question, IP/session busy, overlength, out of Saturn scope or CPU/concurrency safety breaker | **BLOCKED** by the applicable guard regardless of model cost | **BLOCKED** |

**P0 must be genuinely zero-provider-traffic**: approved pinned site/PDF index, canonical `Entity/Fact/Relation/EvidenceRef`, `SourceCoverageReceipt` and `EvidenceEligibilityDecision` where required, deterministic `VerifiedClaim` / `ConflictPosition` and server renderer. Cached local answers must retain exact `bundle_id`, policy/dictionary revisions, evidence eligibility, scope and cache-invalidation obligations. **A cached raw LLM answer is not P0**, and hidden LLM classifiers/LLM rewrites/native paid tools are forbidden.

The user's message remains untrusted and cannot force the system to choose P0 or bypass a spending breaker. Route selection is server-owned, conservative, before any paid dispatch.

## 3. Accounting and failure order

1. Apply existing non-monetary admission gates first: canonical IP, one anonymous session and in-flight fence, ≤1,200 character question and ≤8 KiB JSON body, Saturn-only domain, Q1–Q10 series/cooldown and Q11+ support handoff, **20 accepted visitor questions/IP/operator-calendar day**, global CPU/concurrency safety guards and private audit availability.
2. Determine a valid **local P0 route** using locally available eligible source facts and approved templates (including honest source-scoped partial/needs_support/clarification). If P0 can serve an admissible question, **do not check its eligibility against the DeepSeek-paid USD allowance**. Atomically admit exactly **one user question**; paid provider reservation and counted POST remain **0**. Do not silently turn an answer needing model assistance into fabricated P0.
3. If a paid P1/P2 route is required, perform global model USD and full prompt/token preflight **before user-turn debit**. An exhausted day/month budget or uncertain reserve capacity is a pre-admission denial: **0 accepted visitor questions, 0 new provider attempt reservation, 0 dispatch-intent and 0 paid POST**. Return a static rate/budget/support notice; do not try a speculative paid POST.
4. Already admitted and durably reserved in-flight requests are handled according to the existing crash-safe `provider_attempt_slot_reserved` / `provider_post_dispatch_recorded` / uncertain dispatch protocol. Do not automatically retry after uncertain dispatch; do not cancel or misclassify prior charges merely because the breaker later trips.
5. Every admitted P0 turn is counted in the **20/day** quota, progressive series and private request/response audit. Idempotent replay uses the prior original-session result without another turn debit. Denied service notices may be minimally audited but do not consume question slots. Local CPU/concurrency abuse guards continue to apply.

**Safety precedence:** IP/day/series and global non-monetary safety denial > local P0 source eligibility > paid P1/P2 budget gate. The existence of a potential P0 route does not bypass another denial, and a paid model route cannot self-authorize by labeling itself free.

## 4. Boundary tests to design (not executed)

- **SEC10-T01 / AR-T21:** global model USD budget exhausted, same IP/day has capacity, eligible source-grounded P0 fact → answered with source citation, `accepted_turn_delta=1`, `provider_attempt_delta=0`, `provider_post_dispatch_delta=0`, `global_model_usd_delta=0`.
- **SEC10-T02:** same budget state, only P1/P2 can solve question → static no-paid-service notice, `accepted_turn_delta=0`, `provider_attempt_delta=0`, `provider_post_dispatch_delta=0`.
- **SEC10-T03:** local P0 answer available but IP day count=20 or series Q11 or same-IP lease busy → blocked, no new accepted turn.
- **SEC10-T04:** local source scope incomplete or contradictory; no safe full answer → safe qualified partial/clarification/needs_support where legitimately supported; never hallucinate or claim complete source coverage.
- **SEC10-T05:** cached previous raw model text presented as local P0 → reject cache promotion and require verified typed facts; no model bypass.
- **SEC10-T06:** USD breaker trips after paid request reserved/dispatched → original turn follows durable request state; no extra POST or false charge count on replay.
- **SEC10-T07:** USD budget available again after configured reset but visitor has exhausted 20/day → IP quota still blocks until its own configured calendar reset.

All scenarios are prospective offline fixtures using fake clock, fake model, fake store and synthetic source values only. They do not prove runtime behavior.

## 5. Operational limits and governance

- This decision **does not set** the actual global USD/day or USD/month figures. Operator budget values, IANA reset timezone, verified support phone/email, trusted proxy chain and privacy/legal audit controls remain launch configuration gates.
- All other accepted requirements remain: explicit `Не выдумывай недостающие технические характеристики.`, trusted Saturn website/PDF corpus, one anonymous active session/IP, technical memory expiry 15m, 30m series reset, 20 accepted questions/IP/day including P0, 10,000 total DeepSeek input tokens and 450 output max, ≤1 model POST/turn, staff-only exact question/response/IP/UTC audit (30-day default).
- This is **owner acceptance of a specific operating policy**, not acceptance of revised contracts DS-EC-02–05, executable tests, site/PDF Ground Truth, production, or merge.
- Independent Architecture Acceptance R2 must examine current corrected contracts and these tests at a new exact frozen Git HEAD.
- **NO Merge, DS-02 coding, paid DeepSeek calls (DS-QV-01 6/6 exhausted), Corpus Freeze, public pilot, NEW RAG edits or Saturn-Main-Site writes.**
