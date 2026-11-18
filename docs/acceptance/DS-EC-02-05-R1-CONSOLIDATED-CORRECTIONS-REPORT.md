# DS-EC-AR-01 — R1 Consolidated Contract Corrections Report (AUTHOR HANDOFF)

**Date:** 2026-11-18  
**Repository/PR:** UkWood/ds-cosult, existing Draft PR #1, branch docs/ds-01c-benchmark-memory  
**Change scope:** DS-EC-02–05 **architecture documentation only**, no executable backend, paid DeepSeek requests or deployment.  
**Baseline prior to corrections:** ed0b2b93b90c04b975eb9c024a40c4f312e2ce61 (consolidated review filed after baseline).  
**Original independent review:** docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md — CHANGES REQUESTED (4 BLOCKER, 8 IMPORTANT, 2 MINOR).  
**AUTHOR RESULT:** REMEDIATION SUBMITTED FOR NEW INDEPENDENT REVIEW. **NOT SELF-ACCEPTED**, no claim that the architecture has passed R1.

## 1. Exact files corrected

- docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md — normative v0.2 §8, SourceBundle required manifest/dictionary/policy IDs; source-coverage and eligibility.
- docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md — normative v0.2 §10, unpaid domain screen, P0/P1/P2 routing, pre-dispatch provider guard and QuestionInterpretationPlan.
- docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md — normative v0.2 §14, crash-safe request FSM, exact 15-minute memory isolation, source snapshot cutover and private audit.
- docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md — normative v0.2 §13, common need/proof/final status mapping, proof-to-claim citation binding, early P1 dispatch handling, controlled templates.
- docs/acceptance/DS-EC-02-05-OFFLINE-R1-FIXTURE-CONTRACT.md — design-only AR-T01..22 with expected quota/provider/status evidence; **nothing executed**.

Earlier sections labeled v0.1 remain as historical explanation. If they conflict with newer *normative v0.2* clauses, the new clauses explicitly take precedence. This must be independently assessed for ambiguity rather than presumed safe.

## 2. Consolidated finding → correction trace (4 BLOCKER / 8 IMPORTANT / 2 MINOR)

| Finding | Remediation and exact principal location | Author disposition |
|---|---|---|
| **CR-B01** coverage for “not specified” and hidden conflict | DS-EC-02 v0.2 §8.1 SourceCoverageReceipt; DS-EC-03 v0.2 §10.4; DS-EC-05 v0.2 §13.1–13.2. Source scope requires approved source manifest and per-source bytes/parser/index receipt, conflict scan over ALL applicable ledger claims (not top-K prompt). | **CORRECTION PROPOSED — R1 review required** |
| **CR-B02** proof eligibility across source, Fact, Relation | DS-EC-02 v0.2 §8.2 SourceEligibilityPolicy v0.2, site/PDF table/diagram, negative and Relation matrix; DS-EC-05 §13.2 claim-to-locator check. Benchmark expert GT explicitly separate. | **CORRECTION PROPOSED — R1 review required** |
| **CR-B03** G2 early provider POST bypassing G5 | DS-EC-03 §10.1–10.3, shared ProviderDispatchGuard preflight for P1 and P2 and distinct QuestionInterpretationPlan vs CandidateAnswerPlan; DS-EC-05 G0/G2/G5 + §13.3. Complete <=10k input, <=450 output, one attempt and money/lease reserve prior POST. | **CORRECTION PROPOSED — R1 review required** |
| **CR-B04** G0 domain recognition vs model classification and debit | DS-EC-03 §10.1–10.2 unpaid conservative domain screen and P0/P1/P2, DS-EC-04 §14.1 FSM, DS-EC-05 G0. Unrecognized/out-of-domain → local clarification/redirect without admission; paid route token/cost preflight BEFORE atomic accepted-turn+provider+USD debit, no unaccounted paid classifier. | **CORRECTION PROPOSED — R1 review required** |
| **CR-I01** crash-safe admission, POST, audit and recovery | DS-EC-04 §14.1, DS-EC-05 §13.4; staging final Q/A/IP/UTC before delivery, uncertain bill holds reserve, idempotent replay and exclusive IP fencing. | **DESIGN ADDRESSED; executable crash tests pending** |
| **CR-I02** enum/status mappings and partial/error semantics | DS-EC-02 §8.3 NeedResolution v0.2; DS-EC-05 §13.1 precise typed mapping, precedence including mixed partial and error; source absence not mistaken for parser failure. | **DESIGN ADDRESSED; schema tests pending** |
| **CR-I03** stable model/variant identity and bundle migration | DS-EC-02 §8.3 identity map, stable IDs ≠ URLs; DS-EC-04 §14.2 in-flight bundle pin and next-turn revalidation/cache invalidation. | **DESIGN ADDRESSED; fixtures pending** |
| **CR-I04** attribute types/units/conditions and relation semantics | DS-EC-02 §8.3 versioned dictionaries, decimal/inequality/tolerance/enum/negative and direction/transitivity; DS-EC-05 §13.2 checks. | **DESIGN ADDRESSED; executable unit tests pending** |
| **CR-I05** understandable natural-language response | DS-EC-03 §10.5 and DS-EC-05 §13.2 controlled modes + explicit human readability/false-refusal assessment with no unchecked LLM prose. | **DESIGN ADDRESSED; human quality acceptance pending** |
| **CR-I06** global USD breaker effect on free local answer | DS-EC-03 §10.5 and DS-EC-05 §13.3 specify recommended policy: block P1/P2 paid, allow fully local P0 within all IP/day/cooldown/CPU constraints. **Owner-specific choice remains to be confirmed** rather than falsely treated as an existing binding DS-SEC-07 rule. | **PROPOSED CHOICE — independent reviewer must flag owner confirmation if necessary** |
| **CR-I07** real source/benchmark readiness | DS-EC-02 §8.1/8.2 + fixture contract require real source inventory, byte-pinned approved PDF/pages and distinct expert GT gate. Existing reports: 3/12 PDF byte-pinned locally, 0 expert-approved benchmark GT, P4/P5 claim review incomplete; real corpus cannot be declared ready from architecture-only edits. | **ARCHITECTURAL LAUNCH GATE DEFINED; CORPUS STILL NOT READY** |
| **CR-I08** privacy and deployment configuration | DS-EC-04 §14.3 + DS-EC-05 §13.4 preserve 30-day private IP/Q/A audit, user notice/lawful basis, trusted proxy, exact IANA operator day-reset timezone, verified support contacts, encryption and actual global USD budgets. No invented values. | **ARCHITECTURAL LAUNCH GATE DEFINED; OPERATOR CONFIG STILL PENDING** |
| **CR-M01** stale historical proposal/pending wording | Explicit v0.2 precedence labels, DS-SEC-07/08/09 normative authority; older individual review documents to be labeled historical pre-correction. Chronological audit and owner wording never rewritten. | **DOCUMENT STATUS CLARIFIED** |
| **CR-M02** stable wire type and schema naming | DS-EC-02 §8.3 canonical names, required schema/dictionary revisions; DS-EC-03 §10.3 QuestionInterpretationPlan; DS-EC-05 §13.1 final mapping. | **DESIGN ADDRESSED; executable schemas deferred until coding GO** |

## 3. Critical implementation invariant found during author consistency check

**Budget failure must NOT use one of the visitor's 20 accepted daily questions.** A paid P1/P2 path therefore has TWO stages:
1. UNDEBITED route eligibility, complete prompt/model token count and global-dollar cost preflight (no provider POST).
2. ONE ATOMIC serializable commit of **accepted visitor-turn debit + request ID + one provider POST attempt token + global USD reserve + exclusive IP in-flight fence**, followed by exactly one possible API POST.

For P0 local, only accepted visitor-turn debit and request/in-flight guard are committed. A token/cost denied paid path remains DENIED, 0 accepted turns and 0 provider calls. Once admitted, later source/verifier failures do not retroactively refund; no duplicate debit on idempotent retries. The current v0.2 corrected contracts contain this invariant. An independent reviewer should look for **any older contradictory sentence** with precedence insufficiently clear.

## 4. Out-of-scope for documentary corrections

- Actual model token estimator/DeepSeek billing reconciliation: no valid new paid GO (prior DS-QV-01 6/6 consumed); fixed-rate $0.00354 example is NOT provider-guaranteed budget maximum.
- Full site/PDF integration or benchmark statistical conclusions: incomplete source custody and expert GT, no Corpus Freeze.
- Public pilot/production: operator IANA timezone, support contacts, daily/monthly USD budget, trusted reverse proxy, privacy legal basis/staff log access must be supplied.
- Code, database/schema implementation, executed unit tests, server deployment, merging PR or changes to separate NEW RAG and read-only Saturn site: NOT PERMITTED.
- The author **cannot independently accept its own changed contracts**; a new architecture-review session must start from frozen PR head and verify all four blockers, important dispositions and fixture proof clauses.

## 5. R1 review ask

Do not accept the author report at face value. Read both the original CR-B01..M02 review and the corrected files independently. Demand exact cross-contract consistency and check AR-T01..22 against written behaviors without claiming execution. Test these additional logical cases explicitly:
- paid route budget failure **before admission** → 0 accepted turn, 0 provider;
- source coverage receipt missing but model confidently proposes a fact → no unsupported absence/complete answer;
- one provider interpret P1 followed by requested P2 → P2 blocked;
- two source facts conflict outside model packet → conflict preserved;
- incorrect PDF row on correct physical page → ineligible;
- proxy/IP lease and 15m/30m/day clocks remain independent;
- malformed/false user roles never become system roles or verified facts.

**Review verdict is pending**, no automatic PASS based on author corrections.
