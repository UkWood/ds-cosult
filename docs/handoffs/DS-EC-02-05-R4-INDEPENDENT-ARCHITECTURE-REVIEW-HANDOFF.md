# DS-EC-02–05 — R4 INDEPENDENT ARCHITECTURE ACCEPTANCE REVIEW HANDOFF

**Date:** 2026-11-18  
**Project:** «DS-консультант» — Entity-Centric Conversational RAG  
**Role:** new independent Architecture Acceptance Review Session **R4** in a DIFFERENT ChatGPT project conversation  
**Repository:** `UkWood/ds-cosult`  
**Existing PR:** [Draft PR #1](https://github.com/UkWood/ds-cosult/pull/1) — OPEN, DRAFT, NO MERGE  
**Branch (navigation only):** `docs/ds-01c-benchmark-memory`  
**Previous immutable R3 review baseline:** `f4627e293c543fb5fa126915f96e3bd8a28aa223`  
**NEW R4 immutable review SHA:** read the final exact full PR HEAD announced **after this handoff file and status/history are committed** in the owner's closing message and PR summary comment. Verify it equals PR #1 HEAD on review kickoff and use that **full SHA as the ref for EVERY source read**, not moving branch HEAD.

## 1. Reviewer independence and mission

You did not author the corrected contracts. Independently verify **R3-CR01**, the single remaining **IMPORTANT** from **Independent DS-EC-AR-04 R3**. The previous R3 verdict was **CHANGES REQUESTED — 0 BLOCKER / 1 IMPORTANT / 0 MINOR**. Other fundamental contracts were independently accepted at documentation level and must not be changed without a new concrete defect.

**Author corrections are claims to inspect, NOT evidence of acceptance**. R4 evaluates architectural-document consistency only. It must return ONE clear **PASS or CHANGES REQUESTED**, with complete consolidated issues if any. It does not execute an implementation, issue a Merge, permit more paid provider calls, freeze the corpus or open production.

## 2. Required primary source reading order — all GitHub files by same immutable R4 SHA

1. This file: `docs/handoffs/DS-EC-02-05-R4-INDEPENDENT-ARCHITECTURE-REVIEW-HANDOFF.md`.
2. Independent R3's original owner-supplied task **Architecture Task A-R3-CR01** (370-line pasted attachment `Вставленный текст(4).txt` in Architecture Session A). It records original DS-EC-AR-04 outcome and exact R3-CR01 requirements. Ask owner for the attachment in new session if not accessible; do NOT pretend the author's correction trace replaces the independent finding.
3. Author correction trace: `docs/acceptance/DS-EC-AR-04-R4-CONSOLIDATED-CORRECTIONS-REPORT.md`; check actual source facts rather than trusting conclusions.
4. **Principal contract:** `docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md` — §3.2–3.4, **§13.1 and new normative §13.1.1**, §13.2–13.4.
5. **Principal fixture spec:** `docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md` — AR-T01–22, revised AR-T22/R1-F07, **R3-F01..R3-F12**, all **NOT EXECUTED**.
6. Cross-check unchanged canonical registry: `docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md` — §6 NeedResolution fields and §8.3.1 ReasonCode/FinalStatus/types.
7. Unchanged DS-EC-03/04 on evidence packet/one-call provider and truthful audit:
  - `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md`;
  - `docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md`.
8. Binding owner decisions (must not reinterpret or weaken): `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md`, `DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md`, `DS-SEC-09-OWNER-APPROVED-MEMORY-AND-QUESTION-QUOTA.md`, `DS-SEC-10-OWNER-APPROVED-PAID-BUDGET-BREAKER-LOCAL-P0.md`.
9. Earlier historical reviews and project status for context only: `docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md`, `docs/acceptance/DS-EC-AR-03-R3-CONSOLIDATED-CORRECTIONS-REPORT.md`, `docs/status/PROJECT_STATE.md`, `docs/history/ARCHITECTURE_LOG.md`.

## 3. Specific R3-CR01 acceptance checklist

**A. One deterministic FinalStatus for arbitrary mixed QuestionNeeds**
1. Defines `SatisfiedNeed` (technical VerifiedClaim OR navigation DocumentReference), `UnresolvedNeed` with per-need reason, `PublishableObject` (VerifiedClaim / DocumentReference / ConflictPosition) as **logical classifications**, not new wire enums.
2. `ConflictPosition` is **not a satisfied technical need** and source-attributed conflicts cannot be published as established equipment truths.
3. Uses a fixed ordered set of required needs; no missing/duplicate `need_id` may silently count as satisfied.
4. Dependency pruning precedes status aggregation. Unresolved prerequisite cannot be used to derive/issue unsafe dependent Fact or falsely publish partial. Independent source-verified needs may remain.
5. Status precedence when **all required needs safely satisfied** => `answered`; **some satisfied, others unresolved** => `partial` if independence/safety verified; **none satisfied** => error first, else clarification, else needs_support; pre-admission denied requests use separate static service path.
6. Status and published object arrays align: in zero-satisfied error/clarification no technical/document/conflict objects, conflict positions may be attributed only under safe supported modes. Empty `QuestionNeeds` never `answered`.

**B. One deterministic ReasonCode and lossless individual reasons**
7. Top-level `ReasonCode` selected exclusively from existing DS-EC-02 §8.3.1 allowlist: all navigation fulfilled => `document_reference_only`; fulfilled technical or mixed navigation+technical => `fully_supported`; otherwise exact ranked unresolved reason.
8. All unresolved reasons remain attached to exact `need_id` via existing `NeedResolution.diagnostics_code` and sanitized `VerifiedAnswerResult.diagnostics[]` for any pre-resolution malformed P2. No new wire `reason_codes[]`, new pseudo-enum or public schema expansion.
9. Error priorities: `verifier_internal_error > source_integrity_error > source_unavailable`; clarification (including fixed malformed P1) and support reasons have explicit deterministic ranks. Error beats clarification/conflict if none satisfied. For partial, any unresolved error must remain visible and precede missing-source claims in top-level cause.
10. Valid P1 `unsupported` remains `NeedResolution=ambiguous_question`, final `clarification/interpretation_unsupported`, one already counted provider POST, no second P2.
11. Malformed P1 output uses `invalid_model_plan` as ReasonCode, fixed clarification unless backend verifier itself broke; malformed P2 cannot produce accepted model-derived Fact and does not trigger another model call.
12. No `source_unavailable` / `source_integrity_error` / `verifier_internal_error` may be relabeled `insufficient_evidence` or falsely claim negative physical characteristic. Historical `partial_missing_fact` and `partial_conflict` remain recognized canonical allowlist but the reducer must not ambiguously select them instead of specific error/status reasons.

**C. Typed object/citation preservation**
13. Only eligible non-conflicting Fact/Relation `VerifiedClaim` is an established technical assertion. A metadata-only DocumentReference with `document_reference_id` citation only fulfills a navigation need. A ConflictPosition is independently cited with `position_id` and never resolves a conflict.
14. Each citation has **exactly one** `claim_id|document_reference_id|position_id`; no underlying source fact silently covers a different `need_id` without its own independently verified need-bound object.
15. No arbitrary model-generated technical text/rewrite after source verification, no source URL guessing, no unverified parent-to-variant inheritance.

## 4. Exact mandatory design fixtures — inspect R3-F01..R3-R3-F12 independently

R3-F01 navigation only => `answered/document_reference_only`; R3-F02 navigation+verified Fact => `answered/fully_supported`; R3-F03 navigation+unindexed characteristic => **`partial/source_scope_not_indexed`**; R3-F04 navigation+unavailable source => **`partial/source_unavailable`**; R3-F05 variant-independent nav+ambiguous variant => **`partial/ambiguous_variant`**; R3-F06 navigation+two genuine contradictory positions => **`partial/applicable_source_conflict`** with 2 attributed citations and 0 established claims for conflict.

R3-F07 malformed P2 no independently verified Fact => `needs_support/invalid_model_plan`, 0 accepted model facts, no retry. R3-F08 independent technical Fact + malformed P2 for different need => `partial/invalid_model_plan`. R3-F09 independent Fact + other source unavailable => **`partial/source_unavailable`** with explicitly unresolved error. R3-F10 none satisfied, conflict + source error + ambiguity => **`error/source_unavailable`**, all three per-need reasons preserved, no public objects under fail-closed error. R3-F11 dependent technical need invalidated by upstream source unavailable => `error/source_unavailable`, no unsafe partial. F12 valid P1 unsupported => `clarification/interpretation_unsupported`, one paid P1 attempt, no P2.

For each F case independently validate: each NeedResolution status / missing-pre-resolution status, per-need canonical reason and candidate proof_state/absence, allowed published VC/DR/CP, exact `FinalStatus`, exact singular `ReasonCode`, ordered `unresolved_need_ids[]`, all citation target identities and 0 paid **additional** POST on malformed/unknown/clarification. Compare AR-T22 and R1-F07 for consistency, not just keyword presence.

**Regression:** original 22 AR-T design criteria preserved, **seven SEC10-T01..07** owner budget behavior preserved. No tests were executed; all are prospectively specified fixtures.

## 5. No-regression invariant checklist

- Original SourceCoverageReceipt scoped source completeness; missing source/index/parser status never invented "property absent".
- SourceAssertionProof, ConflictAssessment, FactPublicationDecision, ConflictPosition; correct PDF table row/revision/variant and source citations.
- ProviderDispatchGuard for any P1/P2 paid POST, whole input ≤**10,000 tokens**, max output **450**, at most **one** paid POST per accepted question; separate reserved slot vs durable dispatch-intent and no auto-retry on uncertain charge.
- Anonymous no-registration one active IP session, 20 **accepted questions/IP/operator calendar day including P0**, 15-minute memory expiry, 30-minute IP series reset, progressive cooldown/Q11 support handoff, private 30-day UTC/IP/Q&A audit.
- Owner **DS-SEC-10 Option A**: global paid DeepSeek USD exhaustion blocks new P1/P2 **before turn debit**, but verified zero-provider P0 may continue within all the independent IP/20-day/series/CPU/concurrency/source/citation/audit and nonmonetary safety guards. Cached unchecked LLM prose is never P0.
- R2-CR01 truthful server audit: staged answer/HTTP transport/client_ack do not prove human visual display; exact saved bytes may replay only to original still-active anonymous session and no second paid POST.
- Strict Saturn domain; only direct visitor input treated as Goal Hijacking threat. Trusted approved Saturn site and PDFs are owner-declared injection-free and source repo is READ-ONLY.
- No editing or writes to independent NEW RAG project.

## 6. Required R4 deliverable

Provide **one** complete independent Architecture Acceptance Review report:
- exact immutable reviewed Git HEAD, PR OPEN/DRAFT/UNMERGED, exact blob SHAs of DS-EC-02–05 and fixture contract;
- R3-CR01 PASS or OPEN with **explicit source clause references**, and pass/open for each of the 15 numbered criteria above;
- 12-case R3-F matrix independently checked (with typed details), consistency of AR-T22/R1-F07, no regressions in prior 20 AR-T and DS-SEC-10 7 scenarios;
- any new defects in **one consolidated** BLOCKER/IMPORTANT/MINOR list with proposed minimal corrections and acceptance tests;
- one final verdict **PASS** or **CHANGES REQUESTED** for **architecture documents only**;
- clearly state **0 tests executed**, no ready production source GT, no operator budget/legal/proxy config;
- no code, paid provider calls, Merge, new PR or source contract edits by the independent reviewer.

## 7. Ready-to-paste instruction for new R4 project chat

Ты — независимая **Architecture Acceptance Review Session R4** проекта «DS-консультант». Проведи полный независимый Acceptance Review исправленного нормативного контракта DS-EC-05 и согласованного комплекта DS-EC-02–05 в **существующем Draft PR #1** репозитория `UkWood/ds-cosult`.

**Проверяемый Git HEAD:** используй полный SHA из последнего финального сообщения Architecture Session A и сверь его с PR #1. Читай все GitHub документы **строго по этому immutable SHA**, а не по имени ветки.

Изучи `docs/handoffs/DS-EC-02-05-R4-INDEPENDENT-ARCHITECTURE-REVIEW-HANDOFF.md`, исходное независимое задание R3 `Architecture Task A-R3-CR01`, `docs/acceptance/DS-EC-AR-04-R4-CONSOLIDATED-CORRECTIONS-REPORT.md`, реальный DS-EC-05 §13.1.1, DS-EC-02 §8.3.1 и offline fixture contract. **Самостоятельно проверь R3-CR01**, 12 сценариев R3-F01..12, AR-T22/R1-F07, единственные FinalStatus/ReasonCode, зависимые потребности и отсутствие потери per-need причин. Проверь регрессии прежних PASS, включая DS-SEC-10 Option A и one-call token/IP protections. Не доверяй авторской оценке. Выдай один полный консолидированный вердикт PASS либо CHANGES REQUESTED с точными нормативными доказательствами.

**Запреты:** Merge, code/DS-02, новые платные DeepSeek API, Production, Corpus Freeze, любые изменения NEW RAG и read-only сайта «Сатурн». Никакие offline fixtures не считать выполненными без реальных результатов.

## 8. Governance / next decision

- No new paid DeepSeek calls (earlier DS-QV-01 6/6 spent). No merge or backend implementation from this handoff.
- Earlier real source readiness: 3/12 PDF bytes pinned, 0 expert approved benchmark Ground Truth, claim-by-claim P4/P5 review open; no Corpus Freeze.
- Operator daily/monthly USD limits, exact IANA timezone, verified support contacts, trusted proxy chain, privacy/legal visitor notice and 30-day audit/backup deletion remain pre-pilot gates.
- Even a positive independent **R4 PASS** would accept only **architecture documents** and require a separate explicit owner authorization for the next coding/offline validation stage.
