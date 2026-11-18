# DS-EC-02–05 — R3 INDEPENDENT ARCHITECTURE ACCEPTANCE HANDOFF

**Created:** 2026-11-18  
**Project:** «DS-консультант» (independent from NEW RAG)  
**Status:** READY FOR INDEPENDENT R3 IN A NEW PROJECT CHAT — NO AUTHOR SELF-ACCEPTANCE  
**Repository:** `UkWood/ds-cosult`  
**PR:** Existing [Draft PR #1](https://github.com/UkWood/ds-cosult/pull/1)  
**Branch:** `docs/ds-01c-benchmark-memory`  
**Original R2 immutable reviewed HEAD:** `99a49a49441055a6324b0aac43a58858940e682a`  
**R3 corrected HEAD:** The **exact immutable full SHA** published by Architecture Session A in the FINAL R3 handoff/PR comment after all files have been written. Reviewer MUST verify it using PR metadata and use **that SHA as `ref` for every read**, not a moving branch ref. This document intentionally does not self-reference a commit SHA because committing it changes HEAD.

## 1. Independent review task, scope and role

You are **Independent Architecture Acceptance Review Session R3**, a distinct new conversation inside the SAME ChatGPT project «DS-консультант». The previous author's only assignment was to fix **two IMPORTANT findings R2-CR01 and R2-CR02**. You must independently inspect their actual corrected Git blob content and decide whether the DS-EC-02–05 architectural contract set is finally internally consistent.

**R2 outcome:** `DS-EC-AR-03 — Independent Architecture Acceptance Review R2` = **CHANGES REQUESTED, 2 IMPORTANT, 0 new BLOCKER**. The user pasted the complete 617-line R2 report in Architecture Session A conversation. Review found original 4/4 BLOCKER PASS, prior AR-T01–22 design desk check 20 PASS / 2 NEEDS CORRECTION (AR-T20 and AR-T22), seven DS-SEC-10 tests PASS **at documentation level**, 0 executable tests run. Remaining R1-CR03 and R1-CR04, plus partial R1-CR06, must be closed by correcting only two types of contradictions.

The author report is NOT acceptance proof. A separate R3 session and frozen HEAD improve independence only if the reviewer actually checks original R2 findings, precise normative clauses and cross-contract consistency.

## 2. Required reading order, all at same immutable R3 HEAD

1. Author-to-R3 scope document: `docs/handoffs/DS-EC-02-05-R3-INDEPENDENT-ARCHITECTURE-REVIEW-HANDOFF.md` (this file).
2. **Original** `docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md` (DS-EC-AR-01, original 4 BLOCKER / 8 IMPORTANT / 2 MINOR).
3. Independent R1 summary `docs/acceptance/DS-EC-AR-02-INDEPENDENT-R1-FINDINGS-RECEIPT.md`.
4. Complete user-supplied independent **R2 report DS-EC-AR-03** (617 lines, dated 2026-11-18). It was uploaded in the preceding Architecture Session A as `Вставленный текст(3).txt`. The original user-supplied report is the authoritative reviewer finding, not a summarization by the author; request it or use previous project conversation if unavailable.
5. Author's **R3 correction trace** `docs/acceptance/DS-EC-AR-03-R3-CONSOLIDATED-CORRECTIONS-REPORT.md`. Treat as allegations to verify.
6. Actual corrected contracts:
   - `docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md`
   - `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md`
   - `docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md`
   - `docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md`
7. Test design `docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md` — AR-T01–22; specifically AR-T20/22 and R1-F06/F07 (**NOT executed**).
8. Binding owner security decisions:
   - `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md`
   - `docs/decisions/DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md`
   - `docs/decisions/DS-SEC-09-OWNER-APPROVED-MEMORY-AND-QUESTION-QUOTA.md`
   - `docs/decisions/DS-SEC-10-OWNER-APPROVED-PAID-BUDGET-BREAKER-LOCAL-P0.md`.
9. Project status/history are supporting audit trail only, not independently proof of architecture compliance: `docs/status/PROJECT_STATE.md`, `docs/history/ARCHITECTURE_LOG.md`.

## 3. Mandatory R3-CR01 / R2-CR01 audit delivery acceptance

R2 established contradiction: DS-EC-04 §14.1.1 distinguished server-side staging/transport from actual browser rendering, but normative §14.3 claimed private audit contained `actually displayed` final text. Similar outdated expressions occurred in DS-EC-04 §§2/6, DS-EC-03 §8 and DS-EC-05 §9.

Verify **all eight** precise R2 acceptance requirements:

1. No active normative duty to prove `actually displayed` based solely on server events. Older text may remain historical only with explicit supersession.
2. `OUTPUT_STAGED` contains the exact prepared deterministic answer, not proof of delivery.
3. `delivery_status=transport_accepted` and HTTP 2xx do not prove browser display/human reading.
4. `client_ack_status` is optional and separately logged, never equated with visual reading.
5. Immutable exact `server_response_exact_bytes` / protected byte storage and `response_bytes_sha256` remain alongside `staged_answer_text`.
6. Idempotent replay allowed only to **the original anonymous session with still-valid lease**.
7. Transport failed/unknown allows **no new DeepSeek POST**; may replay stored response bytes only under #6.
8. AR-T20 and R1-F06 specify correct typed expected outcomes.

Do not modify or reopen already accepted provider request FSM, dispatch-intent counting and uncertain-charge no-retry design.

## 4. Mandatory R3-CR02 / R2-CR02 typed proof and navigation acceptance

R2 found DS-EC-05 §13.1 falsely placed `source_reference_only` (a metadata document navigation type) and `invalid_model_plan` (a ReasonCode) in the `proof_state` column, although the declared enum is `eligible|inapplicable|unsupported|conflict|not_indexed|source_error|internal_error`.

Verify **all nine** R2 acceptance requirements:

1. Every status table row uses one of seven exact allowed proof enum values **or an explicit absence marker** when no candidate was evaluated.
2. A missing technical verified claim is represented as **no VerifiedClaim**, not a new fake proof_state.
3. `DocumentReference` is a separate metadata-only type, not `claim_kind=source_reference_only` inside VerifiedClaim.
4. Invalid JSON/plan/ID produces **`ReasonCode=invalid_model_plan`**, not a proof_state, and never accepted model-derived technical facts.
5. A document link/navigation-only answer cannot be `answered` if required technical needs remain unresolved.
6. `ConflictPosition` is a separately attributed source assertion, never an established VerifiedClaim for the disputed property.
7. Common type schema versions, `NeedResolution`, `FinalStatus`, `ReasonCode`, `DocumentReference`, `VerifiedAnswerResult`, `CitationBinding` IDs, and claim_kind are consistent between DS-EC-02 registry (§8.3.1) and DS-EC-05 (§3.2–3.4, §13.1).
8. AR-T22 and R1-F07 have exhaustive noncontradictory expected outcome for malformed plans, metadata navigation, conflict and mixed partial/error.
9. Two independent coders following only normative text would choose the same typed output, not two alternative pseudo-enums.

Include test cases: (a) pure navigation-only need can be answered with DocumentReference and citation but zero technical claims, (b) navigation plus unanswered technical need => not overall answered, (c) malformed P2 candidate => no accepted model facts, no second paid call, possible separate independently grounded partial, (d) two proven conflicting positions => cited as positions but no confirmed fact.

## 5. Regression checks — do not reopen proven design without a newly identified flaw

- R1-CR01: source truth proof separate from attributed conflicting source positions (including wrong PDF table row rejection).
- R1-CR02: provider call-slot reservation separate from durable POST dispatch-intent and unknown-charge accounting; valid P1 `interpretation_status=unsupported` → `ambiguous_question`, reason `interpretation_unsupported`, final clarification, at most one P1 POST, no second P2.
- R1-CR05: owner DS-SEC-10 **Option A**: exhausted global paid DeepSeek USD ⇒ P1/P2 denied **before accepted-turn debit**; protected zero-paid **P0** may answer if source verified and IP/20/day/Q11/CPU/concurrency/audit guards satisfied. No P0 promotion from cached free-form LLM prose or fabricated source.
- Original SourceCoverageReceipt (scoped declared-source completeness), EvidenceEligibilityPolicy/site/PDF physical page and exact table cell, site canonical identity/variant/version, relation direction/units, provider input ≤10,000 tokens / output ≤450, one paid call per accepted turn, 15-minute memory expiry and separate 30-minute IP series and operator-calendar-day quota.
- Visitor direct Goal Hijacking cannot change system role/source/proof/quotas, source site+PDF remain owner-declared trusted and injection-free.
- Audit retention default 30 days in private staff-only store, exact IP/source/status/UTC but no false claim of browser display.

## 6. Output requirements

Produce **one independent reviewer report** in Russian:
- exact immutable reviewed Git HEAD, original PR state OPEN/DRAFT/UNMERGED, Git blob SHA for core contracts and normative owner documents;
- independent pass/open status **R2-CR01** and **R2-CR02** against each of **8+9** criteria;
- re-evaluated **AR-T20/22** and **R1-F06/F07** design-level cases; regression assessment of 20 prior PASS and DS-SEC-10 seven cases;
- any new contradictions, with one consolidated list BLOCKER/IMPORTANT/MINOR and precise corrective instructions;
- **final architecture verdict PASS or CHANGES REQUESTED**, never author-supplied self-approval;
- independent distinction between architectural desk-check, **0 executed tests**, source/benchmark GT readiness, privacy/operational launch controls, separate coding/paid-API/Merge permissions;
- do not change source contracts in the reviewer role. If a repo report/comment is needed, do so only within existing Draft PR #1, with owner authorization and no merge.

## 7. Ready-to-paste starting task for the R3 new project chat

Ты — **независимая Architecture Acceptance Review Session R3** проекта «DS-консультант». Проведи полную независимую повторную приёмку исправленных контрактов **DS-EC-02–05** в существующем Draft PR #1 `UkWood/ds-cosult`. Проверь HEAD PR #1 и зафиксируй **точный полный Git SHA, переданный Architecture Session A в последнем handoff**; читай все GitHub файлы только по этому immutable SHA.

Сначала прочитай `docs/handoffs/DS-EC-02-05-R3-INDEPENDENT-ARCHITECTURE-REVIEW-HANDOFF.md`, полный независимый отчёт R2 (DS-EC-AR-03), `docs/acceptance/DS-EC-AR-03-R3-CONSOLIDATED-CORRECTIONS-REPORT.md`, исходные DS-EC-AR-01 / независимые R1, фактические исправленные DS-EC-02/03/04/05, DS-SEC-07/08/09/10 и offline fixture contract.

Независимо проверь **R2-CR01** (все 8 требований truthful audit/delivery, не путать `OUTPUT_STAGED` с отображением браузером), **R2-CR02** (все 9 требований типизации `proof_state`/ReasonCode/`DocumentReference`), **AR-T20/22, R1-F06/F07**, а также регрессии прошлых PASS, one-call ProviderDispatchGuard и owner DS-SEC-10 Option A (защищённый P0 при исчерпанном платном USD бюджете).

Не доверяй авторскому отчёту, используй реальные Git blob SHAs. Выдай **один консолидированный PASS или CHANGES REQUESTED**, аргументированные изменения/замечания и чётко отдели архитектурную приёмку от неисполненных тестов и разрешений на кодирование/внедрение.

**Никаких Merge, кодирования, платных DeepSeek API, Production, Corpus Freeze, изменений NEW RAG или доверенного сайта «Сатурн».**

## 8. Scope boundaries and pre-implementation gates

- Existing Draft PR only; no new PR, merge, repository split or source-site write.
- Previous paid DeepSeek DS-QV-01 GO 6/6 exhausted; no additional paid calls without separate owner limit/GO.
- Real approved PDF source custody incomplete by earlier owner WSL reports (3/12 bytes pinned), expert-approved benchmark Ground Truth 0; architecture acceptance does not freeze or verify entire corpus.
- Operator USD day/month budget figures, real support contacts, trustworthy proxy chain, IANA calendar reset zone, privacy/legal visitors notice and 30-day delete/backup policies remain launch configuration/acceptance gates.
- Independent R3 PASS does **not** itself grant DS-02 coding, runtime deployment or Merge. Next step requires separate explicit owner decision.
