# DS-EC-02/03 — Architecture Contract Consistency Check v0.1

**Date:** 2026-11-18  
**Status:** DOCUMENTATION COMPLETE / INTERNAL DESIGN CONSISTENCY REVIEW — **NOT OWNER ACCEPTANCE OR EXECUTABLE TEST PASS**  
**Reviewed scope:** two new source-verifiable Entity-Centric RAG architecture specifications; no code, no real Saturn source fetch, no paid API.
**Amendment recheck (2026-11-18):** Owner DS-SEC-08 changed complete input cap 3,000 → **10,000 tokens**, preserving max output 450, one-or-zero model calls and all source verification gates. The earlier documentation-only review concerned the original 3k policy; this updated review checks the amended 10k policy, cost reservation and offline boundary gates. No executable acceptance has occurred.

## Verified by reading back the GitHub branch documents

1. DS-EC-02 defines Entity, Fact, Relation, SourceBundle, EvidenceRef and query-time NeedResolution, with immutable source revision and scoped identity.
2. Site provenance requires exact manifest canonical URL, pinned commit/blob/content hashes and field source path. PDF provenance requires approved URL, bytes SHA256, version and physical page; missing link is a blocking validity error rather than a valid citation.
3. Missing attributes are **typed unknown NeedResolution**, never fabricated negative Facts. Errors/corpus gaps/source conflicts have independent statuses.
4. Compatibility and other technical relations require primary, applicable source evidence, not a coincidental interface value or shared family.
5. DS-EC-03 uses a compact EvidencePacket with pinned bundle and references to exact supported Fact/Relation IDs; direct visitor text cannot become trusted evidence.
6. Model input envelope is now 10,000 tokens (DS-SEC-08 supersedes the original reviewed 3,000) **including ALL serialized message content**, output 450 tokens; upper-bound segment allocations total 10,000 and are flexible, measured actual request is binding. LLM call count at most 1/user turn; zero-call templates possible.
6a. **Boundary/cost review after amendment:** current DS-EC-03 documents admission at exactly **10,000** counted input tokens and rejection/downsizing at **10,001**; its seven illustrative ceiling-capacity allocations sum to **10,000**. At fixed verified peak Flash rates the model-only reservation example is **$0.00354** for 10k cache-miss input + 450 output, replacing historical $0.00144 for 3k; ordinary source-sufficient packets stay shorter. These are specification checks, not observed runtime behavior.
7. Model's CandidateAnswerPlan is **not** user-visible technical prose; server checks structure, IDs, source revision, evidence, applicability and status before deterministic rendering. Generated free-form factual additions are disallowed in the first pilot design.
8. DS-SEC-07 accepted IP/session, daily, cooldown, support, private audit and global budget protections remain applicable before inference and after rendering.
9. Synthetic-only examples explicitly labeled; no private benchmark, genuine visitor IP, PDF bytes or secrets have been copied into public docs.

## Open choices deliberately NOT represented as approved implementation

- Canonical ID assignment and migration of variants: choose one stable ID strategy after source inventories are inspected.
- Eligible extraction review threshold for runtime fact inclusion and difference from benchmark expert GT approval.
- Controlled renderer coverage vs linguistic quality; complex comparisons may need additional approved templates, not unchecked model paraphrases.
- Exact supported typed attribute vocabulary and unit conversion/equivalence rules.
- Input token counter for direct DeepSeek model and margin, plus how to gate packets where required evidence exceeds 10k.
- 20 daily **billable provider attempts** versus **accepted user turns**, especially when a response is locally assembled at zero provider cost. Require explicit reconciliation before implementation, without changing DS-SEC-07 by inference.
- Operational values still unset: actual IANA reset timezone, global dollar budgets, support contacts, verified trusted proxy topology, privacy notice and log deletion policy implementation details.
- Grounding: only 3/12 PDF byte-pinned by prior WSL reports, 0 expert-approved benchmark GT, P4/P5 full claim-level factual review open; **NO Corpus Freeze**.

## Next architecture stage

Propose **DS-EC-04 typed dialogue memory and anaphora/correction resolution**, then **DS-EC-05 source-grounded answer verifiers and output modes** or combine them if owner requests a unified specification. Before any coding task, approve scoped entity/fact/relation contracts and offline acceptance fixtures. No general "RAG works" claim is possible based solely on contract documentation.

**Governance:** open Draft PR #1 only, no Merge, DS-02, production, new DeepSeek request, NEW RAG changes or Saturn site writes.
