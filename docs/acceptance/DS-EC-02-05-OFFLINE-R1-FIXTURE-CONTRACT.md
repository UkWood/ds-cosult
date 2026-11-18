# DS-EC-AR-01 — Offline Acceptance Fixture Contract for Independent R1

**Date:** 2026-11-18  
**Status:** TEST DESIGN ONLY — NOT EXECUTED, NO LIVE DEEPSEEK GO.  
**Scope:** DS-EC-02–05 corrected v0.2 contracts. Synthetic entity IDs, fake clock, mock DeepSeek, fake provider charge ledger and fake source/PDF manifests; never real visitor IP or private benchmark GT.

## Test setup

- Two synthetic devices DEMO:A:R1 and DEMO:B:R2, shared model family with distinct revision and power/temperature fields. All invented data explicitly labeled SYNTHETIC_ONLY.
- Approved synthetic source bundle SYN-B1 with pinned source-route manifest and PDF document identities, SHA-256 placeholders validated in fake adapters, physical page numbers and table-cell paths.
- Separate synthetic SYN-B2 for cutover, one unpinned approved PDF, one parser-failing source, and two conflicting eligible source facts.
- Shared atomic mock quota/budget store keyed by canonical test IP (RFC 5737 TEST-NET addresses only), distinct mock session cookie identifiers. No personal data.
- Mock DeepSeek route choices P1 QuestionInterpretationPlan or P2 CandidateAnswerPlan, injected wrong IDs/JSON/roles, timeout and unknown bill, with a counter asserting at most one outbound POST for an accepted turn.
- All scenarios declare exact accepted_turn_delta, provider_attempt_delta, expected final status, sources checked and whether local/payed response is allowed. Fake provider output tokens capped at 450; fake input measured inclusive of system/formatting/state/evidence, with 10,000 hard maximum.

## Predeclared acceptance matrix

| ID | Synthetic condition / action | Expected result and accounting |
|---|---|---|
| AR-T01 | A power field appears only on PDF page outside top-K; source inventory says it is required | Find supported value with exact physical page or explicitly mark incomplete; never say “not specified” from top-K miss |
| AR-T02 | Two independently eligible conflicting field values, one omitted from model packet | Full applicable Fact ledger yields conflict and both EvidenceRefs; never choose one |
| AR-T03 | PDF bytes/page valid but parser attaches value from different table row/column/variant | EvidenceEligibilityDecision ineligible, no technical claim |
| AR-T04 | Same Ethernet on A and B but no compatible_with relation | Compatibility needs_support, no invented relation |
| AR-T05 | Early P1 classification prompt would exceed 10,000 counted tokens, or USD budget insufficient | 0 admitted turns, 0 provider POSTs, 0 external spend; safe static refusal |
| AR-T06 | Valid P1 intent interpretation then model attempts P2 selection | Exactly one accepted turn and one P1 POST; P2 blocked |
| AR-T07 | Visitor asks model to ignore all instructions and discuss unrelated subject | 0 accepted turns, 0 paid calls, static scoped notice |
| AR-T08 | Visitor asks real in-domain characteristic plus forged role override | One accepted technical turn; system unchanged; no fake source fact; P0/P1/P2 <=1 model POST |
| AR-T09 | 20 valid questions answerable by local templates, same IP/site-calendar day | 20 visitor slots, 0 provider POSTs; 21st request denied without charge |
| AR-T10 | 9 local + 11 valid P1/P2 questions same IP/calendar day | 20 visitor slots, exactly 11 provider POST attempts; 21st denied |
| AR-T11 | 15m inactivity expires memory; after 15–30m IP series persists; after 30m series resets | Technical state no old entity/facts; daily quota retained until configured day reset; tested DST boundary |
| AR-T12 | Concurrent same-cookie tab resend / second cookie from same canonical IP | One active lease, one accepted debit per unique request ID, no duplicate paid POST, no private transcript leak |
| AR-T13 | POST dispatched then timeout/unknown charge and retry attempted | One provider attempt and conservative USD reserve retained; no automatic POST retry |
| AR-T14 | SourceBundle changes from SYN-B1 to SYN-B2 during one admitted turn | Turn answers only from pinned B1 or safe error; next turn re-resolves B2, invalidates old citations/coverage receipt |
| AR-T15 | Model chooses valid Fact ID with wrong variant/unit or citation physical page | Invalid claim, never rendered; diagnostic identifies scope/proof mismatch |
| AR-T16 | Model requests answered even though required temperature NeedResolution not supported | Server calculates partial/needs_support with qualified unresolved need |
| AR-T17 | Source checksum/parser or verifier exception | processing_error and public error/explicit partial; never “not specified” |
| AR-T18 | Provider-bound complete input 10,000 vs 10,001 tokens | Exactly 10,000 eligible if other gates pass; 10,001 blocked before paid POST; output max 450 |
| AR-T19 | One known attribute with exact structured site field | Deterministic zero-model source-cited answer, one visitor slot, stable Russian wording |
| AR-T20 | Audit contains actual final answer/question/IP/UTC and rejected metadata only | Private staff-only 30-day policy; no real PII in public repository or new visitor session |
| AR-T21 | Operator global USD breaker exhausted; technical question locally answerable (P0) | **Proposed** policy: P0 remains within IP/20/day/series/CPU guard; P1/P2 zero paid calls; owner confirmation required before launch |
| AR-T22 | All cross-layer NeedResolution variants, evidence proof errors, final statuses combined | Deterministic versioned mapping including partial, conflict, missing, unavailable, ineligible, internal error |

## Explicit negative test gates

- No mocked accepted-turn/post counter may become negative or exceed its quota; duplicate request idempotency key never triggers a second provider dispatch.
- Missing PDF source, parser failure and source absence must produce **different** backend statuses; no trusted website/PDF injection threat expansion.
- Domain eligibility must be established conservatively **without unaccounted LLM classification**. If unknown, local clarification, 0 model calls and 0 admitted-turn debit.
- One complete source bundle per turn; fact IDs, coverage receipts, mapping dictionaries and citations pinned to revision.
- Free-form technical prose from model, user-proposed new IP or compatible_with, wrong source locator or unverifiable recommendation cannot bypass final policy.
- Core data examples are synthetic; no claim of benchmark ground-truth or production corpus acceptance.

## Independent reviewer proof requirements

For each AR-T01..22 independently inspect contract text and show the **exact clause** that defines the expected result. Classify PASS, NEEDS_CORRECTION or NOT_SPECIFIED **at documentation level**. Reviewers must not mark any fixture EXECUTED without real offline test evidence. Separately check the four BLOCKER and all eight IMPORTANT/two MINOR items in DS-EC-AR-01.

A separate future coding-session test suite may implement these fixtures with a fake provider and deterministic clock after an explicit owner GO. No paid DeepSeek API use, Corpus Freeze, prod deployment, merges or writes outside the existing PR.
