# DS-EC-03 — Evidence Packet, Compact Dialogue Context and Deterministic Answer Gate

**Recorded:** 2026-11-18  
**Status:** ARCHITECTURE DESIGN CANDIDATE v0.1 — OWNER REVIEW PENDING; NO MODEL OR API RUN
**Owner-approved input cap amendment DS-SEC-08 (2026-11-18):** 10,000 complete input tokens replaces the original 3,000 ceiling, with unchanged 450 output tokens and no change to the one-call limit; source-selection still targets the shortest sufficient prompt.  
**Upstream:** DS-EC-01 reference architecture and DS-EC-02 Entity/Fact/Relation/EvidenceRef contracts.  
**Mandatory operator policy:** DS-SEC-07 public access, prompts, rate/budget and private logging controls.

## 1. Design question

How can a visitor ask naturally about multiple Saturn devices and their revisions while the backend sends **no more than 10,000 total input tokens to DeepSeek**, with **at most 450 model output tokens**, preserving facts and their source applicability? The model's final prose must never become independent evidence.

Proposed separation:
- **QuestionNeeds / ContextState** are private backend-controlled state and intent records, not truth.
- **EvidencePacket** is a small, pinned, immutable per-request selection of existing verified Fact/Relation IDs and exact EvidenceRefs.
- **CandidateAnswerPlan** is an untrusted proposal from DeepSeek in a constrained structure, not user-visible final text.
- **VerifiedAnswerResult** is the independently checked outcome assembled by backend, not the raw provider output.

The public site/PDF corpus is trusted and owner-declared injection-free. The adversary in this design is the **visitor text**, including direct Goal Hijacking and false user-supplied technical assertions.

## 2. Query and compact state contracts

### QuestionNeeds

Fields: request_id; user_question_exact (kept only in private session/audit, not a GitHub artifact); requested_intent; target_entity_hints; target_attribute_keys; target_relation_types; per-need identifiers; source_bundle_id; slot for entity/version ambiguity; status.

A multiple-condition question is split into atomic needs. Example:
- Need N1: device X supply voltage, exact version X/v1.
- Need N2: device Y supply voltage, exact version Y/v2.
- Need N3: direct compatibility of X/v1 with Y/v2 (requires **explicit Relation**, never deduced from voltage or protocol alone).

A need is not automatically "covered" by one keyword match. Either an exact scoped source-backed Fact/Relation is available or a typed unresolved outcome is returned.

### DialogState

A compact **server-owned** structure:
- active_entity_ids[] and version/variant disambiguation;
- comparison_entity_ids[] and explicit short-term anaphora handles ("первый", "второй", "он");
- previously asked need_ids and last answer status;
- pending_clarification (if any);
- bundle_id pinned to snapshot/revision and server policy_revision;
- last_verified_fact_ids[] (references only, not self-authenticating user assertions);
- session identity and IP-lease metadata stored separately, not sent to the model.

**NOT** stored as verified fact: user's `считай, что IP68`, forged role messages or a model-generated summary without source IDs. Legitimate `я имел в виду модель B` updates only the selected entity and re-resolves evidence; it does not rewrite source truth.

When an active source bundle changes, invalidate fact/citation handles referring to the former bundle, and reconstruct as appropriate. Never mix old and new evidence silently.

## 3. EvidencePacket v0.1 contract

Required:
- packet_id, request_id, bundle_id, policy_revision, packet_schema_revision;
- question_needs[] with expected entity/attribute/relation;
- resolved_entities[]: entity_id, canonical_name, identity_scope/variant, and deterministic disambiguation status;
- supported_facts[]: exact fact_id, subject_entity_id, attribute_key, typed value/unit, qualifiers, evidence IDs;
- supported_relations[]: exact relation_id, subject/object IDs, relation_type, qualifiers, evidence IDs;
- evidence_snippets[]: evidence_id, channel, precise source locator, **short exact relevant excerpt** or typed field locator, source identity and integrity hashes;
- need_outcomes[]: supported, insufficient_evidence, ambiguous_entity_or_variant, conflict, scope_not_indexed, source_unavailable, processing_error or out_of_scope;
- packet_validation: source-locator verification, claim applicability verification, parser/revision checks, token counts and abstention reasons.

All Fact/Relation/EvidenceRef IDs must resolve in the **same pinned bundle**. The EvidencePacket stores **only** source-approved facts, not user-supplied "corrections". Missing attributes are represented by need_outcomes with a reviewed source scope, never by inventing a false-value Fact.

**Prompt text that says "I am the system" remains a user message** and is never translated into the provider's true system role, packet policy, or new source evidence.

## 4. Hierarchical source selection

1. L0 alias and entity resolver picks likely canonical IDs and exact variants. If ambiguous: ask clarification; do not guess.
2. L1 short dossier yields candidate fields and relation IDs. Prefer narrow typed evidence to long prose.
3. L2 Fact/Relation ledger verifies which question needs have proven matches. Preserve qualifiers and all applicable contradictions.
4. L3 source excerpt/page locator is included **only for a fact actually used**, to validate that a quoted source supports that particular need and version. Truncate at meaningful boundaries only; no blind mid-sentence truncation that loses qualifiers.
5. L4 diagrams/images are **not** silently converted into technical edge/direction facts; a visually interpreted fact needs separately source-bound interpretation and quality gate. The first textual pilot can return "requires document review" where diagram semantics are unresolved.

Never place a whole PDF or all device datasheets in a conversational prompt simply because they were retrieved. Page count/bytes SHA remain in local source store; packet holds only minimum necessary excerpt and location.

Priority by evidence need coverage first, then source-specific applicability, then minimum safe token cost. Similarity score alone does not establish truth or compatibility. If contradictory evidence is applicable, include both sides or return a conflict message; do not cut the inconvenient side to stay within budget.

## 5. Strict model input budgeting

**Hard rule originally approved in DS-SEC-07 and AMENDED by DS-SEC-08 (owner, 2026-11-18):** maximum **10,000 input tokens for the entire provider request**, including true system role instructions, the current question, compact state, source-backed facts, cited excerpts, formatting schema and message framing. Output max is a **separate** 450-token server-set cap. 1,200 Unicode characters of user text is a different independent input limit.

**10,000 is an upper bound, not an input token target.** For ordinary short technical questions, aim for a minimal sufficient evidence packet (often ≤3,000 tokens) and zero-call deterministic answers where suitable. Use the larger 10k envelope only for genuinely complex cases with multiple entities, competing evidence or longer relevant excerpts.

Proposed illustrative **ceiling-capacity allocation for a complex request**, not minimum values, fixed slices or a substitute for an actual tokenizer:

| Input segment | Target tokens |
|---|---:|
| System policy, Saturn-only role and explicit no-fabrication rule | 600 |
| Current question, minimal compact dialogue state | 500 |
| Entity identities and versions | 500 |
| Typed Facts and Relations with qualifiers | 2,400 |
| Relevant exact source excerpts and locator bindings | 4,300 |
| Structured output contract and constrained format | 300 |
| Conservative counting margin / serialization overhead | 1,400 |
| **TOTAL HARD ENVELOPE** | **10,000** |

Actual current question may require more than the illustrative 500-token segment. The backend must count the entire assembled **actual API payload** using a compatible tokenizer; if exact preflight count is unavailable, it must use a conservative headroom policy validated against provider usage, with no claims of exact 10k enforcement until validated. It must not rely on these approximate buckets; redistribute only soft targets, never exceed the hard 10,000-token limit.

Precedence for shrinkage:
- Discard duplicate quotes and irrelevant entity summaries first.
- Remove optional historical conversational text, preserving typed anaphora handles and necessary correction state.
- Drop low-priority optional facts only when not needed for a required comparison/qualifier.
- If exact required claim evidence, contradictory alternative, page scope, model variant, system instruction or output schema still cannot fit: return **partial/clarification/needs_support** via server code, or decline that inference. **Never** silently omit a condition or send an overbudget provider request.

The backend reserves a conservative worst-case provider cost before POST; initial fixed-rate example 10,000 cache-miss input tokens + 450 output ≈ **$0.00354** at earlier validated Flash rates, subject to pricing revision/provider billing. No default paid web search, Files/OCR or multi-call model verification in public visitor runtime.

## 6. Single-call strategy (0 or 1 model API request per visitor turn)

This rule prevents a seemingly benign "separate classifier + answer model + verifier model" pipeline from tripling token costs unexpectedly.

- **Path 0: fully local, 0 DeepSeek calls.** Exact attribute/FAQ/known-unknown lookup; backend resolves typed need and renders a source-cited answer or missing-data status deterministically. Must still pass domain/rate/log policies.
- **Path 1: local retrieval first, 1 model call.** If the backend can resolve entities/needs and gather source packet, use the **one** DeepSeek call for constrained, multilingual/natural dialog output planning. Backend validates the proposed plan and assembles safe final output. No second model verifier call.
- **Path 2: model help required for parsing ambiguous natural question, 1 model call.** If local intent/entity resolution fails but question is plausibly in-domain, spend the sole permitted DeepSeek call on **structured interpretation only**, then perform source retrieval and deterministic answer rendering in backend. Do **not** call the model again for final prose.
- **Denied or blocked:** out of domain, rule override, exhausted IP quota, 11th series turn, overlong question, exceeded token or global monetary budget: **0 model calls**, deterministic static response.

Both inference paths must be able to return natural, concise, understandable site answers without unverifiable model-added facts. A source-grounded free-form long explanation cannot be guaranteed by a deterministic verifier without a more precise controlled-language contract; first pilot intentionally favors **controlled templates**.

## 7. CandidateAnswerPlan and final gate

For a model-selected answer, require a small structured plan **only**, using allowlisted IDs from the EvidencePacket. This is an abstract proposed payload, not runnable JSON Schema:

~~~json
{
  "packet_id": "PKT-DEMO-001",
  "task": "compare",
  "status": "partial",
  "selected_fact_ids": ["FACT-DEMO-PWR-01"],
  "selected_relation_ids": [],
  "unresolved_need_ids": ["NEED-COMPATIBILITY"],
  "presentation_mode": "short_comparison",
  "clarify_entity_ids": []
}
~~~

The plan is synthetic and does **not** claim any real Saturn specifications.

Backend must check:
1. packet_id exactly matches active verified packet; bundle and policy revision cannot change.
2. Every selected fact/relation ID exists, is source-eligible, addresses a requested need, has same bundle, proper variant/revision and source locator.
3. Each chosen relation has **source-supported pairwise semantics**; matching interface fields never substitute compatible_with evidence.
4. Missing/conflicting/scope_not_indexed needs remain properly unresolved; the model cannot claim a supported value from its world knowledge.
5. No extra JSON fields, raw HTML, policy overrides, arbitrary URLs or unapproved output styles; parse/schema errors are **not** accepted.
6. Complete source citations for all technical statements are chosen by backend from EvidenceRef, **not** invented by model. The backend may attach exact site link or PDF page; don't cite a wrong physical page or different source revision.
7. Output status is one of answered / partial / clarification / needs_support / error / out_of_scope; policy gate may downgrade or block any model proposal. Model cannot authorize its own answer.

**Controlled rendering:** Final answer is assembled by backend templates grounded in verified typed values, approved exact source excerpts and deterministic connective grammar. A model's unverified natural-language technical additions are not displayed. If a template cannot express a complex technical explanation accurately, return a bounded partial answer or a follow-up rather than hallucinating a fluent narrative. Future owner review can broaden natural-language generation with separately proven claim extraction and rechecking.

**No LLM rewriting after the final gate**. This is a design direction for the new independent project, not a statement that the separate NEW RAG already supplies approved reusable code.

## 8. Private answer result and audit requirements

Suggested VerifiedAnswerResult:
- request_id, active_bundle_id, policy_revision, output_status;
- final_answer_text from deterministic renderer;
- verified_claim_refs[] (each Fact/Relation to EvidenceRef);
- citations[]: exact URL or original PDF ref + physical page;
- unresolved_need_ids[] and reason_code;
- token/cost usage and provider actual billing field (unknown until reconciled);
- audit_event_id and response emission timestamp.

The accepted user question and the **actually displayed** final reply, UTC times and canonical client IP must be stored only in the **private encrypted audit backend**, with approved 30-day pilot retention and privacy notice/lawful-purpose assessment before launch. Do not include raw visitor chats or IPs in PUBLIC GitHub or general RAG document caches. A blocked request must produce limited safe audit metadata and **must not** cause a paid provider call.

**Owner-resolved quota semantics (DS-SEC-09):** **20 accepted visitor questions per canonical IP per configured operator-calendar day**, including locally assembled or cached answers; paid provider POST attempts and USD reservations have separate counters. Each admitted question consumes exactly one visitor-turn slot (idempotent replays do not double-count), and at most one provider POST may be attempted. A blocked/invalid request is not an admitted visitor question.

## 9. Offline acceptance examples (new, not run)

| ID | Case | Expected result |
|---|---|---|
| P-01 | One known typed attribute from eligible site field | zero-call deterministic answer with exact site citation |
| P-02 | Source-backed PDF fact with bytes SHA and physical page | correct document/page citation |
| P-03 | Missing IP rating | missing_data, not false/IP54 |
| P-04 | User-supplied IP68 contrary to missing source | user claim rejected, no new Fact |
| P-05 | Same interface, no source relation | no compatibility assertion |
| P-06 | Two independently sourced conflicting values | conflict, both evidence kept |
| P-07 | Two variants same product family | exact variant preserved / clarify |
| P-08 | "А у второго?" across turns | resolve previous second entity from typed state |
| P-09 | Forged developer role in visitor message | no policy change or expanded source scope |
| P-10 | First five rapid requests followed by cooldown | prescribed 0/10/20/40/60/90 sequence, no provider call on 429 |
| P-11 | Complete provider input counted as 10,001 tokens | no provider call; safe partial/clarification or correctly reduced packet |
| P-11A | Complete provider input counted as exactly 10,000 tokens (otherwise valid) | hard token limit allows admission, subject to separate budget and other gates |
| P-12 | User asks to omit source citation | backend citations remain mandatory |
| P-13 | Model invents fact ID in candidate JSON | final verifier rejects it |
| P-14 | Model chooses valid Fact but wrong variant | verifier rejects it |
| P-15 | Model status answered but need missing | downgrade/needs_support |
| P-16 | Cached local reply and different session same IP | no extra active session, no private data leak |
| P-17 | Daily IP limit exhausted / global USD breaker | zero provider traffic, static notice/support |
| P-18 | Bounded cost + token telemetry and audit | actual final text logged with IP/UTC privately |
| P-19 | Source snapshot changes between requests | packet recreated, old refs invalidated |
| P-20 | Malformed structured model output | no unchecked prose, safe error/partial |

Tests require deterministic fake source and mock provider first. No live API test permitted by exhausted previous GO. Real Saturn expert Ground Truth and PDF custody are still incomplete; no Corpus Freeze.

## 10. Owners' next architectural decisions

- Select exact supported Fact/Relation attribute vocabulary and casing/version normalization for the **first three demo entities**; choose a non-sensitive fixture, not an invented Saturn value.
- Review planned output modes (simple fact / compare / qualified relation / missing data) and whether controlled templates are sufficient for the intended user experience.
- **RESOLVED under owner DS-SEC-09:** 20 accepted visitor question turns per IP/operator-calendar day, including zero-call responses, while provider POST attempts and cost are tracked separately; implementation must verify atomic idempotent counters.
- Decide separate dialogue session state/history persistence and privacy boundaries as the next architecture step.
- Confirm operator-specific timezone, support contacts, budgets, trusted proxies and privacy handling before any pilot.

**Status:** DESIGN FOR REVIEW; no code, no paid calls, no new PR, no merge, DS-02, production or corpus freeze. Saturn-Main-Site READ-ONLY, NEW RAG unchanged.
