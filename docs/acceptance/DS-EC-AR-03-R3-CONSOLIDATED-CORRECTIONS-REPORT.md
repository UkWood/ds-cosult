# DS-EC-AR-03 — R3 Consolidated Architecture Corrections Report (AUTHOR SUBMISSION)

**Prepared:** 2026-11-18  
**Project:** DS-консультант — Entity-Centric Conversational RAG  
**Repository:** `UkWood/ds-cosult`  
**PR/branch:** existing OPEN/DRAFT PR #1 / `docs/ds-01c-benchmark-memory` — NO MERGE  
**R2 independently reviewed original HEAD:** `99a49a49441055a6324b0aac43a58858940e682a`  
**Independent R2 outcome:** **DS-EC-AR-03 CHANGES REQUESTED — 2 IMPORTANT (R2-CR01 and R2-CR02), no new BLOCKER**. Original 4 BLOCKER independently PASS, AR-T01–22 design check 20 PASS / 2 NEEDS CORRECTION, SEC10-T01–07 architecture desk-check 7 PASS, executable tests **0**.  
**Author correction status:** **DOCUMENTARY CHANGES SUBMITTED TO NEW INDEPENDENT R3 REVIEW; NOT AUTHOR SELF-ACCEPTANCE**.  
**R3 final frozen HEAD:** obtain from the final PR comment / owner-facing completion report after status/history/handoff commits; R3 must use one immutable commit SHA for every file read.

## 1. Changes actually performed, no scope expansion

All edits are in **existing Draft PR #1**, without new PR or merge:

| Contract/document | Old blob at R2 baseline | New blob after correction | Narrow purpose |
|---|---|---|---|
| `docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md` | `499d4fa207a99ce962c40755a5b057358f53ae94` | `d76885a18ad034d49ae3f40755863424daa079ab` | R2-CR01: §2, §6 and normative §14.3 use staged exact deterministic server response + observed transport, not unsupported "actually displayed" claim |
| `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md` | `8121406b3710974ed4c55a8bc69f56752874df60` | `a555564a8d1854930818f6b03047c22e3ac2b9e9` | R2-CR01: §8 private audit terminology aligned to DS-EC-04 §14.1.1 and §14.3 |
| `docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md` | `5d9fc47699e25973116c0b7cf354e5243c276ae1` | `545aad110b54865372766162d4984fd00ef66d47` | R2-CR01: §9/§13.4 audit; R2-CR02: §3.2, §3.4, §13.1 proof enum, navigation and malformed model mapping |
| `docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md` | `f265057d694fef662b84d1a6d18a3e10d58afece` | `32c7198cdd27c5a2423bc91f82b64b475eae2a65` | R2-CR02: minimal §8.3.1 canonical registry alignment; `DocumentReference` independent from technical `VerifiedClaim` |
| `docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md` | `48729d392a139f0e31d14b33806dff57f9a61e51` | `7d1ecdcd24e8bf5d87250fe2d360a933345f535a` | R2-CR01/02: AR-T20/22 and R1-F06/F07 expected outcomes made unambiguous; existing 22 AR-T cases retained |

All source/blob values above were **re-fetched and checked after GitHub writes**. They identify actual author edits, not hypothetical modifications. Earlier original independent R1/R2 reports, prior owner decisions DS-SEC-07/08/09/**10**, and all frozen source/history evidence remain preserved.

## 2. R2-CR01 — durable response versus truthful delivery

**R2 finding:** DS-EC-04 §14.3 said `actually displayed` despite §14.1.1 expressly prohibiting inference of visual browser rendering from server-side activity.

**Corrected normative contract:** DS-EC-04 §14.3 states:
- `staged_answer_text`: exact deterministic server-created final answer **intended for emission**;
- `server_response_exact_bytes` stored encrypted/durably, plus `response_bytes_sha256` integrity hash;
- `response_transport_attempted_at_utc` as nullable server-side attempt time;
- `delivery_status=not_attempted|transport_attempted|transport_accepted|transport_failed|transport_unknown` based only on server transport evidence;
- separately optional `client_ack_status=not_supported|not_received|received`, **never proof of visual display or human reading**;
- `OUTPUT_STAGED` proves **durable preparation**, not delivery; HTTP 2xx and client acknowledgement do not prove on-screen reading;
- idempotent replay of **identical staged bytes only to the same still-valid original session**, no extra accepted-turn debit, **no extra model POST** if original transport failed/unknown;
- store exact admitted question, IP, UTC and source/result correlation in restricted 30-day private audit; a missing final answer gets an error/outcome record, not false delivered status.

Earlier misleading phrases in DS-EC-04 §§2/6 and DS-EC-03 §8 and DS-EC-05 §9 were replaced by correct semantics, not merely superseded at the bottom. The already-accepted §14.1.1 network/response FSM and crash/dispatch accounting was **not rewritten**.

### R2-CR01 acceptance criteria self-check (DOCUMENTS ONLY)

| Criterion | Contract location / intended evidence |
|---|---|
| A01 No speculative `actually displayed` in active normative audit | DS-EC-04 §14.3; DS-EC-03 §8; DS-EC-05 §9 |
| A02 `OUTPUT_STAGED` is not delivered | DS-EC-04 §14.1.1 and §14.3 |
| A03 `transport_accepted` is not proof of screen display | DS-EC-04 §14.3 |
| A04 Client ACK separately typed, not visual-reading proof | DS-EC-04 §14.1.1 and §14.3 |
| A05 Exact bytes and SHA integrity retained | DS-EC-04 §14.3; DS-EC-05 §13.4 |
| A06 Replay original still-valid session only | DS-EC-04 §14.3 |
| A07 Unknown/failed delivery triggers no second paid POST | DS-EC-04 §14.3; DS-EC-05 §13.4 |
| A08 AR-T20 and R1-F06 precise outcomes | Offline R1 fixture contract |

**Author status:** `CORRECTION PROPOSED — INDEPENDENT R3 MUST VERIFY`, not an independent PASS.

## 3. R2-CR02 — canonical proof state and separate document navigation

**R2 finding:** DS-EC-05 §13.1 placed `source_reference_only` (document navigation object) and `invalid_model_plan` (reason code) in the `VerifiedClaim.proof_state` column, neither belonging to its seven-member enum. Earlier §3.2 also allowed legacy `claim_kind=source_reference_only`.

**Corrected normative contract:**
- `VerifiedClaim.claim_kind` only `structured_fact|structured_relation`, both based on precise non-conflicting applicable source evidence. `DocumentReference` is a **separate canonical type** with `document_reference_id` citation and `ReasonCode=document_reference_only`, never a backdoor for equipment technical claims.
- Accepted `VerifiedAnswerResult.verified_claims[]` contains only technical `eligible` records with `FactPublicationDecision=established_fact`. Candidate diagnostics may use exactly `eligible|inapplicable|unsupported|conflict|not_indexed|source_error|internal_error` but do not produce accepted VerifiedClaims for non-eligible candidates.
- **No candidate evaluated = explicit “—”**, not a made-up proof state.
- Malformed plan/wrong ID/unknown field has **`ReasonCode=invalid_model_plan` only**; model-derived accepted VerifiedClaims **zero**; any partial answer relies exclusively on independent pre-verified facts, no second paid API POST.
- A navigation-only set of fully resolved needs can be `answered`; when any required technical need remains unresolved, a document URL cannot make the whole result `answered`.
- Contradictory source facts can produce cited **`ConflictPosition[]`** (attributed source statements), **zero truth-bearing VerifiedClaims** for the disputed need.
- DS-EC-05 §13.1 is now explicitly a **five-column typed table**: NeedResolution/processing condition, **candidate proof state** (only enum or —), accepted typed object, FinalStatus, ReasonCode. DS-EC-02 §8.3.1 canonical schema registry repeats the same boundary.
- `VerifiedAnswerResult` includes a separate `document_reference_citation_bindings[]` to avoid evidence-to-claim confusion.

### R2-CR02 acceptance criteria self-check (DOCUMENTS ONLY)

| Criterion | Contract location / intended evidence |
|---|---|
| B01 Enum-only candidate proof state or explicit “—” | DS-EC-05 §3.2 / §13.1; DS-EC-02 §8.3.1 |
| B02 No VerifiedClaim when no technical claim exists | DS-EC-05 §13.1 |
| B03 DocumentReference distinct from VerifiedClaim | DS-EC-05 §§3.2–3.4 / §13.1 |
| B04 invalid_model_plan is ReasonCode, not proof state | DS-EC-05 §13.1 and DS-EC-02 registry |
| B05 Cannot mark all needs answered with unsatisfied technical need | DS-EC-05 §13.1 multiple-need rule |
| B06 ConflictPosition is attribution, not established claim | DS-EC-05 §13.1 and DS-EC-02 §8.2.1 |
| B07 Canonical names and schema versions retained | DS-EC-02 §8.3.1; DS-EC-05 §3.4 |
| B08 R1-F07 / AR-T22 exhaustive safe mapping | Offline R1 fixture contract |
| B09 Independent implementations can make same typed choice | Explicit enum/object/reason/absence mapping in DS-EC-05 §13.1 |

**Author status:** `CORRECTION PROPOSED — INDEPENDENT R3 MUST VERIFY`, not an independent PASS.

## 4. Regression invariants inspected as architecture text only

- **R1-CR01**: `SourceAssertionProof` and `ConflictAssessment` remain separate from `FactPublicationDecision` and `ConflictPosition`; no conflicting claim asserted as established fact.
- **R1-CR02**: `provider_attempt_slot_reserved` is not actual POST; `provider_post_dispatch_recorded` separate before network, unknown billed attempts held and never automatically retried; valid P1 unsupported→clarification, no P2 retry.
- **R1-CR05**: DS-SEC-10 owner approved paid DeepSeek USD breaker: P1/P2 blocked when exhausted, verified local P0 remains under IP/20/day/series/CPU/source/audit, P0 consumes one question and no paid POST. No budget amounts invented.
- **Original CR-B01/B03/I03/I04**: SourceCoverageReceipt scope/completeness, universal ProviderDispatchGuard/10,000 total input/450 output and <=1 POST, source bundle version pin/migration, canonical typed units and directional relations retained.
- User direct Goal Hijacking cannot alter backend role, source Fact/Relation, policy or spending gate; site and approved PDFs remain owner-declared trusted/injection-free.
- **AR-T20/22, R1-F06/07** have explicit design expected statuses; 22 AR-T design cases and seven DS-SEC-10 design cases persist; **0 executable/mock/API tests performed**.

**No code, no physical source verification and no independent architecture PASS** was produced by this author check.

## 5. Remaining gates and governance

R2 corrections are limited to these two IMPORTANT issues. Exact source PDF/index readiness (earlier owner WSL report: 3/12 PDF byte pins, 0 expert-approved benchmark GT, P4/P5 review not complete), operator paid USD thresholds, IANA reset timezone, verified service contact details, trusted proxy topology, privacy/legal notices and actual audit retention control remain **separate** runtime/launch tasks. No plan to auto-merge or start DS-02 implementation.

**Next:** send R3 reviewer in another ChatGPT project conversation. It must freeze final PR HEAD, read actual source blobs, independently decide **PASS or CHANGES REQUESTED** on **architecture documents only** and check for regressions/new conflicts, without trusting this author report.

**DO NOT MERGE / CODE / CALL PAID DEEPSEEK / DEPLOY / CORPUS FREEZE / WRITE NEW RAG OR SATURN SITE.** DS-QV-01 authorized paid 6/6 already consumed.
