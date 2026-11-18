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
| AR-T22 | R3-CR01: verify canonical aggregation of mixed navigation/technical/conflict/missing/source-error/malformed-P2 plans; all 12 R3-F01..12 synthetic cases | **Exactly one** `FinalStatus` and top-level canonical `ReasonCode` per case by DS-EC-05 §13.1.1; per-need reasons retained by `need_id` in NeedResolution/diagnostics; typed VerifiedClaim vs DocumentReference vs attributed ConflictPosition; exact `unresolved_need_ids[]`, citation targets and **no second paid POST**. Expected typed values for each subcase specified in R3-F matrix below. |

## Additional R1 synthetic desk-check fixtures (NOT EXECUTED)

| Case | Fixture | Required answer, counters and invariant |
|---|---|---|
| R1-F01 / AR-T02 | Approved source A says 24 В, source B says 12 В same variant, one omitted from EvidencePacket | Two proven source assertions and ConflictAssessment=applicable_conflict; publication_role=attributed_conflict_position each; zero established VerifiedClaims for disputed voltage; two cited ConflictPositions; final needs_support |
| R1-F02 / AR-T03 | One conflicting PDF assertion has wrong table row despite correct SHA/page | Wrong-row assertion is unproven; cannot be an attributed conflict position or adopted value |
| R1-F03 / AR-T13 | Reserved paid slot, crash BEFORE dispatch-intent, proven no network send | admitted=1; provider attempt recorded=0; no automatic retry |
| R1-F04 / AR-T13 | Dispatch-intent durable then crash BEFORE proven socket send | admitted=1; dispatch-risk attempt=1; USD hold, outcome unknown; no automatic retry or false claim remote received |
| R1-F05 / P1 valid unsupported | Paid P1 returns interpretation_status=unsupported after admission | admitted=1, one dispatch-risk attempt, NeedResolution=ambiguous_question, reason=interpretation_unsupported, final clarification, zero additional P2 |
| R1-F06 / AR-T20 | `OUTPUT_STAGED` exact response bytes/hash, server HTTP failed/unknown or transport accepted, optional client ACK | Durable intended answer + question/IP/UTC; independent transport timestamp/status + ACK. No claim of human-visible display from any transport/ACK state. Same still-active session may replay exact response bytes, 0 second provider POST / visitor debit; other cookie denied. |
| R1-F07 / AR-T22 | Malformed P2 and one or more independently validated navigation/technical needs; source error/conflict/ambiguity combinations | **Normative R3-F03..F10 cases below:** one supported navigation plus source_unavailable => `partial/source_unavailable`; with ambiguous_variant => `partial/ambiguous_variant`; with true conflict => `partial/applicable_source_conflict`; malformed P2 with no independent result => `needs_support/invalid_model_plan`; with independent verified Fact => `partial/invalid_model_plan`. All per-need diagnostics and citations retained; model plan contributes 0 accepted claims, no second paid POST. |
| R1-F08 / AR-T21 | Global paid USD breaker triggered; source-proven local P0 fact available | **DS-SEC-10 OPTION A APPROVED:** admitted +1 question, 0 provider attempts/dispatch/reservation and 0 paid model cost; keep source/citation and IP/day/series/CPU/audit checks |
| R1-F10 / AR-T21 | Same budget outage, P1/P2 required; no trustworthy P0 | static budget/support notice, 0 accepted-turn debit, 0 provider attempts/dispatch and 0 paid cost |
| R1-F11 / AR-T21 | Global paid budget exhausted; valid P0 fact but IP/day=20, Q11 consecutive, or CPU breaker | denied by non-monetary limit; 0 new accepted-turn debit and no provider calls |
| R1-F12 / AR-T21 | Cached LLM prose deceptively labeled local P0 | reject P0 provenance; no paid fallback under breaker and no invented fact |
| R1-F09 / AR-T09/10 | Two legal series of up to ten questions with 30m idle reset | Correct 20/day question slots, 11 recorded paid dispatches in mixed case, no 11th rapid-series bypass |


## R3-CR01 — deterministic mixed QuestionNeeds fixtures R3-F01..R3-F12 (DESIGNED, NOT EXECUTED)

This section is **normatively tied to the single mixed-need reducer in DS-EC-05 §13.1.1**, without a second status machine. All values/identifiers are synthetic (SYN-B1, DEMO devices) and never real Saturn device facts. All independent source assertions, bindings and applicability checks are assumed proven **only where explicitly stated**. Required needs are ordered `N1,N2,N3` and `unresolved_need_ids[]` must retain this order. **No additional API POST is permitted for a malformed model plan, clarification or failed transport.**

**Notation:** `R(N)=status / canonical per-need reason / candidate proof_state`; `—` means **no candidate proof_state and no accepted VerifiedClaim**, not an extra enum. For the intentionally malformed P2 plan that stops evaluation before NeedResolution, `R(N)=— / invalid_model_plan / —` means **no invented NeedResolution.status**; the existing sanitized `VerifiedAnswerResult.diagnostics[]` binds the `need_id` to canonical `ReasonCode=invalid_model_plan` and `unresolved_need_ids[]` includes it. `VC(N)` = established, eligible technical VerifiedClaim; `DR(N)` = approved metadata-only DocumentReference; `CP(N:A,B)` = two source-attributed ConflictPositions (never established Fact). `cit` binds each published object to **exactly one** verified `claim_id|document_reference_id|position_id`. For local P0 cases `model POST delta=0`; for P1/P2 already dispatched, delta=1 on the original request, **0 additional POST** for retry or rendering.

| Case | Frozen required QuestionNeeds, NeedResolution / reason / diagnostic `proof_state` | Published typed objects and CitationBinding targets | Exact FinalStatus / top ReasonCode / unresolved_need_ids[] / model POST |
|---|---|---|---|
| **R3-F01** navigation only | N1 navigation: `supported / document_reference_only / —` | DR(N1) with 1 `document_reference_id` citation; **0 VC** | `answered / document_reference_only / [] / 0 (P0)` |
| **R3-F02** navigation + supported technical Fact | N1 navigation: `supported/document_reference_only/—`; N2 technical: `supported/fully_supported/eligible` | DR(N1) + VC(N2), **2 independent citations** (`document_reference_id`, `claim_id`) | `answered / fully_supported / [] / 0 (P0)` |
| **R3-F03** navigation + known unindexed property | N1: `supported/document_reference_only/—`; N2: `scope_not_indexed/source_scope_not_indexed/—` (partial_index receipt, no evaluated candidate) | DR(N1) with `document_reference_id` citation; **no VC(N2)** | **`partial / source_scope_not_indexed / [N2] / 0 (P0)`** |
| **R3-F04** independent navigation + source not readable | N1: `supported/document_reference_only/—`; N2: `source_unavailable/source_unavailable/—` (N1 source/variant independently valid) | DR(N1) + its document citation only; N2 has no citation | **`partial / source_unavailable / [N2] / 0 (P0)`**; explicit error for N2, not negative fact |
| **R3-F05** variant-independent navigation + ambiguous target variant | N1: `supported/document_reference_only/—`; N2: `ambiguous_entity_or_variant/ambiguous_variant/—` (N1 not dependent on variant) | DR(N1) with its citation; no VC(N2) | **`partial / ambiguous_variant / [N2] / 0 (P0)`**; ask variant for N2 |
| **R3-F06** navigation + opposing proven source positions | N1: `supported/document_reference_only/—`; N2: `conflict/applicable_source_conflict/conflict` for rejected technical truth candidate | DR(N1) and **CP(N2:A,B)**, 3 independent citations (1 `document_reference_id`, 2 distinct `position_id`); **0 VC for N2** | **`partial / applicable_source_conflict / [N2] / 0 (P0)`**; conflict positions do not satisfy N2 |
| **R3-F07** invalid P2, no independently accepted evidence | N1 technical: **`—/invalid_model_plan/—`** pre-NeedResolution failed model candidate; 0 validated technical facts | **No VC, DR, CP or citations** | `needs_support / invalid_model_plan / [N1] / 1 initial P2 POST; 0 additional` |
| **R3-F08** independent Fact + invalid P2 for other need | N1 technical: `supported/fully_supported/eligible` from **independent local verifier**, N2 technical: `—/invalid_model_plan/—` pre-NeedResolution failed P2 | VC(N1) with 1 `claim_id` citation; 0 model-derived VC(N2) | `partial / invalid_model_plan / [N2] / 1 initial P2 POST; 0 additional` |
| **R3-F09** independent Fact + failure of other source | N1 technical: `supported/fully_supported/eligible` independent; N2 technical: `source_unavailable/source_unavailable/—` | VC(N1) + 1 `claim_id` citation; no object or citation for N2 | **`partial / source_unavailable / [N2] / 0 (P0)`**; N2 error clearly stated |
| **R3-F10** zero satisfied, 3 distinct unresolved types | N1: `conflict/applicable_source_conflict/conflict`; N2: `source_unavailable/source_unavailable/—`; N3: `ambiguous_entity_or_variant/ambiguous_variant/—` | **No public VC, DR, CP or citation in this fail-closed error-mode fixture** (source conflict detail retained in per-need diagnostics) | **`error / source_unavailable / [N1,N2,N3] / 0 (P0)`**; error outranks ambiguity outranks conflict |
| **R3-F11** dependent technical need with failed prerequisite | N1 prerequisite: `source_unavailable/source_unavailable/—`; N2 technical candidate: `supported` with private candidate `proof_state=eligible`, but **publication revoked** due dependency on N1; unresolved N2 carries inherited `source_unavailable` | **0 public VC, DR, CP and 0 citations**, even if N2 had a syntactically valid candidate | `error / source_unavailable / [N1,N2] / 0 (P0)`; dependent claimed value suppressed |
| **R3-F12** valid paid P1 unsupported | N1: `ambiguous_question/interpretation_unsupported/—` after a valid admitted P1 plan reporting unsupported intent | No published technical or navigation object or citations | `clarification / interpretation_unsupported / [N1] / 1 recorded P1 POST; 0 P2`; accepted turn not refunded |

**Required per-case serialization assertions:** `VerifiedAnswerResult.reason_code` is exactly the one named in the final column; each unresolved N has exactly one canonical per-need reason via DS-EC-02 `NeedResolution.diagnostics_code` where the status exists, or the **existing** sanitized `diagnostics[]` for malformed pre-NeedResolution P2. All other unresolved per-need codes remain visible/auditable even when the top-level reason selects another: R3-F10 must preserve **all 3 reasons** in order `N1:applicable_source_conflict; N2:source_unavailable; N3:ambiguous_variant`. R3-F11 must preserve **N1:source_unavailable; N2:source_unavailable** and dependency evidence. Never infer browser visual display from staged/HTTP response.

**Additional reason-priority regression:** if no needs are satisfied and `source_integrity_error` + `source_unavailable` + `applicable_source_conflict` coexist, expect `error / source_integrity_error` and all 3 individual codes preserved; if an independent VC is also satisfied, expect `partial / source_integrity_error` (only when dependency isolation safe). If a valid P1 unsupported is the sole unresolved need, expect exactly `clarification / interpretation_unsupported`. A budget-denied P1/P2 **pre-admission** follows owner DS-SEC-10 static service path, not this admitted-turn reducer.

**All 12 R3-F cases, all 22 AR-T cases and SEC10-T01..07 are PROSPECTIVE DESIGN FIXTURES ONLY. NONE WERE EXECUTED.** The matrix is a normative expected-behavior specification for later coding/test GO, not experimental evidence.

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
