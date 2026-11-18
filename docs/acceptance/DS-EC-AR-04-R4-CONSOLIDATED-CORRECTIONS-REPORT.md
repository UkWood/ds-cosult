# DS-EC-AR-04 — R4 Consolidated Corrections Report (Architecture Session A, Author)

**Date:** 2026-11-18  
**Project:** DS-консультант — Entity-Centric Conversational RAG, separate from NEW RAG  
**Repository:** `UkWood/ds-cosult`  
**PR/branch:** existing Draft PR #1, `docs/ds-01c-benchmark-memory`  
**Immutable R3 reviewed baseline:** `f4627e293c543fb5fa126915f96e3bd8a28aa223`  
**Original independent R3 verdict:** **DS-EC-AR-04 CHANGES REQUESTED — 0 BLOCKER / 1 IMPORTANT / 0 MINOR**, open **R3-CR01**, R2-CR01 PASS, R2-CR02 PARTIALLY CLOSED due to status/reason aggregation B08/B09.  
**Operation:** bounded **documentation-only** author correction. **NOT independent R4 acceptance, NOT code implementation, NOT executed tests**.  
**Final immutable R4 review SHA:** to be supplied by final PR comment and Architecture Session A owner-facing handoff after all Git commits, never a moving branch ref.

## 1. Baseline and actual edited paths

At task start, GitHub PR #1 HEAD **matched** the R3 baseline `f4627e293c543fb5fa126915f96e3bd8a28aa223` and was OPEN/DRAFT/UNMERGED. All edits were made to the existing branch and PR.

| Path | Old R3 blob SHA | New author-corrected blob SHA | Scope |
|---|---|---|---|
| `docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md` | `545aad110b54865372766162d4984fd00ef66d47` | `7d0bf4cb1fc790d799bcb81596e54ebf982b107e` | Normative **§13.1.1** single deterministic mixed-need reducer, slight precision corrections to §13.1 invalid P1/P2 and dependency isolation |
| `docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md` | `7d1ecdcd24e8bf5d87250fe2d360a933345f535a` | `1f8ec2edc745d968cca140dcce06ddb1c386ba72` | Clarified **AR-T22 / R1-F07** and designed 12 precise synthetic **R3-F01..F12** offline cases |

**Unmodified core contracts:** DS-EC-02 `32c7198cdd27c5a2423bc91f82b64b475eae2a65`, DS-EC-03 `a555564a8d1854930818f6b03047c22e3ac2b9e9`, DS-EC-04 `d76885a18ad034d49ae3f40755863424daa079ab`. All owner DS-SEC-07/08/09/10 decisions were preserved unchanged. Project status, history, this author report and independent R4 handoff receive documentary updates, not new policy.

## 2. R3-CR01 finding → concrete correction

### A1. Single FinalStatus reducer (DS-EC-05 §13.1.1)

The previous §13.1 allowed overlapping interpretations of `partial/error/clarification/needs_support` for mixed QuestionNeeds with metadata-only DocumentReference and a separately failing technical need.

The corrected normative algorithm uses **one ordered set of required QuestionNeeds**, each need accounted exactly once:
1. `SatisfiedNeed` is an abstract condition (NOT new serialized enum): a technically applicable, established `VerifiedClaim` **or** a metadata-only navigation `DocumentReference` satisfying its own corresponding need, each with exact claim/document reference citation.
2. `UnresolvedNeed`: need lacking safe applicable satisfaction, with one exact canonical reason, preserved under `NeedResolution.diagnostics_code` or, for pre-NeedResolution malformed P2, an existing sanitized diagnostic entry bound to `need_id`.
3. `PublishableObject`: `VerifiedClaim`, `DocumentReference` or source-attributed `ConflictPosition`; the latter is never a SatisfiedNeed and never established equipment truth.

The rule runs **after evidence, source coverage, conflict, dependency and citation validation**. A required dependent need cannot count as satisfied if its prerequisite fails unless independently source-proven without that prerequisite. Unsafe dependent claims are pruned before status selection; a malformed/cyclic dependency map yields `verifier_internal_error` and fail-closed behavior.

**One first-match status decision:**
- all required needs safely satisfied -> `answered`;
- at least one independently satisfied and at least one unresolved -> `partial`, with all unresolved reasons explicitly retained;
- zero satisfied and any internal/source error -> `error`;
- zero satisfied, no error but any unresolved ambiguity -> `clarification`;
- zero satisfied, no error or ambiguity -> `needs_support` (including missing, incomplete, unresolved genuine conflict and malformed P2 plan);
- pre-admission IP/quota/overlength/paid-budget rejection is **a separate static service path**, no claimed technical `answered`.

With zero satisfied needs, an `error` or `clarification` publishes **no** technical/document/conflict objects; `needs_support` may display valid independently source-proven **attributed** ConflictPositions with exact position citations, never an adopted disputed value.

### A2. One deterministic ReasonCode (existing DS-EC-02 §8.3.1 allowlist)

For fully answered needs: `document_reference_only` only when **all** required needs are navigation; otherwise `fully_supported` (including mixed navigation + technical).

For partial output, select the highest priority reason from all unresolved needs in a **fixed group+reason order**, without hiding the per-need outcomes:
- Error group: `verifier_internal_error > source_integrity_error > source_unavailable`.
- Clarification group: malformed-P1 `invalid_model_plan > interpretation_unsupported > ambiguous_variant > ambiguous_entity > ambiguous_question`.
- Support group: malformed-P2 `invalid_model_plan > applicable_source_conflict > source_scope_not_indexed > insufficient_evidence`.

**Partial selection priority:** errors, then clarification group, then support group. **No-satisfied** selection chooses the top reason **only within the status-determining group**: error before clarification before support. Ties use canonical frozen need order for display; LLM order never changes the result. The existing allowlisted compatibility codes `partial_missing_fact` and `partial_conflict` are **not emitted as top-level codes by this reducer**, so actual errors/coverage issues remain distinguishable; no enum values were added/deleted.

**Per-need reasons:** `NeedResolution` already defines `need_id,status,diagnostics_code`; `VerifiedAnswerResult` already contains `unresolved_need_ids[]` and sanitized `diagnostics[]`. The correction specifies exact need_id↔canonical reason correlation in the existing arrays and preserves the full cause set (including source errors) without expanding the public wire schema. For malformed P2, no fabricated NeedResolution.status; the existing diagnostics array carries `need_id` and `invalid_model_plan`. A malformed **P1** (not provider/backend validator exception) deterministically yields `NeedResolution=ambiguous_question`, reason `invalid_model_plan`, fixed static clarification and no second POST; an actual backend validator exception is `verifier_internal_error`, not malformed-model content. Valid P1 `interpretation_status=unsupported` remains `clarification/interpretation_unsupported`.

### A3. Typed object/citation constraints unchanged

- `VerifiedClaim`: established source-verified non-conflicting Fact/Relation; accepted `claim_kind=structured_fact|structured_relation`, eligible proof.
- `DocumentReference`: approved metadata navigation, not technical evidence; its `document_reference_id` citation cannot satisfy a technical need.
- `ConflictPosition`: independently verified *what the source says*, not adopted technical truth; position-specific citation.
- `CitationBinding`: exactly one of `claim_id|document_reference_id|position_id`. Technical source applicability / relation qualifiers required. One underlying Fact used for several needs requires **distinct need-bound VerifiedClaims**, not one object implicitly satisfying arbitrary needs.

This is a refinement of the previous canonical DS-EC-05 §13.1 reducer, not a parallel alternate status enum/machine. Owner security and paid budget decisions remain unaffected.

## 3. R3-F01..R3-F12 deterministic expected outcomes

**All below are synthetic fixture definitions, NOT executed results.** Exact per-need outcomes, candidate proof states/absence, objects, citations and POST counts are specified in `docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md`.

| Fixture | FinalStatus | Single ReasonCode | unresolved_need_ids | Published evidence objects | New extra paid POST? |
|---|---|---|---|---|---|
| R3-F01 navigation only | `answered` | `document_reference_only` | [] | 1 DocumentReference + document citation | 0 |
| R3-F02 navigation + confirmed Fact | `answered` | `fully_supported` | [] | DocumentReference + VerifiedClaim, separate citations | 0 |
| R3-F03 nav + source not indexed | **`partial`** | **`source_scope_not_indexed`** | [N2] | Nav DocumentReference + citation | 0 |
| R3-F04 nav + source unavailable | **`partial`** | **`source_unavailable`** | [N2] | Nav DocumentReference + citation; error reason retained | 0 |
| R3-F05 variant-independent nav + variant ambiguity | **`partial`** | **`ambiguous_variant`** | [N2] | Nav DocumentReference + citation | 0 |
| R3-F06 nav + genuine scoped conflict | **`partial`** | **`applicable_source_conflict`** | [N2] | Nav DocReference + 2 attributed ConflictPositions, 3 citations | 0 |
| R3-F07 malformed P2, no independent proof | `needs_support` | `invalid_model_plan` | [N1] | None | 0 retry after original 1 P2 |
| R3-F08 verified independent Fact + malformed P2 for another need | `partial` | `invalid_model_plan` | [N2] | 1 eligible VerifiedClaim + claim citation | 0 retry after original 1 P2 |
| R3-F09 independent Fact + source unavailable for another | **`partial`** | **`source_unavailable`** | [N2] | 1 VerifiedClaim + citation | 0 |
| R3-F10 no satisfied; conflict + source unavailable + ambiguity | **`error`** | **`source_unavailable`** | [N1,N2,N3] | None, error-mode fail closed; per-need reasons all retained | 0 |
| R3-F11 dependency on unavailable prerequisite | `error` | `source_unavailable` | [N1,N2] | None; candidate eligible dependent value withheld | 0 |
| R3-F12 valid P1 unsupported | `clarification` | `interpretation_unsupported` | [N1] | None | 0 P2 after original 1 P1 |

The **exact per-need diagnostic triples and expected citation targets** are in the fixture contract. R3-F10 retains three different per-need reasons `applicable_source_conflict,source_unavailable,ambiguous_variant` even though the top reason is `source_unavailable`. R3-F11 retains upstream and dependent failure details. The source/endpoint identities and all product values in fixtures are synthetic only.

## 4. Original and regression acceptance checklist — AUTHOR DOCUMENTATION SELF-CHECK ONLY

| Gate | Status of authored clauses, NOT executed testing |
|---|---|
| R3-CR01 unique FinalStatus, ReasonCode, no pseudotypes | Specified in DS-EC-05 §13.1.1 |
| R2-CR01 truthful `OUTPUT_STAGED` vs transport display | DS-EC-04 unchanged |
| R2-CR02 seven `proof_state` values / separate DocumentReference | DS-EC-02 and DS-EC-05 §3 unchanged |
| R1-CR01 SourceAssertionProof/ConflictAssessment vs ConflictPosition | Unchanged |
| R1-CR02 dispatch-intent / reserved call-slot / unknown charge no retry | Unchanged |
| R1-CR05 DS-SEC-10 Option A protected local P0 / P1/P2 paid breaker | Unchanged |
| Original source coverage, provenance, physical PDF page, variants/units, relation direction | Unchanged |
| Model total input ≤10,000 / output ≤450, maximum 1 paid POST | Unchanged |
| IP one session, 20 admitted questions/day incl P0; 15m memory, 30m series, Q6–Q11 | Unchanged |
| AR-T01–22 and SEC10-T01–07 fixture descriptions | Design-only desk-check; 22 original tests preserved; no runtime test performed |
| Visitor direct Goal Hijacking, trusted site/PDF boundary | Unchanged |
| Controlled renderer/no post-policy LLM rewriting | Unchanged |

**Not yet independently accepted:** R3-CR01. Author's self-check cannot assert PASS; independent Architecture Acceptance Review R4 required.

## 5. Open future launch dependencies, not part of scope

Previous owner WSL: only 3 of 12 PDF sources byte-pinned, zero expert-approved Ground Truth and P4/P5 real source claim review incomplete; no Corpus Freeze. Operator daily/monthly USD budget figures, genuine support contacts, IANA timezone, trusted proxy topology, visitor privacy notice/legal basis/audit deletion policy all still pending. No model runtime implementation, unit tests, public pilot or new paid API call is authorized.

**Governance:** NO Merge, no code/DS-02, no paid DeepSeek HTTP (prior DS-QV-01 6/6 used), no production, no Corpus Freeze, no NEW RAG writes and no changes to read-only `UkWood/Saturn-Main-Site`.

## 6. Required next independent gate

New **Architecture Acceptance Review Session R4** in a separate project chat must independently inspect the exact final frozen Git HEAD, this report, original R3 task/findings, actual DS-EC-05 §13.1.1, full 12-case fixture matrix, original 22 AR-T and seven SEC10-T, and regressions, then give a **single PASS or CHANGES REQUESTED**. No author-issued acceptance.
