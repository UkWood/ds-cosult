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
| AR-T09 | 20 valid P0 locally answered questions on same IP/operator-calendar day, **in two separate 10-question series with ≥30m inactivity between series** (15m memory expiry expected) | 20 accepted visitor slots, 0 paid POSTs; question 21 denied without charge; no 11th rapid-series question admitted |
| AR-T10 | 9 local + 11 paid P1/P2 across **two legal series**: series 1 = 9 local + 1 paid, wait ≥30m, series 2 = 10 paid; all within same operator calendar day | 20 accepted visitor slots and 11 recorded dispatch-intent POST attempts; question 21 denied; cooldown/series rules obeyed |
| AR-T11 | 15m inactivity expires memory; after 15–30m IP series persists; after 30m series resets | Technical state no old entity/facts; daily quota retained until configured day reset; tested DST boundary |
| AR-T12 | Concurrent same-cookie tab resend / second cookie from same canonical IP | One active lease, one accepted debit per unique request ID, no duplicate paid POST, no private transcript leak |
| AR-T13 | P1 reserves call-slot then crashes **(a) before dispatch-intent**, **(b) after durable dispatch-intent before confirmed send**, **(c) during network timeout** | (a) 1 admitted question, 1 reserved slot, **0 recorded provider POST attempts** and no automatic retry; (b)/(c) 1 conservative dispatch-risk attempt, reserve retained, unknown outcome, no retry |
| AR-T14 | SourceBundle changes from SYN-B1 to SYN-B2 during one admitted turn | Turn answers only from pinned B1 or safe error; next turn re-resolves B2, invalidates old citations/coverage receipt |
| AR-T15 | Model chooses valid Fact ID with wrong variant/unit or citation physical page | Invalid claim, never rendered; diagnostic identifies scope/proof mismatch |
| AR-T16 | Model requests answered even though required temperature NeedResolution not supported | Server calculates partial/needs_support with qualified unresolved need |
| AR-T17 | Source checksum/parser or verifier exception | processing_error and public error/explicit partial; never “not specified” |
| AR-T18 | Provider-bound complete input 10,000 vs 10,001 tokens | Exactly 10,000 eligible if other gates pass; 10,001 blocked before paid POST; output max 450 |
| AR-T19 | One known attribute with exact structured site field | Deterministic zero-model source-cited answer, one visitor slot, stable Russian wording |
| AR-T20 | R2-CR01: stage exact intended server bytes/hash with question/IP/UTC; fail HTTP send or receive HTTP 2xx; optional client ACK; original-session retry after failed/unknown transport | Audit stores `staged_answer_text`, protected `server_response_exact_bytes`, `response_bytes_sha256`, nullable `response_transport_attempted_at_utc`, `delivery_status` and optional separate `client_ack_status`. No inference of browser display/reading even from HTTP success/ACK. Exact bytes may replay only to same live anonymous session, 0 extra visitor debit and **no second paid POST**. |
| AR-T21 | Operator global **DeepSeek-paid** USD breaker exhausted; source-verified, safe P0 locally answerable | **OWNER APPROVED DS-SEC-10:** P0 admitted with all IP/session/20/day/series/cooldown/CPU/audit checks, +1 accepted question, +0 provider attempt/dispatch and +$0 model cost; P1/P2 blocked before admission |
| AR-T22 | R2-CR02: source conflict, malformed model JSON/invalid ID, metadata-only navigation, valid P1 unsupported, source error, mixed partial | `proof_state` diagnostic is **only** `eligible|inapplicable|unsupported|conflict|not_indexed|source_error|internal_error` or **absent**; `source_reference_only` and `invalid_model_plan` are **never proof_state**. Navigation emits `DocumentReference` (not technical VerifiedClaim) with `ReasonCode=document_reference_only`, `answered` only if all needs are satisfied navigation. Invalid plan emits `ReasonCode=invalid_model_plan`, no model-derived VerifiedClaim, no retry. ConflictPosition is attributed-only, not established truth. |

## Additional R1 synthetic desk-check fixtures (NOT EXECUTED)

| Case | Fixture | Required answer, counters and invariant |
|---|---|---|
| R1-F01 / AR-T02 | Approved source A says 24 В, source B says 12 В same variant, one omitted from EvidencePacket | Two proven source assertions and ConflictAssessment=applicable_conflict; publication_role=attributed_conflict_position each; zero established VerifiedClaims for disputed voltage; two cited ConflictPositions; final needs_support |
| R1-F02 / AR-T03 | One conflicting PDF assertion has wrong table row despite correct SHA/page | Wrong-row assertion is unproven; cannot be an attributed conflict position or adopted value |
| R1-F03 / AR-T13 | Reserved paid slot, crash BEFORE dispatch-intent, proven no network send | admitted=1; provider attempt recorded=0; no automatic retry |
| R1-F04 / AR-T13 | Dispatch-intent durable then crash BEFORE proven socket send | admitted=1; dispatch-risk attempt=1; USD hold, outcome unknown; no automatic retry or false claim remote received |
| R1-F05 / P1 valid unsupported | Paid P1 returns interpretation_status=unsupported after admission | admitted=1, one dispatch-risk attempt, NeedResolution=ambiguous_question, reason=interpretation_unsupported, final clarification, zero additional P2 |
| R1-F06 / AR-T20 | `OUTPUT_STAGED` exact response bytes/hash, server HTTP failed/unknown or transport accepted, optional client ACK | Durable intended answer + question/IP/UTC; independent transport timestamp/status + ACK. No claim of human-visible display from any transport/ACK state. Same still-active session may replay exact response bytes, 0 second provider POST / visitor debit; other cookie denied. |
| R1-F07 / AR-T22 | Malformed model plan, valid document navigation with unrelated technical need, source-error partial | `invalid_model_plan` **ReasonCode only**, no invalid proof_state or newly accepted VerifiedClaim; `DocumentReference` only satisfies navigation needs, with bound document citation and `ReasonCode=document_reference_only`. Technical need remains unresolved, so cannot be fully `answered`. Partial only with independently verified claims; source internal error remains explicit. |
| R1-F08 / AR-T21 | Global paid USD breaker triggered; source-proven local P0 fact available | **DS-SEC-10 OPTION A APPROVED:** admitted +1 question, 0 provider attempts/dispatch/reservation and 0 paid model cost; keep source/citation and IP/day/series/CPU/audit checks |
| R1-F10 / AR-T21 | Same budget outage, P1/P2 required; no trustworthy P0 | static budget/support notice, 0 accepted-turn debit, 0 provider attempts/dispatch and 0 paid cost |
| R1-F11 / AR-T21 | Global paid budget exhausted; valid P0 fact but IP/day=20, Q11 consecutive, or CPU breaker | denied by non-monetary limit; 0 new accepted-turn debit and no provider calls |
| R1-F12 / AR-T21 | Cached LLM prose deceptively labeled local P0 | reject P0 provenance; no paid fallback under breaker and no invented fact |
| R1-F09 / AR-T09/10 | Two legal series of up to ten questions with 30m idle reset | Correct 20/day question slots, 11 recorded paid dispatches in mixed case, no 11th rapid-series bypass |

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
