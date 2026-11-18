# DS-EC-02–05 — R1 Independent Architecture Acceptance Handoff

**Prepared:** 2026-11-18, DS-консультант project  
**Status:** AUTHOR HANDOFF, **NOT INDEPENDENT ACCEPTANCE**  
**Repository:** UkWood/ds-cosult  
**Only branch / PR:** docs/ds-01c-benchmark-memory / Draft PR #1  
**Reviewed original baseline HEAD:** ed0b2b93b90c04b975eb9c024a40c4f312e2ce61  
**Current corrected/frozen review HEAD:** obtain EXACT PR head SHA from the final creator handoff and verify through GitHub get_pr_info; use that **commit SHA as the ref** for all file reads. Do not use moving branch HEAD for evidence after review starts.

## Independent-review role

You are **Architecture Session R1 — reviewer only**, in a separate new conversation of the SAME ChatGPT project “DS-консультант”. You are **not** the author/coding agent, have no authority to merge or implement and must not modify the corrected contracts before rendering a verdict.

Your objective: critically test the author corrections to the four **architectural** contracts DS-EC-02–05, compared with the earlier independent review. The author is not allowed to mark its own corrections accepted. An unrelated conversation alone does not guarantee independence: **read original review and actual source files at frozen Git HEAD, verify proof for each item, and issue your own independent decision**.

## Required documents (retrieve from GitHub by exact frozen commit)

1. Original authoritative independent review: docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md (4 BLOCKER, 8 IMPORTANT, 2 MINOR).
2. Author's proposed corrections: docs/acceptance/DS-EC-02-05-R1-CONSOLIDATED-CORRECTIONS-REPORT.md — **not self-validating**.
3. Core corrected contracts:
   - docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md (v0.2 §8)
   - docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md (v0.2 §10)
   - docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md (v0.2 §14)
   - docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md (v0.2 §13)
4. New designed scenarios: docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md, AR-T01–22 **NOT EXECUTED**.
5. Accepted owner policy, not up for design reversal:
   - docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md
   - docs/decisions/DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md
   - docs/decisions/DS-SEC-09-OWNER-APPROVED-MEMORY-AND-QUESTION-QUOTA.md
6. docs/status/PROJECT_STATE.md, docs/history/ARCHITECTURE_LOG.md — governance/context, not substitutes for verified source contracts.

## Mandatory acceptance agenda

- **CR-B01:** can a verified SourceCoverageReceipt for entity/variant/attribute prove absent within a declared complete pinned source scope, not accidentally ignore off-top-K PDFs? Does conflict detection scan full source ledger independently of model packet?
- **CR-B02:** is runtime EvidenceEligibilityPolicy unequivocal for structured site fields, PDF text vs tables vs diagrams, negations and relations, including exact row/column/variant/unit and distinct benchmark expert-GT threshold?
- **CR-B03:** is ProviderDispatchGuard mandatory BEFORE any paid P1 early interpretation or P2 answer-plan POST, with full input ≤10,000 tokens, output ≤450, one attempt, disabled tools/thinking, money reserve and timeout no-retry? Is QuestionInterpretationPlan separate from CandidateAnswerPlan?
- **CR-B04:** can the server recognize domain eligibility without an unaccounted paid classifier, and are 20 accepted turns (including local), provider attempts, money reserves, IP in-flight and request-id idempotency **atomically** accounted? Very specifically: if a global-dollar/token preflight fails, it must reject **with zero visitor-turn debit and zero model calls**.
- **CR-I01..I08:** transaction crash states/audit order; versioned status mapping; stable entity IDs and snapshot cutover; unit dictionary/qualifiers; natural-language output quality; zero-call local policy under global USD breaker; source/PDF custody and independent GT; privacy/operator-only deployment configuration.
- **CR-M01..M02:** historical supersession labels, canonical type names and versioned schema/enum registry.
- **AR-T01..22:** for each intended test, cite exact clauses and whether behavior is normatively specified; do NOT claim these cases ran.
- Check **no new contradictions introduced** by append-only normative v0.2 clauses relative to earlier sections/gates. The reviewer may request inline consolidation if precedence notes are insufficient.

## Required output

One complete independent report in Russian:
- reviewed frozen commit SHA, each file's fetched Git blob SHA, policy baseline;
- **PASS / CHANGES REQUESTED** as verdict on **architecture documents only**; list each CR item BLOCKER/IMPORTANT/MINOR as PASS/OPEN/CONDITIONALLY DISPOSED;
- all newly discovered defects in **one consolidated review** with exact normative locations, minimal scope correction and acceptance tests; no piecemeal remarks if avoidable;
- clearly distinguish architecture review from executed backend tests, real source QA and production readiness;
- explicit next gate (owner accepts architecture → separate scoped offline coding GO → separate runtime verification; no Merge without owner approval).

If the reviewer publishes an acceptance report as a GitHub document, use the **existing Draft PR #1** only and only if owner authorizes reviewer documentation. Review may otherwise be delivered entirely in the new chat with findings and a PR comment, without altering source contract files.

## Boundaries

- Trusted site and PDF are owner-declared injection-free; threat under test is direct visitor Goal Hijacking. No broadened untrusted-source injection scope.
- Public consultant has no visitor registration; one active session/IP; 15m live technical memory expiry; 30m series reset; 20 **accepted user questions**/IP/operator calendar day including 0-call local answers; fixed progressive pauses; zero/one paid DeepSeek request/turn; ≤10k whole input / 450 output; 30-day restricted full Q/A/IP/UTC audit and operator-controlled global USD budget.
- DS-QV-01 paid GO **all 6/6 used**; no further paid DeepSeek calls without new explicit numeric approval.
- Source corpus **NOT READY**: owner reported 3/12 PDF bytes pinned and 0 expert-approved benchmark GT. A reviewed architecture is not Corpus Freeze.
- NEW RAG UkWood/LLM-RAG-chat-bot independent and untouched.
- UkWood/Saturn-Main-Site READ-ONLY.
- NO implementation DS-02, production, Merge, new PR, expanded model/tool scope or implicit new budgets.

## Ready-to-paste starting task for the new architecture chat

“Ты независимая Architecture Acceptance Review Session R1 проекта DS-консультант. Твоя задача — провести повторную полную независимую приёмку исправленных документов DS-EC-02–05 в существующем Draft PR #1 репозитория UkWood/ds-cosult. Сначала проверь актуальный HEAD PR и зафиксируй его неизменным для всех чтений, затем изучи документы docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md, docs/acceptance/DS-EC-02-05-R1-CONSOLIDATED-CORRECTIONS-REPORT.md, docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md, все четыре исправленных DS-EC-02–05 и решения DS-SEC-07/08/09. Не доверяй выводам автора исправлений: самостоятельно проверь закрытие четырёх BLOCKER, восьми IMPORTANT и двух MINOR, включая непротиворечивость платного preflight с подсчётом 20 вопросов/IP/сутки. Выдай независимый итог PASS или CHANGES REQUESTED, полный консолидированный список замечаний и аргументированные критерии закрытия. Никаких платных API-вызовов, кодирования, Merge, Corpus Freeze или изменений NEW RAG и сайта Сатурна.”

**Important:** The project files and corrected contracts are the source of this handoff; memory of a previous chat is not a substitute for reading actual exact GitHub files.
