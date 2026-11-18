# DS-ARCH-BASELINE-01 — Owner-Accepted Architecture for Restricted Experimental Coding

**Date:** 2026-11-18  
**Status:** **OWNER ACCEPTED — ARCHITECTURE BASELINE FOR RESTRICTED EXPERIMENTAL IMPLEMENTATION**  
**Owner directive:** stop iterative independent reviews, record all current project decisions in GitHub, **MERGE existing Draft PR #1 into main**, move to limited coding and empirical hypothesis testing on two specific Saturn entities.  
**Repository:** `UkWood/ds-cosult`; architecture source PR #1 `docs/ds-01c-benchmark-memory`  
**Last R4 review source HEAD before owner decision:** `0026ff04583a8047b0521c7f53ac2aa20523e161`  
**Merge commit SHA:** GitHub PR #1 merge result is the immutable historical reference; do not guess it before merge.  
**Approved implementation target:** restricted LOCAL experiment, **not production/pilot offered to public visitors**.

## 1. Decision, supersession and meaning of "accepted"

The owner explicitly decided that **DS-EC-02–05 as an architectural direction are sufficient to begin restricted experimental coding**, subject to mandatory R4-CR01 implementation clarification (§3). The owner has **closed the rolling independent architectural review cycle**. No separate R5 acceptance loop is a prerequisite for the scoped developer task. This is a governance override of older documents saying "no DS-02 coding/no merge"; those historical documents/review decisions remain immutable evidence of past state and may not be silently rewritten.

**Do not misstate this as:** a factual grounding-quality PASS on real Saturn sources, a runtime security/privacy acceptance, a complete source/PDF corpus freeze, live paid API authorization, public production release, or a waiver of failure-safe behavior.

**Review trace preserved:** DS-EC-AR-01 original 4 BLOCKER/8 IMPORTANT/2 MINOR; independent R1/R2/R3 reports and corrective cycles; R4's **R4-CR01** has been accepted as a controlled implementation requirement (NOT an independently verified doc-level PASS). R3 §13.1.1 deterministic FinalStatus/ReasonCode reducer remains the normative prior specification, with §3 below resolving the remaining timing/authority ambiguity. Later completed coding verification may prompt bounded new implementation requirements; **do not restart independent architecture reviews for every local issue**.

## 2. Architecture baseline: what Codex must preserve

- **Entity-Centric RAG:** stable canonical `Entity` identity, version/variant qualifiers, `Fact`, `Relation`, `EvidenceRef`, `SourceBundle`, source/coverage and eligibility proof; hierarchical entity dossiers, local source index, deterministic fact/reference selection where possible.
- **Verifiability:** source field/path or reviewed PDF physical page + exact locator/bytes hash; no invented technical characteristics; full relevant eligible ledger conflict scan, not only the LLM's top-K excerpts; an unindexed PDF does not prove a fact is absent.
- **Answer:** `QuestionNeed` → `NeedResolution` → validated `VerifiedClaim` for supported technical Fact/Relation, separate metadata-only `DocumentReference`, source-attributed non-established `ConflictPosition`; server-owned `FinalStatus`, `ReasonCode` and per-need diagnostics. Deterministic renderer, **no unchecked LLM rewrite**.
- **Model:** direct official DeepSeek API, intended non-thinking `deepseek-flash` optional route; no vendor-native browsing/search/files/paid tools in first local pilot; **0 or at most 1 paid model POST per accepted visitor turn**, never P1 then P2. Whole serialized input **≤10,000 tokens**, output **≤450 tokens**, entire visitor text **≤1,200 Unicode characters**, request body **≤8KiB**. Provider-generated data can suggest an interpretation or select existing evidence **but does not certify source truth**.
- **Security/cost:** no public anonymous registration; one active anonymous chat/IP when public policy applies, 15m technical memory expiry, 30m series reset, 20 accepted visitor questions/IP/operator day including local P0, Q6–Q10 progressive cooldown and Q11 support handoff; controlled USD day/month reserve with crash-safe request-id deduplication, staff-only 30-day private Q/A/IP/UTC audit if traffic admitted. For *restricted loopback-only experiment*, public-IP deployment is expressly **OUT OF SCOPE** and policies must be modeled/tested offline without claiming internet-safe implementation.
- **DS-SEC-10 owner Option A:** global **paid DeepSeek USD** exhaustion prohibits new paid P1/P2 **before admission and question debit**, but approved source-verified entirely local **P0** can answer within independent IP/day/series/CPU/concurrency/source-proof/audit guards; P0 counts 1 question, 0 paid calls. Cached raw LLM prose never qualifies as P0. Non-monetary safety breaker may stop all.
- **Privacy:** no secrets, raw personal conversations, private IP logs, local paid API keys, unapproved GT or original proprietary data committed to the PUBLIC GitHub repository. Private runtime data must be local ignored storage with retention / purge tests.
- **Source trust:** read-only `UkWood/Saturn-Main-Site`, owner-declared trusted site/PDF sources, version pinned. The primary pilot injection threat is user-origin Goal Hijacking. No cross-project implementation borrowing from NEW RAG without separate owner GO.

## 3. R4-CR01 — MANDATORY implementation clarification, owner accepted

**Exact authoritative owner statement:**
> «При ADMITTED фиксируется исходный вопрос и его контекст. После P1 сервер окончательно формирует и проверяет полный набор QuestionNeeds. Затем набор фиксируется до итоговой проверки и формирования ответа. Зависимости устанавливаются по проверенным источникам до вычисления FinalStatus. Ни P1, ни P2 не могут самостоятельно исключить обязательную часть исходного вопроса.»

**Required operational ordering:**

1. **Pre-admission:** validate canonical IP/session, user-length/body, domain and route feasibility. Paid path full token/USD budget preflight happens BEFORE atomic admission debit. This is unchanged from DS-EC-03/04/05. Server identifies a provisional **immutable coverage of the original submitted technical ask**, including independently identified conjuncts, comparisons and referenced entities; uncertainty is explicit, not erased.
2. **At `ADMITTED`:** durably pin `original_question_exact` (private, no public GitHub), `request_id`, the source-context snapshot (`DialogState`/active comparison referents), `SourceBundle` and policy/dictionary revisions, source-original intent/coverage anchors and accepted-turn accounting. Earlier account and ID fences remain atomic. This is not yet permission to freeze a final need list.
3. **After optional P1:** P1 returns `QuestionInterpretationPlan` only. The **SERVER**, not P1, constructs and validates **the complete final `QuestionNeeds`**, by reconciliation with all required spans/clauses of the original question and pinned context. Missing/inapplicable required parts must remain **explicit unresolved needs**, never silently dropped. If server cannot prove full coverage, give a safe clarification/needs_support, not a deceptively complete answer.
4. **Freeze:** persist a canonical ordered immutable `QuestionNeeds` set and its `question_needs_hash` once, **after P1 if invoked** or after deterministic server interpretation if P1 is not used, and **before** source proof verification, answer-plan selection and final answer assembly. All subsequent operations use that exact hash. No LLM may change it, even by omitting a need from its own output. This freeze is a separate stage from admission, not a replacement for the already pinned original question/context.
5. **Evidence-derived dependencies:** server forms and verifies need-to-need dependency edges from approved pinned source evidence/validated entity variant scope and already pinned dialogue referents **before** applying DS-EC-05 §13.1.1 `FinalStatus` reducer. P1/P2 text alone cannot establish prerequisites, compatibility, source identity or valid inference. An unresolved prerequisite invalidates dependent publication unless independently proven.
6. **P2 is post-freeze only:** P2 may choose/order candidate IDs from a server-supplied EvidencePacket but cannot create/delete/reclassify required needs or change the frozen hash. Any omission, mismatched hash, invented Fact/Relation, cross-variant source, or malformed plan is rejected/handled as explicitly unresolved, no second paid POST or ungrounded response.
7. **Invariant:** for every required part of the original user question there is at least one final QuestionNeed **or** a bounded documented unresolved coverage diagnostic that prohibits `answered`. A verified full `answered` requires *all original required intents* covered by satisfied need-specific objects and valid citations. All opaque failures have explicit per-need diagnostics. All planned paths must be testable with fake P1/P2 and no paid network.
8. **Replays/continuations:** same idempotency key retains the original question/context and eventual frozen need set; user follow-up is a NEW admitted turn with its own separately pinned question and reference snapshot; memory expiry or bundle change does not silently rewrite old required needs.

**Precedence:** This R4-CR01 owner clarification controls *when and how* `QuestionNeeds` are finalized. If earlier explanatory prose implies that QuestionNeeds is frozen already at ADMITTED or can be model-reduced, that reading is superseded. All other DS-EC-02–05 proof rules, expense guards and §13.1.1 status/reason ranking remain unchanged.

## 4. Approved first implementation scope

**DS-PILOT-01:** build a local runnable, evidence-grounded conversational proof of concept containing **exactly two top-level Saturn objects**:
- Device **БКД-ПК-RF.2**;
- System **СЛДКС-1**.

The baseline source inventory, exact pinned site files/SHAs and PDF limitations live in `docs/corpus/DS-PILOT-01-TWO-ENTITY-SOURCE-SCOPE.md`.

The self-contained developer task is **`docs/tasks/DS-CODEX-01-TWO-ENTITY-LOCAL-PROTOTYPE.md`**. It is owner-authorized to create code in a **NEW isolated feature branch and Draft PR based on main AFTER PR #1 merge**, with no merging of that feature PR without separate owner decision. Testing must be **locally reproducible offline**, direct paid DeepSeek API default disabled, source statement checks deterministic. Implement only enough of the architecture to falsify the RAG hypotheses; log unsupported complete-production features rather than claiming they exist.

## 5. Exit criteria / next gates

1. The pre-coding architectural/documentary baseline and code assignment are committed in the existing PR #1 and owner-authorized **merged into main**.
2. Codex starts after merge from verified exact main commit in a separate coding session and creates a new coding Draft PR; **do not code on the merged documentation branch**.
3. Codex delivers CLI and loopback web demo, exactly two entity source dossiers, precise canonical source citations, local answer/clarification/abstention, frozen mixed needs with R4-CR01 tests, fake provider tests and full run instructions.
4. Owner/Architecture Session A reviews **working pilot outputs and actual tests** rather than reopening independent architecture review cycles. Optional paid DeepSeek tests require a **new explicit owner GO and numeric spending cap**, none is granted by this document.
5. Real PDF ingestion, 12-document corpus custody/GT completion, open public registration/IP proxy/security deployment, operational operator USD caps and production remain **later separate decisions**.

**Historical non-approval statements** in prior review tasks/PR description document prior phases; they do not override this **later owner explicit APPROVED/MERGE/CODEX POC** decision. Prior source content quality remains subject to real verification, not "approved Ground Truth".
