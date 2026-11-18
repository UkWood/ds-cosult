# DS-EC-AR-02 — R2 Consolidated Corrections and Owner Decision Report

**Prepared:** 2026-11-18  
**Project/repository:** DS-консультант / `UkWood/ds-cosult`  
**Existing branch/PR:** `docs/ds-01c-benchmark-memory` / Draft PR #1, NO MERGE  
**Independent R1 review baseline HEAD:** `7625b27c30d9dd558dffb5f1069b6b4a4d8e055e`  
**Author's pre-DS-SEC-10 observed HEAD:** `63616d3850ae46969a5bb734840778c69352e5b4` (already contained R1-CR01/02/03/04/06 changes)  
**Final R2 reviewed-head ref:** **MUST be taken from the final owner-facing handoff / PR metadata after all documentation commits**, frozen by full SHA before the new independent R2 session reads anything. This report is not a self-acceptance.  
**R1 verdict:** **CHANGES REQUESTED** — 2 of original 4 BLOCKER OPEN, 3 of 8 IMPORTANT OPEN + 3 conditionally disposed, 2 of 2 MINOR OPEN; design desk-check AR-T01–22: 17 PASS / 5 NEEDS CORRECTION / **0 EXECUTED**.  
**Author's present disposition:** **CORRECTIONS SUBMITTED FOR INDEPENDENT R2** — no PASS assumed.

## 1. Provenance and change ownership

The owner-provided independent report is `DS-EC-AR-02 — Independent Architecture Acceptance Review R1` (938 lines; original supplied in project conversation). Its concise independently prepared finding receipt is `docs/acceptance/DS-EC-AR-02-INDEPENDENT-R1-FINDINGS-RECEIPT.md`, which does **not** replace source evidence or the original user attachment.

At the moment this Architecture Session A received the explicit owner approval of R1-CR05 (global-paid-budget option A), **PR #1 HEAD was already `63616d3850ae46969a5bb734840778c69352e5b4`** and already included normative author corrections to R1-CR01/02/03/04/06 in DS-EC-02–05 and R1 offline fixture amendments. These changes were *observed and inspected*, not claimed as newly written by the current owner-decision operation. The new work in this operation is:
- explicit owner decision `DS-SEC-10` approving protected zero-provider P0 despite exhausted DeepSeek-paid USD budget;
- reconciliation of the paid/global budget semantics through related owner decisions, entity-centric reference, abuse-control proposals, DS-EC-03/04/05 and the R1 fixture matrix;
- correction of DS-EC-04 contract title to v0.2;
- this R2 author report and an independent new-session handoff.

**Never replace the independent R1 verdict with the author's own assertions.** The R2 reviewer must obtain the exact corrected Git blob bytes by frozen commit and independently check every referenced condition.

## 2. Consolidated six-item R1 correction trace — submit for R2

| R1 item | Source clauses after corrections | Proposed author disposition, NOT R2 acceptance |
|---|---|---|
| **R1-CR01 / BLOCKER** Source assertion fidelity versus conflict publication | `DS-EC-02 §8.2.1`: separate `SourceAssertionProof`, `ConflictAssessment`, `FactPublicationDecision`, `ConflictPosition`. `DS-EC-05 §7, §13.1/13.2`: two source-proven contradictory values may appear *only* as attributed conflict positions with citations, never as independently established VerifiedClaims. `AR-T02`, `R1-F01/F02`, `EC5-06/40`. | **CLAIMED ADDRESSED in preexisting amendments**. Check eligibility flags, negative/path examples and source-to-conflict rendering rigor. |
| **R1-CR02 / BLOCKER** Reserved slot versus actual network dispatch, P1 `unsupported` | `DS-EC-03 §10.2/§10.2.1, §10.3.1`, `DS-EC-04 §14.1/§14.1.1`, `DS-EC-05 §13.1/§13.3`: `provider_attempt_slot_reserved` (call authorization) separate from durable `provider_post_dispatch_recorded` (conservative dispatch risk count), `provider_outcome_unknown`; no automatic retry. Valid P1 `interpretation_status=unsupported` maps to `NeedResolution=ambiguous_question`, `reason=interpretation_unsupported`, `FinalStatus=clarification`, with already-counted accepted turn and recorded actual/at-risk POST only when dispatch intent was committed; no second P2. `AR-T13/T22`, R1-F03/04/05. | **CLAIMED ADDRESSED in preexisting amendments**. Independently inspect pre-intent/no-send crash, post-intent ambiguous send and no double charge. |
| **R1-CR03 / IMPORTANT** Exact response staging versus transport delivery | `DS-EC-04 §14.1.1` and `DS-EC-05 §13.4`: `staged_answer_text`, exact `server_response_exact_bytes` or encrypted bytes/hash, `response_transport_attempted_at_utc`, `delivery_status`, optional `client_ack_status`; server cannot prove browser visual display. Idempotent retry only to original active anonymous session. `AR-T20`, R1-F06, EC5-38. | **CLAIMED ADDRESSED in preexisting amendments**. Verify no lower-precedence prose falsely promises actual displayed answer. |
| **R1-CR04 / IMPORTANT** Complete status/reason and metadata navigation | `DS-EC-02 §8.3/§8.3.1` canonical registry and enum; `DS-EC-03 §10.3.1`, `DS-EC-05 §13.1` NeedResolution→publication role→final status/reason; `invalid_model_plan`, source-attributed conflict, P1 unsupported, `DocumentReference` metadata-only verified navigation (no technical value implied), partial/error handling. `AR-T22`, R1-F07. | **CLAIMED ADDRESSED in preexisting amendments**. Review cross-product status table, invalid-plan fallback, no technical answered with unsatisfied needs. |
| **R1-CR05 / IMPORTANT — OWNER DECISION** Paid global USD breaker versus safe local P0 | **OWNER NOW APPROVED** `docs/decisions/DS-SEC-10-OWNER-APPROVED-PAID-BUDGET-BREAKER-LOCAL-P0.md`: DeepSeek-paid USD exhaustion => P1/P2 blocked before turn debit, but verified zero-provider P0 remains eligible under IP/session/20-day/series/cooldown/CPU/concurrency/source-citation/private-audit guards; one accepted turn for P0, zero paid POST and cost. Normatively aligned `DS-SEC-07/09`, `DS-EC-01/03/04/05`, `DS-SEC-04/05/06` and `AR-T21/R1-F08/F10–12`. | **OWNER DECISION CLOSED; R2 ARCHITECTURE CONSISTENCY STILL TO BE VERIFIED.** No new operator USD amount is implied. |
| **R1-CR06 / MINOR** Labels, schema registry and legal series fixtures | `DS-EC-02 §8.3.1`, DS-EC-03, DS-EC-05 §13.1, normative DS-EC-05 13.1–13.5 (instead of misnumbered 12.1–12.5); DS-EC-04 current title **v0.2**, DS-SEC-08 20-billable historical note marked **SUPERSEDED BY DS-SEC-09**; `AR-T09/T10` each specify **two legal question series** with ≥30m idle reset and 20 accepted per operator-day; no 11th in uninterrupted series. | **CLAIMED ADDRESSED**, exact schema version/enum labels and all cross-refs require R2 review. |

## 3. Owner policy DS-SEC-10 (new normative source) — scope of approval

The owner's explicit instruction approving **Option A** is authoritative for the budget-breaker route selection, not an authorization to bypass any other guard:

- `P0`: **fully local** source-eligible verified Fact/Relation/ConflictPosition, valid scope/coverage/citations, deterministic final renderer, no model or paid tool, bounded CPU; admitted exactly once (+1 accepted visitor turn), no provider attempt reservation/dispatch, +0 DeepSeek model USD. Source-qualified partial allowed only when safe and transparent.
- `P1/P2`: under exhausted or unavailable global paid provider USD reserve, **deny before user-turn admission** (+0 accepted turns, +0 call-slot, +0 dispatch intent/POST). Never use a paid preliminary classifier.
- `P0` remains blocked if per-IP 20/day, continuous series Q11, cooldown, same-IP active other session, source integrity, audit storage, CPU, concurrency or any separate non-monetary safety breaker forbids it.
- Cached plain LLM prose is **not** a P0 source; user-entered fake source claims and system-role overrides cannot reclassify a request as P0.
- An already reserved/in-flight paid request preserves its original crash/unknown-provider-outcome rules after the breaker trips; no charge refund or automatic second call.
- Operator USD/day/month figures, organization IANA calendar timezone, proxy, support contacts and privacy controls are still **NOT CONFIGURED**; owner has approved behavior, not monetary numbers or production.

## 4. Required independent R2 review gates

**Mandatory independent source read-back at exact frozen HEAD**:
1. `R1-CR01..06` each evaluated with exact normative clauses and defects found, not by a keyword presence check.
2. All original `DS-EC-AR-01` 4 BLOCKER / 8 IMPORTANT / 2 MINOR dispositions remain intact or improved, particularly source coverage B01, universal ProviderDispatchGuard B03, identity I03, dictionary I04.
3. `AR-T01..22` design desk-check; previously R1 flagged **T02/T13/T20/T21/T22**. The revised R1 fixtures include paid budget scenarios R1-F08/F10–F12, and owner DS-SEC-10 proposes SEC10-T01..T07. **No scenario has been executed.**
4. Test contradictions in historical v0.1 text versus normative newer v0.2/v0.3 clauses and owner DS-SEC-07/08/09/10.
5. Check whether R1-CR02's **reserved attempt** and **dispatch-intent** distinction consistently accounts for *provider_post_attempts_ip_day* and unknown transmission, without falsely asserting bytes reached the provider or silently retrying.
6. Check whether user-accepted local P0 under budget outage is both **source-eligible** and subject to all independent IP/quota/series/CPU/log guards; no cached free-form model text used as evidence.
7. Independently verify exact proof path for conflict display: true/source-proven assertion vs publication as technical truth; two citations may be shown as conflicting claims without a fabricated winner.
8. Verify exact response bytes/delivery audit claims: no false claim of human-visible display from server staging/transport success.
9. Inspect source revisions, append-only owner decisions, and no fabricated real corpus readiness; site and approved PDF are owner-declared trusted/injection-free; visitor is threat boundary.

**Decision criterion:** independent R2 returns **PASS** only for a complete, internally consistent **architecture document baseline**; any material unclosed issue => **CHANGES REQUESTED with one consolidated finding list**. Neither result establishes tested backend, frozen corpus, deployment, production or allowable new paid DeepSeek calls.

## 5. Status and governance

This is an **author report**, not an independent acceptance. Its purpose is a falsifiable trace from reviewer findings to immutable corrected GitHub source. R2 session must read the files and may identify new inconsistencies. Retain the original user-provided DS-EC-AR-02 report, its GitHub findings receipt and the untouched original DS-EC-AR-01 review as historical acceptance artifacts.

**NO MERGE, DS-02 CODING, PAID API, PRODUCTION, CORPUS FREEZE OR WRITES TO NEW RAG / TRUSTED SATURN SITE.** Prior DS-QV-01 allowed DeepSeek requests are exhausted **6/6**. Source custody remains incomplete according to earlier owner WSL reports (3/12 PDF byte pins, 0 expert-approved benchmark GT, P4/P5 factual review open).
