# DS-EC-02–05 — R2 INDEPENDENT ARCHITECTURE ACCEPTANCE HANDOFF

**Date:** 2026-11-18  
**Status:** AUTHOR HANDOFF — INDEPENDENT R2 NOT YET PERFORMED  
**Repository:** UkWood/ds-cosult (exact name)  
**Existing branch and PR:** docs/ds-01c-benchmark-memory, Draft PR #1, OPEN/UNMERGED  
**Independent R1 frozen HEAD:** 7625b27c30d9dd558dffb5f1069b6b4a4d8e055e  
**R2 review ref:** use the FULL frozen SHA in the final owner-facing handoff / PR comment after all documentation updates. Independently confirm the PR metadata. Use this exact SHA as the GitHub ref for ALL source reads; never a moving branch name during verification.

## 1. Role and independence

You are a NEW independent Architecture Acceptance Review Session R2 in a separate conversation of the SAME ChatGPT project DS-консультант. You did not author the corrections. Independently assess the actual corrected documents by frozen Git commit, not assertions in author reports. The R2 goal is a single architecture-document verdict PASS or CHANGES REQUESTED. Never treat document-only checks as executed code/backend tests or as corpus/production acceptance.

Owner explicitly approved a new policy DS-SEC-10: **when global DeepSeek-paid USD budget is exhausted, P1/P2 are blocked, but verified zero-provider local P0 remains available within all independently accepted IP, day quota, series, cooldown, local CPU, concurrency, source evidence and audit guards.** The 20-questions/IP/day allowance includes local P0 and a P0 answer consumes one accepted visitor turn. A budget-denied paid question consumes zero accepted turns. Never reopen variant B unless the owner issues a new explicit decision.

## 2. Required documents — read in this order by frozen SHA

1. Original consolidated architecture review: docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md (DS-EC-AR-01: 4 BLOCKER, 8 IMPORTANT, 2 MINOR).
2. Independent R1 findings receipt: docs/acceptance/DS-EC-AR-02-INDEPENDENT-R1-FINDINGS-RECEIPT.md (CHANGES REQUESTED; the full user-supplied 938-line independent R1 report remains in previous project conversation; the receipt is NOT a verbatim full report).
3. Author R2 corrections trace: docs/acceptance/DS-EC-AR-02-R2-CONSOLIDATED-CORRECTIONS-REPORT.md. Do not trust author conclusions.
4. Synthetic offline fixture contract: docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md (AR-T01–22 plus R1-F01–F12). None were executed.
5. Actual corrected contracts: docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md; docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md; docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md; docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md.
6. Authoritative decisions: docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md; DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md; DS-SEC-09-OWNER-APPROVED-MEMORY-AND-QUESTION-QUOTA.md; **DS-SEC-10-OWNER-APPROVED-PAID-BUDGET-BREAKER-LOCAL-P0.md**.
7. Cross-context: docs/architecture/DS-EC-01-ENTITY-CENTRIC-VERIFIABLE-RAG-REFERENCE.md; docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md; docs/security/DS-SEC-06-IP-LEASE-DAILY-LOCKOUT-AUDIT-PROPOSAL.md; docs/status/PROJECT_STATE.md; docs/history/ARCHITECTURE_LOG.md. These are context, not substitutes for primary contracts.

## 3. Six mandatory R1 issues — independent dispositions

**R1-CR01 (BLOCKER):** verify SourceAssertionProof/ConflictAssessment/FactPublicationDecision/ConflictPosition separate genuine source position from established technical fact. A says 24 В and B says 12 В in same synthetic variant: both correctly source-proven positions may be displayed with two citations in conflict mode, but neither is an established VerifiedClaim. Wrong PDF row cannot qualify, despite valid page SHA. Check AR-T02, EC5-06, EC5-40 and R1-F01/02.

**R1-CR02 (BLOCKER):** differentiate reserved provider authorization, durable outbound dispatch-intent, conservative counted at-risk POST and provider_outcome_unknown. A provable crash before dispatch intent/no socket send gives 0 recorded POST attempts; a crash after intent with uncertain send gives 1 conservative at-risk attempt and held budget, never automatic retry. Valid P1 interpretation_status=unsupported after admitted POST maps to NeedResolution ambiguous_question/reason interpretation_unsupported, final clarification, with no quota refund and no extra P2. Check AR-T13/T22 and R1-F03/04/05.

**R1-CR03 (IMPORTANT):** distinguish staged deterministic answer, exact response bytes, server transport attempt and delivery_status, optional client_ack. Server staging/HTTP 2xx never proves browser/human visual receipt. Idempotent replay to original valid session only. Check AR-T20, EC5-38, R1-F06.

**R1-CR04 (IMPORTANT):** inspect shared NeedResolution, SourceAssertionProof, ConflictPosition, publication role, VerifiedClaim, metadata-only DocumentReference, invalid_model_plan and complete final status/reason cross-table. No answered technical claim for missing/conflicted/wrong-variant needs. Check AR-T22, R1-F07.

**R1-CR05 (IMPORTANT — OWNER DECISION APPROVED):** read DS-SEC-10 and its normative reconciliation into DS-SEC-07/09, DS-EC-01/03/04/05, security resources/IP documents and AR-T21/R1-F08/F10/F11/F12. Paid P1/P2 denied on exhausted provider USD BEFORE daily question admission; verified source-cited P0 may remain available and consumes one of 20 questions, 0 model cost, no reserved call slot, no dispatch event. Other IP/day/series/CPU/concurrency/audit and nonmonetary safety breakers still apply. A cached freeform LLM answer is NOT local P0. Check operator money figures are NOT fabricated.

**R1-CR06 (MINOR):** check DS-EC-05 normative 13.1–13.5 numbering, DS-EC-04 title v0.2, canonical type/enum naming, metadata-only citation, historical DS-SEC-08 billable-only wording marked superseded, and daily AR-T09/10 test design uses two allowed series of up to ten questions each with ≥30m idle reset and same operator-calendar-day cap.

## 4. Original findings + test coverage

Repeat coverage on original DS-EC-AR-01 4 BLOCKER / 8 IMPORTANT / 2 MINOR; no new contradiction may reopen already solved B01 source coverage, B03 universal paid guard, I03 entity versioning or I04 units/dictionary. Independent R1 had 17 design cases PASS, five NEEDS CORRECTION (AR-T02, T13, T20, T21, T22) and **zero executed**. R2 should re-evaluate all 22 design cases and the additional DS-SEC-10 tests SEC10-T01–T07.

Include cases: early G2 interpret call full input >10,000 tokens must issue zero POST; max output 450, one call slot per accepted turn; unpaid domain admission before any paid classifier; unknown charge no replay; P0 never bypasses daily 20, one-session IP lock, Q11 series support, CPU or private audit. Website/approved PDFs are owner-declared trusted and injection-free; primary injection threat is direct user Goal Hijacking.

## 5. Required report structure

- Exact reviewed immutable Git HEAD and all key Git blob SHAs, same existing PR status.
- One final **PASS** or **CHANGES REQUESTED** for architecture documents only.
- Consolidated status of R1-CR01–06 plus original 4/8/2 defects, exact source evidence and identified new problems if any.
- AR-T01–22 desk-check results and DS-SEC-10 budget fixture design review; label **tests NOT EXECUTED**.
- Future conditions explicitly separated: schema/backend implementation GO; runtime/mock/real corpus grounding tests; privacy/operator budget/support/proxy launch gate. No inferred Corpus Freeze or real-source readiness from document checks.
- No automatic merge or code from reviewer. If changes are needed, submit one consolidated correction list with acceptance criteria; leave source contracts unchanged.

## 6. Pasteable initial task for an independent new project chat

Ты независимая Architecture Acceptance Review Session R2 проекта «DS-консультант». Проведи полный независимый Acceptance Review исправленных контрактов DS-EC-02–05 в существующем Draft PR #1 UkWood/ds-cosult. Сначала проверь Git HEAD, указанный в финальном handoff Architecture Session A, и читай все документы строго по этому неизменному commit SHA. Прочитай docs/handoffs/DS-EC-02-05-R2-INDEPENDENT-ARCHITECTURE-REVIEW-HANDOFF.md, исходный DS-EC-AR-01, независимый R1 findings receipt, авторский R2 correction report и все четыре контракта. Проверь R1-CR01–06, все исходные 4 BLOCKER/8 IMPORTANT/2 MINOR, AR-T01–22 и новые DS-SEC-10 бюджетные сценарии. Обязательно учти утверждённое владельцем решение A: P1/P2 блокируются по глобальному оплаченному USD-бюджету, а проверенный локальный P0 доступен при полном соблюдении других ограничений. Не доверяй заявлениям автора исправлений. Дай единый аргументированный PASS или CHANGES REQUESTED и полный консолидированный список замечаний. Никаких Merge, кодирования, платных DeepSeek API, production, Corpus Freeze, изменений NEW RAG или сайта «Сатурн».

## 7. Immutable governance boundaries

- Existing Draft PR #1 ONLY, no Merge, no new PR or implementation.
- DeepSeek paid DS-QV-01 prior owner GO 6/6 **exhausted**.
- No new paid API calls; NO DS-02 coding, production or Corpus Freeze.
- NEW RAG UkWood/LLM-RAG-chat-bot is independent and untouched.
- UkWood/Saturn-Main-Site is READ-ONLY; never write there.
- Real PDF source custody/benchmark GT remain incomplete: earlier reports state 3/12 byte-pinned PDFs, 0 expert-approved Ground Truth.
- Independent R2 acceptance does not itself authorize pilot, paid API, code or merge.
