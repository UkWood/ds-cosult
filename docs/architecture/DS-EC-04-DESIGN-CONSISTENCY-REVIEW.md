# DS-EC-04 — Independent Design Consistency Review v0.1

**HISTORICAL PRE-R1 DESIGN REVIEW.** This report documents what was checked BEFORE the consolidated review and subsequent owner-authorized v0.2 corrections. Its earlier PASS/REVIEW NOTES must **not** be read as independent acceptance of the new corrected contracts. Current authoritative review baseline: `docs/acceptance/DS-EC-02-05-CONSOLIDATED-ARCHITECTURE-ACCEPTANCE-REVIEW.md` (CHANGES REQUESTED). Author's R1 correction trace: `docs/acceptance/DS-EC-02-05-R1-CONSOLIDATED-CORRECTIONS-REPORT.md`. **A separate reviewer/session must decide whether R1 passes.**


**Recorded:** 2026-11-18  
**Review target:** `docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md`  
**Status:** **ARCHITECTURE DOCUMENTATION REVIEW — PASS WITH REVIEW NOTES; NOT AN IMPLEMENTATION ACCEPTANCE**  
**Review performed:** read back created GitHub file in existing Draft PR #1 and checked mandatory design invariants, test table coverage and consistency with earlier accepted requirements.

## 1. Evaluated invariants

| Gate | Review finding |
|---|---|
| Canonical referent and version | PASS — typed `focus_entity_id`, exact variant, stable ordered comparison anchors; no guessed referent on ambiguous pronoun |
| Legitimate conversational changes | PASS — explicit question/entity/attribute correction can update **intent** but cannot change source truth |
| Direct Goal Hijacking | PASS AS DESIGN — fake system roles, visitor-declared IP68/compatibility and instruction override are never accepted as backend policy or Facts; model runtime behavior not tested |
| Prior answer truth boundary | PASS AS DESIGN — only backend-verified Fact/Relation IDs enter state; raw assistant prose and user-proposed facts have no fact authority |
| Source consistency | PASS — one SourceBundle per turn, deliberate invalidation/re-resolution on revision or policy change |
| Session isolation | PASS AS DESIGN — private DialogState by authenticated anonymous session/active IP lease; different cookie at same IP cannot see old dialogue |
| 15m IP lease vs 30m series | PASS AS DESIGN — expiry of technical memory at 15m does not reset IP-based 30m progressive series or day quota |
| 20 accepted visitor questions/IP/day | PASS AS OWNER-APPROVED DS-SEC-09 POLICY — local no-call answers count; actual paid model POSTs counted independently |
| Private logs | PASS AS DESIGN — accepted full Q/A + IP/UTC audit isolated to staff-only 30-day store; never GitHub or another visitor |
| One in-flight call and atomic updates | PASS AS DESIGN — CAS `context_revision`, exclusive in-flight/lease fencing and idempotency; no automatic provider retry after uncertain spending |
| 10,000 input / 450 output | PASS — owner-approved full-context cap, no uncontrolled past-turn replay, shortest evidence-sufficient source packet |
| Adversarial and benign tests | PASS ON COVERAGE — **30 named, synthetic, offline test scenarios**, not executed |
| Independence | PASS — no NEW RAG changes, no site write, no actual DeepSeek request, no new PR or merge |

**Scope:** the review attests the proposed document **states** these safeguards. It does NOT prove that code, IP resolution, tokenizer counting, source proof, claim gates or DeepSeek itself enforce them. No false claim of Ground Truth acceptance or deployed policy is made.

## 2. Important design choices still open (not blockers for documentation-only design)

**RESOLVED — MEM-REVIEW-01 by owner DS-SEC-09:** full active technical dialogue memory is cleared after **15 minutes** of inactivity even if the same cookie returns. IP-based 30-minute series and 20-question daily allowance persist independently. Keep privacy/no-leakage implementation tests.

**RESOLVED — MEM-REVIEW-02 by owner DS-SEC-09:** hard **20 accepted visitor questions/IP/operator-calendar day**, including local and cache replies; actual provider POST attempts and dollar usage are separate counters. No double counting on idempotent replay. DS-SEC-09 supersedes the former billable-only interpretation.

**IMPORTANT — MEM-REVIEW-03: atomicity and response/audit order.** `CAS` on memory revision alone is insufficient to prevent parallel provider POSTs or guarantee audit completeness: acquisition of shared IP in-flight lease and cost reserve **must precede** provider dispatch. Use explicit request-state transitions and fencing/timeout behavior in coding design, including backend crash after POST, return response before audit commit, and request replays.

**IMPORTANT — MEM-REVIEW-04: natural language versus independent fact verification.** The single-call policy may use its only model inference for understanding a complex anaphoric query; final answer is then rendered deterministically. Acceptance tests must evaluate user-facing quality, not just role safety, and distinguish clarification from over-refusal.

**IMPORTANT — MEM-REVIEW-05: SourceBundle update timing.** If a new approved corpus revision is published mid-turn, the active turn remains pinned to its starting bundle and must not silently switch to new facts before rendering. Subsequent turns may re-resolve under the new bundle with explicit migration; avoid dangling citations.

**IMPORTANT — MEM-REVIEW-06: session activity definition.** Lease refresh should be tied to verified same-session activity, not unbounded automated browser keepalives or requests blocked solely due to malicious/over-limit inputs. Need testable exact inactivity clock semantics and 15m in-flight extension behavior.

**IMPORTANT — MEM-REVIEW-07: privacy/retention prerequisites.** Full IP and Q&A are potentially personal data. Owner accepted private 30-day default, but lawful basis, exact employee permissions, deletion/backup handling, trusted proxy topology and visitor notice must pass separate launch review. No real visitor data in public test fixtures.

## 3. Proposed future Acceptance gates

At eventual coding preflight (requires owner GO):
1. Fake-clock tests for 14:59 / 15:00 IP lease boundary, 29:59 / 30:00 question-series boundary, next company-calendar midnight, with daylight-saving transitions under configured IANA timezone.
2. Synthetic dialogue tests: compare A/B, `а у второго?`, swap to C/D, two ambiguous masculine devices, entity revision correction, source conflict, fake user facts.
3. Concurrency: two tabs same cookie and different cookies sharing one IP, simultaneous CAS, in-flight provider timeout and crash recovery, idempotent repeated client request ID.
4. Source migration: old bundle at turn entry, new bundle published mid-call, next-turn safe re-resolution and citation invalidation; no source mix.
5. Security: forged `system` payload, false `мы уже доказали`, direct goal override, legitimate `забудь предыдущую тему`, no raw-text quote promoted to source or privileged role.
6. Provider-free test: mocked DeepSeek / fake tokenizer input 9,999; 10,000; 10,001 tokens, output max 450, no paid calls for cooldown, hard-day lock or local verified answer.
7. Logging privacy: accepted actual final response (not only model candidate), original question, IP/UTC privately recorded, 30-day expiry and no cross-session leakage; blocked inputs logged minimally.

**No tests have been executed**, no new paid DeepSeek GO exists (DS-QV-01 exhausted 6/6). Real site/PDF GT readiness remains blocked in prior project status (0 expert-approved benchmark GT; only 3/12 PDF bytes SHA-pinned by owner-reported WSL prior evidence).

## 4. Recommendation and governance

**Recommendation:** carry DS-EC-04 forward as an **architecture candidate** with MEM-REVIEW-01/02 **resolved by DS-SEC-09 owner decision**, then draft DS-EC-05 atomic-claim verifier and controlled rendering modes. Do not authorize implementation implicitly through document creation.

This review is a limited documentation assessment, not proof that DeepSeek cannot be goal-hijacked or that memory/accounting concurrency is safe in executable code.

Existing `UkWood/ds-cosult` Draft PR #1 ONLY; no Merge, no DS-02 implementation, no Corpus Freeze, no production, no live API requests, no NEW RAG writes, and `Saturn-Main-Site` remains READ-ONLY.
