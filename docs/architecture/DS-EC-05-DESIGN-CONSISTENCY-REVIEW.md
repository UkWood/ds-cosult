# DS-EC-05 — Independent Architecture Design Consistency Review

**Reviewed:** 2026-11-18  
**Status:** **DOCUMENTATION CONSISTENCY PASS WITH REVIEW NOTES — NOT OWNER ACCEPTANCE AND NOT CODE TEST PASS**  
**Reviewed artifact:** `docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md`  
**Related owner decision:** `docs/decisions/DS-SEC-09-OWNER-APPROVED-MEMORY-AND-QUESTION-QUOTA.md` — 15m memory expiry and 20 accepted visitor turns/IP/operator-day including zero-model local/cache answers.

## 1. Independent read-back checks

The created file was read back from the same existing Draft PR #1 branch, not merely assumed written. Structural inspection found **12 design chapters** and **45 proposed synthetic offline acceptance scenarios (EC5-01..EC5-45)**, not executed.

| Criterion | Documentation verdict |
|---|---|
| Compatibility with DS-EC-02 | PASS — explicit Entity/Fact/Relation and source-bound EvidenceRef IDs; no inferred compatibility |
| Compatibility with DS-EC-03 | PASS — frozen EvidencePacket and untrusted structured CandidateAnswerPlan; 0/1 provider call |
| Compatibility with DS-EC-04 | PASS — typed DialogState and server policy; visitor corrections cannot mutate trusted corpus facts |
| Owner DS-SEC-08 input allowance | PASS — entire input <=10,000 tokens, max output 450, no fill-to-max requirement |
| Owner DS-SEC-09 daily quota | PASS — 20 admitted visitor questions/IP/operator-day including local/cache answers; provider POST attempts and USD separately counted |
| Owner DS-SEC-09 memory expiry | PASS — 15m active memory invalidation, 30m IP series and day quota independent |
| Evidence binding | PASS AS DESIGN — website canonical route/commit/blob/field, PDF URL/byte SHA/parser/physical page |
| Missing versus negative/source error | PASS — distinct `insufficient_evidence`, `scope_not_indexed`, `source_unavailable`, `processing_error`; no invented negative property |
| Conflicts versus versions | PASS — same applicable scope conflicting claims preserved; two variants not falsely combined |
| Verification integrity | PASS AS DESIGN — model-selected identifiers rechecked for fact applicability and specific citation-to-claim support; verifier internal errors not disguised as ordinary reject |
| Status and renderer | PASS AS DESIGN — answered/partial/clarification/needs_support/error/out_of_scope; server-controlled source-cited templates and no generative post-gate rewrite |
| Direct visitor Goal Hijacking | PASS AS DESIGN — fake roles, fabricated IP class and "omit citations" cannot create trusted facts or disable final server gate |
| Cost and audit | PASS AS DESIGN — max one paid POST; server budget reservation before dispatch; actual displayed answer + full accepted question/IP/UTC in private staff-only 30-day log |
| Source-readiness honesty | PASS — no claim that real Saturn corpus is frozen or verified |

**Interpretation:** the *documentation* specifies intended safeguards. This review provides **no evidence** that an implemented verifier is correct, that DeepSeek will always follow a schema, or that synthetic/real technical answers are grounded in production.

## 2. Consolidated review notes

**IMPORTANT EC5-CR-01 — typed source coverage for "not specified".** Backend needs a precise definition of the inspected source set and extraction completeness; absence in one snippet is insufficient to claim a device property is not stated in all Saturn documentation. `scope_not_indexed`, `source_unavailable` and `processing_error` must not be collapsed into `insufficient_evidence`. Include explicit test of partial PDF ingestion.

**IMPORTANT EC5-CR-02 — verifier completeness vs extraction quality.** A correctly matching Fact ID and CitationBinding may still be wrong if extraction selected the wrong PDF table row, qualified revision or diagram element. Implement an independent source extraction/locator integrity gate and expert-reviewed validation fixtures before declaring production fact-grounding reliability.

**IMPORTANT EC5-CR-03 — final answer naturalness under no-prose policy.** Server-only templates improve verifiability but could make technical explanations awkward, particularly multi-need comparison and conditions. Offline user-facing readability tests should be part of acceptance. Any future flexible LLM prose mode must preserve claim-specific proof rather than asserting unverified text.

**IMPORTANT EC5-CR-04 — atomic admission/audit/outcome transaction.** Counting each accepted question once, each provider POST separately, cost-reserving before dispatch, committing memory CAS and persisting actual displayed output require explicit recovery semantics. Do not display "answered" before a required audit record is safely stored; never auto-retry an uncertain paid POST.

**IMPORTANT EC5-CR-05 — source snapshot migration in long requests.** Source bundle is pinned for each turn. A new document revision arriving during inference cannot silently replace a source locator or value; next turn re-resolves. Test stale citation invalidation and version-specific conflicts.

**IMPORTANT EC5-CR-06 — operator configuration / legal launch gates.** Real IANA day-reset timezone, support contacts, global day/month budgets, trusted proxy chain and privacy basis/notice/staff audit access are not provided and must not be guessed. Full IP+dialogue logging can contain personal data even without visitor registration.

**IMPORTANT EC5-CR-07 — review statuses must distinguish evidence failure from technical uncertainty.** Need-to-final mapping must be made executable, including `partial` when some claims supported and another source read fails. Error must never be translated into "device property not specified" by rendering.

**MINOR EC5-CR-08 — source navigation case.** `document_reference_only` needs a metadata-only navigation template that cannot be mistaken for proof of any other technical assertion. This should be covered by the future JSON schema and test fixture.

All notes are **design/implementation acceptance gates**, not discovered code defects (no code exists). They do not prevent drafting the next owner architecture review.

## 3. Reviewable contracts and deterministic gates

The design has explicit conceptual contracts `CandidateAnswerPlan`, `VerifiedClaim`, `CitationBinding`, `VerifiedAnswerResult`; statuses and deterministic server-owned rendering modes; an 11-stage G0–G10 acceptance chain before displaying source-backed facts; 45 distinct prospective tests including forged roles, invented facts, model/tool behavior, partial corpus, conflict, versioned relations, PDF page provenance, 10,000/10,001 input boundary, 15m expiry, 30m series, 20 accepted turns and global USD breaker.

A future coding assignment MUST transform this design into a versioned executable schema with negative/positive unit and integration tests. It must not replace the verifier with a model self-review, substring-only check, or "reasonable sounding" generated answer.

## 4. Owner approval and next gate

- **Owner-accepted in this step:** two DS-EC-04 open policy decisions via DS-SEC-09.
- **Proposed, not yet owner-approved as final implementation contract:** DS-EC-05 detailed verifier and renderer specification.
- **Candidate next architectural milestone:** consolidate DS-EC-02..05 into one scoped first-pilot baseline with open issue resolutions, then request explicit owner acceptance before coding.
- **Corpus limitation:** project reports 3/12 local PDF SHA pins, 0 expert-approved benchmark Ground Truth, P4/P5 claim review incomplete; do not freeze or call full corpus ready.

**Governance:** no runtime implementation, new paid DeepSeek (DS-QV-01 consumed 6/6), Merge, DS-02, Corpus Freeze, production or writes to NEW RAG/read-only Saturn-Main-Site.
