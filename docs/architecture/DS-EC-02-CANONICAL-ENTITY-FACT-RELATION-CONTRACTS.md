# DS-EC-02 — Canonical Data Contracts: Entity, Fact, Relation and EvidenceRef

**Date:** 2026-11-18  
**Status:** ARCHITECTURE CONTRACT CANDIDATE v0.2 — AUTHOR CORRECTION AFTER CONSOLIDATED REVIEW; NOT YET INDEPENDENTLY ACCEPTED OR IMPLEMENTED  
**Scope:** independent DS-консультант only; extension of DS-EC-01, not borrowing code or contracts from NEW RAG.  
**Security baseline:** DS-SEC-07 owner-accepted restrictions remain mandatory. Source inputs: trusted Saturn site and approved Saturn PDF only, considered injection-free by owner.

## 1. Purpose and precise model

An **Entity** states which real technical object/edition the user means. A **Fact** states one atomic, typed claim about exactly one entity with applicable conditions. A **Relation** states a directional, source-supported link between two particular entities or editions. An **EvidenceRef** binds a Fact/Relation to an exact original source and location. A **SourceBundle** identifies the immutable combination of site revision, approved PDF bytes and parser policies from which the candidate corpus was built.

Trusting a source is **not** the same as trusting any parser's output. Evidence bindings, qualifiers, extraction checks and expert-reviewed benchmark labels are separate layers. This is a proposal, not a claim of implemented validation.

### Rules that MUST hold in this proposed contract

- A record identity is **not** its display name, slug, arbitrary retrieved sentence or raw user text.
- A technical value may appear in a final user answer **only** after the backend checks the exact Fact/Relation ID, applicable entity/edition, source binding, extraction state and relevant qualifiers.
- Every factual record is immutable **within a pinned SourceBundle**. A changed source snapshot produces a new record revision/bundle, not silent in-place truth mutation.
- The user may edit which entity they *ask* about, but can never create approved Fact/Relation/EvidenceRef by asserting a property in chat.
- Absence of a property from indexed material is not proof of its negation. Only an **explicit sourced negative assertion** may be encoded as a negative Fact.
- The published site and approved PDFs are trusted by owner, but an extraction/revision mismatch can still block an assertion.
- Document IDs, evidence IDs, entity IDs and source route IDs are independent typed namespaces; never deduce canonical page URLs by guessing slugs.
- **Real** device assertions must not be invented in example fixtures. Synthetic demonstration records are always labeled SYNTHETIC and excluded from the production corpus.

## 2. Shared SourceBundle and EvidenceRef contract

### 2.1 SourceBundle

Required fields:

| Field | Type | Requirement |
|---|---|---|
| bundle_id | immutable string | Unique manifest identity; content-derived or signed, implementation choice later |
| site_snapshot_id | string | Stable identity for one pinned site content snapshot |
| site_commit_sha | SHA string | Pinned source Git commit |
| site_tree_sha | SHA string | Root of verified source tree when supplied |
| site_route_manifest_id | string | Exact canonical path inventory; no guessed routes |
| source_inventory_manifest_id | string | **v0.2 required** complete approved site/PDF-to-entity source inventory for scoped coverage receipts; includes known excluded/unpinned sources |
| attribute_dictionary_revision | string | **v0.2 required** typed field/unit/qualifier normalization contract |
| relation_dictionary_revision | string | **v0.2 required** directed relationship vocabulary and no-inference rules |
| evidence_policy_revision | string | **v0.2 required** runtime source-to-claim eligibility rules |
| entity_identity_map_revision | string | **v0.2 required** provenance-backed stable ID mapping across bundle revisions (may be empty initially) |
| pdf_revisions | list | Approved per-document bytes SHA-256 + document/revision IDs; may initially be empty |
| extraction_policy_version | string | Versioned parser/schema and normalization rules |
| built_at_utc | ISO8601 timestamp | Operational metadata, **not** a source revision substitute |
| publication_state | draft / source_checked / runtime_eligible / blocked | No automatic Corpus Freeze |

An AnswerSession binds to exactly one bundle_id per turn. No mixing site revision A with a newly fetched, unpinned PDF revision B. Production eligibility is decided by separate corpus validation gates; no current DS-CORPUS-1.0 Freeze is claimed.

### 2.2 EvidenceRef (required by Fact and Relation)

Common fields: evidence_id; bundle_id; channel (site or pdf); source_document_id; source_revision_id; parser_version; extraction_method; precise locator; optional source_quote_exact and source_quote_sha256; evidence_check_state; attribution metadata if an analyst/editor verified interpretation.

Conditional **site** fields: source repository identity, **site_commit_sha**, exact canonical_url from trusted manifest, **blob_sha**, **content_sha256**, and source_path within the trusted file/structured field. Nested slugs and support-document paths must come from source manifest, never user-provided guesses.

Conditional **PDF** fields: original approved source URL, document_id, edition/revision, **pdf_bytes_sha256**, **physical_page** (1-based) plus page span if needed, exact table/section/region locator, and parser version. Printed-page label may be supplemental, never substitute for physical_page. Direct PDF web URL alone is insufficient provenance.

EvidenceRef points to a source location, **not a blanket license to assert an arbitrary technical statement**: each Fact/Relation separately names the exact supported value and scope.

A technical field supported by two places stores two distinct evidence refs; disagreement is retained, not automatically overwritten by a more recent publication date. Source quotes, when present, must match the immutable source byte-derived parser output exactly (or be explicitly marked a human transcription with separate review).

### 2.3 Processing states, not fabricated confidence

- evidence_check_state: discovered / bytes_verified / locator_verified / extraction_verified / interpretation_reviewed / blocked.
- benchmark_gt_state: not_in_benchmark / candidate / expert_approved / rejected / blocked.
- A Fact may be eligible for a *bounded runtime answer* only under its explicit source-extraction policy; **expert_approved** is specifically required when a result is used as formal benchmark Gold, not automatically as a universal prerequisite for all trusted-source browsing.
- Never equate "source URL opened" or "vector similarity high" with extraction_verified.
- Parser, retrieval or checksum failure is an ERROR, **not** a normal unknown attribute.

## 3. Entity v0.1 contract

Required fields:

| Field | Purpose |
|---|---|
| entity_id | Opaque, stable ID assigned by operator/indexer; not inferred from a website slug or name |
| entity_type | system / device / software / component / document |
| canonical_name | Source-declared authoritative display name |
| identity_scope | Product family, device model, exact execution, edition or version — explicit type |
| identity_parent_id | Nullable ID linking exact model to family (only with source/provenance where meaningful) |
| aliases[] | Literal alias and language, its provenance, ambiguity class |
| source_bindings[] | Exact approved canonical routes or document refs |
| bundle_id | Which pinned corpus bundle contains this record |
| entity_record_revision | Immutable revision under a given bundle |
| record_state | draft / resolved / ambiguous / retired_in_bundle / blocked |

Optional fields: source-backed model number, lifecycle fact links, explicit model_variant_ids, source language/locale and links to attached documents. Avoid duplicating uncontrolled technical fact values in the Entity metadata.

**Identity rules:** family ≠ device model ≠ hardware execution ≠ software edition ≠ document revision. If two names collide, return multiple candidates and ask a precise clarification. An alias never proves two devices are identical; a source-backed identity relation must justify merge. A website redesign changing a canonical route does not imply a new device. A new hardware revision must not inherit old attributes without a source applicability rule.

Lifecycle status, model availability and compatibility are **Facts/Relations** with source provenance, not free-floating generated metadata.

### Synthetic example: Entity

~~~json
{
  "fixture": "SYNTHETIC_ONLY",
  "entity_id": "DEMO:DEVICE:CTRL-A:R1",
  "entity_type": "device",
  "canonical_name": "ДЕМО-КОНТРОЛЛЕР А",
  "identity_scope": "hardware_revision",
  "identity_parent_id": "DEMO:DEVICE:CTRL-A:FAMILY",
  "aliases": [{"text": "Демо-А", "language": "ru", "evidence_id": "EV-DEMO-01"}],
  "source_bindings": ["SRC-DEMO-CARD-01"],
  "bundle_id": "BUNDLE-DEMO-01",
  "entity_record_revision": "E-001",
  "record_state": "resolved"
}
~~~

These identifiers are artificial and **not** Saturn devices, real routes, or approved evidence.

## 4. Fact v0.1 contract

Required fields:

| Field | Purpose |
|---|---|
| fact_id | Immutable fact assertion ID; new when value/qualifiers/evidence change |
| subject_entity_id | Exact entity/edition to which the assertion applies |
| attribute_key | Dictionary-defined typed property, never ad-hoc LLM-generated name |
| value | Explicit typed scalar/string/bool/enum/list/range, with unit when numeric |
| polarity | positive or explicitly_source_negated; no "not found" negation |
| qualifiers | Variant, hardware/software version, applicability conditions, valid era and contextual scope |
| evidence_ids[] | At least one verified EvidenceRef pointing to this value and its applicability |
| bundle_id | Same pinned bundle as subject and evidence |
| extraction_state | Candidate/extracted/verified/blocked; distinct from expert GT status |
| record_revision | Immutable per assertion version |

**Value representation:** use exact decimal strings for quantities, source_unit and normalized_unit separately with a declared conversion version; preserve inequalities, +/- tolerances, temperature intervals, protocol labels, SI prefixes and conditional qualifiers. An empty or null value is not a Fact. Missing data lives in **NeedResolution**, not as a negative Fact or as "value=null".

For lists or enums include explicit source enumeration; never assume the list is exhaustive unless evidence explicitly says so. Boolean false is a claim that needs explicit source support; if there is no source, status is insufficient_evidence.

### Synthetic example: verified candidate Fact

~~~json
{
  "fixture": "SYNTHETIC_ONLY",
  "fact_id": "FACT-DEMO-PWR-01",
  "subject_entity_id": "DEMO:DEVICE:CTRL-A:R1",
  "attribute_key": "nominal_supply_voltage",
  "value": {"type": "quantity", "number_decimal": "24", "unit": "V", "original_text": "24 В"},
  "polarity": "positive",
  "qualifiers": {"variant": "R1", "conditions": ["nominal"]},
  "evidence_ids": ["EV-DEMO-01"],
  "bundle_id": "BUNDLE-DEMO-01",
  "extraction_state": "verified",
  "record_revision": "F-001"
}
~~~

**Incorrect interpretation explicitly prohibited:** no "IP54" Fact can be created from the absence of a protection-rating field; no "not Bluetooth capable" Fact can be synthesized merely because Bluetooth was not mentioned.

## 5. Relation v0.1 contract

Required fields:

| Field | Purpose |
|---|---|
| relation_id | Immutable relationship assertion ID |
| subject_entity_id / object_entity_id | Explicit directional, scoped IDs, both present in SourceBundle |
| relation_type | Predeclared typed vocabulary |
| qualifiers | Model variants, revisions, required accessories, firmware thresholds and conditions |
| evidence_ids[] | Exact source(s) explicitly supporting **the relationship itself** |
| bundle_id | Fixed snapshot |
| assertion_state | proposed / source_verified / expert_reviewed / blocked / conflict |
| record_revision | Immutable relationship assertion revision |

Initial relation vocabulary:
- document association: documented_in (metadata-only, no technical compatibility implied);
- taxonomy: model_variant_of, part_of (source-backed, no automatic domain-specific propagation);
- technical: requires, supported_by, compatible_with, incompatible_with, replaced_by, connects_to — **only** where source directly establishes its specific semantics and applicability.

**Non-derivability:** matching RS-485, Ethernet, same voltage, shared parent family, co-appearance in a diagram, or similar component names is **not** a valid proof of compatible_with. Do not infer mutual compatibility from two independent connections to a third device. Directionality and transitivity are false by default, unless a narrowly defined relation rule is individually approved.

~~~json
{
  "fixture": "SYNTHETIC_ONLY",
  "relation_id": "REL-DEMO-REQ-01",
  "subject_entity_id": "DEMO:DEVICE:CTRL-A:R1",
  "relation_type": "requires",
  "object_entity_id": "DEMO:COMPONENT:SUPPLY-Z",
  "qualifiers": {"conditions": ["standard_operation"], "model_variants": ["R1"]},
  "evidence_ids": ["EV-DEMO-02"],
  "bundle_id": "BUNDLE-DEMO-01",
  "assertion_state": "source_verified",
  "record_revision": "R-001"
}
~~~

The demo relation is hypothetical, never to be interpreted as a Saturn product recommendation.

## 6. NeedResolution: query-time status rather than fabricated facts

A user question yields one or more atomic needs; for each need the retrieval/verification layer returns exactly one typed outcome:

- supported: applicable verified Fact or Relation found; candidate can enter answer packet.
- ambiguous_entity_or_variant: more than one viable canonical identity; ask clarification.
- insufficient_evidence: properly searched approved available scope, but it does not establish the requested claim; wording: "В доступных материалах не указано" with scope qualification, not a universal no-property claim.
- conflict: two applicable trusted source assertions disagree; preserve both source refs and their revisions, present qualified conflict or escalate.
- scope_not_indexed: necessary approved source material not included/pinned in current bundle; **never** treat as absent.
- source_unavailable: identified approved source cannot be read/validated; do not claim unknown fact as if source was examined.
- processing_error: parser, checksum, schema, retrieval or verifier failure; stop or show safe technical error.
- out_of_scope or policy_blocked: external task or visitor goal-hijack request; no technical retrieval required.

NeedResolution fields: need_id, requested entity/attribute/relation, status, reviewed_bundle_id, eligible_fact_ids, eligible_relation_ids, matched_evidence_ids, ambiguity_candidates, conflict_groups, diagnostics_code. Outcomes cannot be elevated from insufficient_evidence to supported by model prose.

## 7. Conflict handling and revision applicability

1. Snapshot pinning: all entity IDs, facts, relations and EvidenceRefs must resolve under exactly one SourceBundle.
2. If two trusted source locations assert different values for the *same applicability*, mark conflict and retain both; do **not** prefer site over PDF, latest date over older, or newer version by guess.
3. If statements apply to different executions/revisions, do not label conflict; require explicit version selection or provide separately qualified values.
4. If source B supersedes source A only with an explicit cited supersession rule, adopt a scoped precedence rule reviewed by operator. Otherwise ask for human clarification/adjudication.
5. A derived structured summary must never discard a source qualifier, especially "without amplifier", "one ray", "optional" or "only for firmware X".
6. Apply corpus revision change as a new bundle and invalidate dependent dossier, citation and answer caches; do not silently reuse old source-locator mappings.


## 8. Normative v0.2 corrections: coverage, eligibility, entity identity (DS-EC-AR-01)

**Precedence:** this v0.2 section supersedes incompatible earlier v0.1 candidate text and examples. It is an AUTHOR CORRECTION, not independently accepted. Sources remain trusted by owner; extracting and applying data requires independent verification. Applies to CR-B01/B02, CR-I02/I03/I04/I07 and CR-M02.

### 8.1 SourceCoverageReceipt — explicit limited-world completeness (CR-B01)

Any NeedResolution claiming 'insufficient_evidence' MUST contain a valid SourceCoverageReceipt with coverage_state 'complete_for_declared_scope'. Scope must specify exact bundle_id, entity_id, variant/edition, attribute_key or directed relation type, and relevant conditions. It proves **only the declared inventoried source scope**, never universal absence of a property in all available manuals.

Required receipt fields:
- contract_version='ec-source-coverage/0.2', coverage_receipt_id, bundle_id, need_id, scope{subject_entity_id,object_entity_id?,variant_id?,attribute_key?,relation_type?,conditions?};
- source_inventory_manifest_id, required_source_ids[], enumerated_source_ids[], inspected_source_ids[], excluded_source_ids[] with reason, parser_versions[], index_revision;
- per-source byte_integrity, locator_integrity, extraction_completeness, indexing_completion and relevant document/variant association;
- applicable_assertion_ids_examined[], coverage_state, diagnostic_codes[], evaluated_at_utc.

Inventory is enumerated **before** top-K/search result selection from trusted canonical routes and pinned approved PDF associations. A source omitted from the model prompt still contributes applicable facts and conflicts to the verifier; all eligible ledger assertions for the exact need/scope are examined outside the shortened LLM packet.

Allowed coverage_state: 'complete_for_declared_scope', 'partial_index', 'source_unavailable', 'processing_error', 'not_applicable'. Required missing/unpinned/incompletely parsed source => 'partial_index' / NeedResolution 'scope_not_indexed'; approved source unreadable => 'source_unavailable'; checksum/parser/index problem => 'processing_error'. Only complete_for_declared_scope plus absence of any eligible applicable assertion may return 'insufficient_evidence'. If an applicable source conflicts, mark 'conflict' and include both source IDs rather than selecting a prompt-visible winner. For a positive fact with incomplete *other* sources, do not claim complete coverage or that no contradictory facts exist.

A receipt is invalidated by a change in SourceBundle, manifest, parser, index, entity or attribute dictionary revision. Cached negative responses require matching exact receipt identity and cannot survive source updates. User wording must specify the checked scope: “В проверенных материалах, включённых в текущий корпус, не указано…”, never universal absence.

### 8.2 EvidenceEligibilityPolicy — verified source-to-claim applicability (CR-B02)

Version 'ec-eligibility/0.2' is bound to bundle and extraction policy. Every runtime technical Fact/Relation requires an EvidenceEligibilityDecision identifying fact/relation_id, need_id, bundle_id, policy_revision, evidence_ids[], per-check PASS/FAIL/NOT_APPLICABLE flags and deterministic reason_code. All required **source-to-assertion proof checks** must pass: approved source identity and bytes/commit, exact field/span/table cell/diagram region locator, extraction value, unit/polarity and qualifiers, source edition, exact entity and hardware/software variant, relation direction and conditions. A **local conflict scan must execute successfully**, but the finding that multiple verified assertions contradict one another is a **separate outcome**, not a failure of source fidelity. Source assertion proof is distinct from permission to publish one value as established technical truth. Neither a correct SHA nor a credible physical page alone validates the assertion.

| Evidence kind | Public answer eligibility |
|---|---|
| Site structured field | Verified pinned site commit/blob/content hash + exact field path, source-declared value/unit/qualifiers and entity applicability |
| Site prose or PDF text | Verified exact text span/physical page/parser; supported meaning/conditions and model edition; no quote-to-unrelated-claim |
| PDF table | Original bytes SHA, physical page AND table ID,row,column,header,model/variant mapping; value, unit, sign, tolerances independently validated |
| PDF drawing/wiring | Verified page/region PLUS separately reviewed interpretation of terminal, connection, direction and edition; otherwise blocked/needs_support |
| Negative property | Explicit applicable source negation with evidence, not missing field |
| Technical Relation | Explicit evidence of exact directional pair, type, firmware/accessory/variant conditions, no inference from same Ethernet or shared parent |
| Document navigation | Approved identity and URL only; no technical claim implied |

EvidenceRef states discovered/bytes_verified/locator_verified alone are insufficient for a published claim. Eligibility requires extraction_verified **and** source-to-assertion applicability, with interpretation_reviewed for diagrams or otherwise ambiguous source semantics. Publication as an **established technical fact** additionally requires absence of unresolved applicable conflict. If genuine conflict exists, both individual source assertions may remain **source-proven** and attributable, but neither becomes an established VerifiedClaim. 'expert_approved' for benchmarking is independent: do not imply every straightforward trusted site field requires separately approved benchmark GT.

### 8.2.1 R1-CR01 — Distinct assertion proof, conflict detection and publication authority

**This paragraph is NORMATIVE for R1** and replaces the earlier shortcut “all Fact/Relation eligibility checks pass only if no conflict”. A successfully executed conflict scan may report **conflict present** while both opposing source assertions are genuinely extracted and properly attributed.

Four independent typed decisions are mandatory per need:
1. **SourceAssertionProof**: `assertion_id`, `need_id`, `source_bundle_id`, `source_id`, `fact_or_relation_id`, `exact_evidence_ref_ids[]`, `source_fidelity_state=proven|unproven|source_error`, `subject_variant_qualifier_scope`, `claim_type`, source literal value/unit and verification revision. `proven` means “the trusted source **states this scoped value**”, NOT “this value is adopted as resolved product truth”.
2. **ConflictAssessment**: `need_id`, `coverage_receipt_id`, `evaluated_assertion_ids[]`, `conflict_state=none|applicable_conflict|incomplete_scope|processing_error`, `opposing_assertion_groups[]`, `comparison_policy_revision`. Conflict scan success is recorded separately from result; `applicable_conflict` is a **successful detection**, not a failed extraction. All applicable ledger assertions are considered outside top-K.
3. **FactPublicationDecision**: `fact_or_relation_id`, `need_id`, `publication_role=established_fact|attributed_conflict_position|blocked`, `reason_code`, `source_assertion_proof_ids[]`, `conflict_assessment_id`, `decision_policy_revision`. `established_fact` requires proof, all mandatory applicability checks and `conflict_state=none`. If `applicable_conflict`, each **proven** opposed source assertion has `attributed_conflict_position`, but **no conflicting value** can have `established_fact`. A failed evidence extraction never becomes a displayable position.
4. **ConflictPosition**: `position_id`, `need_id`, `assertion_proof_id`, exact source-quoted or typed assertion value and qualifiers, approved `evidence_ref_ids[]`, `source_label`, `render_role=attributed_only`. It is a **source-attributed statement**, not a VerifiedClaim or a resolved technical value. The final controlled renderer displays both positions as “Источник A указывает …; источник B указывает …; подтверждённого единого значения нет”, with independent exact CitationBinding for **each position**.

`EvidenceEligibilityDecision` must therefore separate `source_fidelity_checks` from `ConflictAssessment` and `publication_role`. The word `eligible` by itself is ambiguous and MUST NOT be used as the sole proof of adoption as truth. Relation conflicts use the same discipline and must preserve direction, version and qualifiers. The public result status is `needs_support` or `partial` (if independent other needs are proven), reason `applicable_source_conflict`. User may see each **verified source assertion** but not a claim that either one is indisputable hardware truth.

**Synthetic example, not Saturn data:** source A states “24 В”; source B states “12 В”, same approved entity/variant/conditions. Both SourceAssertionProof entries are `proven`, ConflictAssessment is `applicable_conflict`, both publication roles `attributed_conflict_position`, zero established VerifiedClaims for this voltage need. The renderer shows two source-attributed positions/citations, status `needs_support`, never “питание 24 В” or “питание 12 В” as final confirmed fact. If one PDF table cell mapping is invalid, that assertion proof is `unproven` and cannot be displayed as a proven conflict position.

**Acceptance:** AR-T02, EC5-06, EC5-40 and negative wrong-cell case AR-T03; check full ledger and no unqualified value output.

### 8.3 Identity, dictionary and schema registry (CR-I02/I03/I04/M02)

Entity_id identifies a stable technical object, **not** its URL or name. A record is uniquely pinned by entity_id + entity_record_revision + bundle_id; model family, concrete execution, firmware edition and document revision are distinct scopes. For cross-bundle moves, entity_identity_map_revision must describe explicit evidence-backed old-to-new mapping or force clarification; never inherit parent-family facts automatically. Route redesign does not by itself create a new technical entity. Turn snapshot remains pinned until output/audit complete; next turn migrates and invalidates old facts/citations/caches.

Fact and Need MUST reference attribute_dictionary_revision, declaring attribute_key, data type, allowed source/normalized units, exact decimal serialization, conversion_rule_revision, range/inclusive bounds, inequality, tolerance, enum/list exhaustiveness, explicit negation and mandatory applicability qualifiers. '0,5 МПа', '12.5 V', ≤ and ± must not be mis-tokenized or silently dropped. Null/missing never equals Boolean false. A list is non-exhaustive unless source explicitly establishes full enumeration. Unrecognized conversion => error/unsupported, not silent numeric rewrite.

Relations MUST reference relation_dictionary_revision. Default semantics: directional=true, transitive=false, invertible=false; any exceptions require separate explicit source-backed reviewed rule. Compatible_with is NEVER inferred from protocol equality, connects_to, or shared family.

Canonical wire types (schema versions required): Entity, Fact, Relation, EvidenceRef, SourceBundle, SourceCoverageReceipt, EvidenceEligibilityDecision, SourceAssertionProof, ConflictAssessment, FactPublicationDecision, ConflictPosition, DocumentReference, QuestionNeed (single), QuestionNeeds (ordered collection), NeedResolution, DialogState, EvidencePacket, QuestionInterpretationPlan, CandidateAnswerPlan, VerifiedClaim, CitationBinding, VerifiedAnswerResult. Public structures must omit IP, cookies, tokens, keys and private audit content.

NeedResolution enum v0.3: supported, insufficient_evidence, ambiguous_entity_or_variant, **ambiguous_question**, conflict, scope_not_indexed, source_unavailable, processing_error, out_of_scope, policy_blocked. `ambiguous_question` with reason `interpretation_unsupported` is required for a valid paid P1 QuestionInterpretationPlan whose interpretation_status is unsupported AFTER admitted dispatch; no automatic turn/POST refund or second P2 request. This is not `insufficient_evidence` about hardware. For missing/conflict completeness evidence link coverage_receipt_id. Eligibility decisions and reason codes are mandatory for selected factual assertions. DS-EC-05 defines the explicit mapping to verification/final statuses.

### 8.3.1 R1-CR04 — Common schema/version/reason registry

Use a single canonical type registry, not independently invented spelling in the four contracts:
- `QuestionNeed` = one atomic need; `QuestionNeeds` = ordered collection of QuestionNeed. `NeedResolution` = per-need outcome.
- `QuestionInterpretationPlan` = strict P1 output **before** source retrieval; `CandidateAnswerPlan` = strict P2 selection of existing Fact/Relation IDs after retrieval. The two schema versions and one-call paths are disjoint.
- `SourceAssertionProof` verifies source-content fidelity; `ConflictAssessment` assesses contradictions; `FactPublicationDecision` assigns `established_fact|attributed_conflict_position|blocked`; `ConflictPosition` is attributed-only display evidence.
- `VerifiedClaim` = adopted **non-conflicting** source-proven technical fact or Relation. `CitationBinding` targets exactly one of `claim_id|position_id|document_reference_id`.
- `DocumentReference` = approved metadata-only source link, navigation content; never proof of arbitrary technical specifications.
- `VerifiedAnswerResult` = backend immutable final result with verified_claims, conflict_positions, document_references, each citation binding and final status/reason.
- `FinalStatus` enum v0.3 = `answered|partial|clarification|needs_support|error|out_of_scope`; server service-denial outcomes are separate. `ReasonCode` v0.3 must include `fully_supported|partial_missing_fact|partial_conflict|ambiguous_entity|ambiguous_variant|ambiguous_question|interpretation_unsupported|invalid_model_plan|insufficient_evidence|source_scope_not_indexed|applicable_source_conflict|source_unavailable|source_integrity_error|verifier_internal_error|document_reference_only|domain_out_of_scope|policy_override_attempt|cost_limit_prevented_inference`. A status/reason may not imply claim support if evidence is absent.
- Type schema versions and source/policy/dictionary/normalization revisions are distinct; each serialized union has a discriminator and strict unknown-field validation. Full executable JSON Schema belongs to a separately approved coding stage, **not claimed implemented now**.

**Canonical cross-layer mapping** is normative in DS-EC-05 §13.1. R1-CR02 P1 `unsupported` = NeedResolution `ambiguous_question`, reason `interpretation_unsupported`, final `clarification` **after an already charged and attempted P1**. Conflict proof does not become an established technical truth. Metadata-only navigation is `document_reference_only` and cannot satisfy unrelated characteristics. A malformed model output maps to `invalid_model_plan`, not a device property. The same names must appear in fixtures and handoffs.

### 8.4 Offline review fixtures (designed, not executed)

- AR-T01: attribute appears only on a non-top-K PDF page => must not answer “not specified”.
- AR-T02: two applicable contradictory facts, one not in LLM prompt => source-ledger conflict detected.
- AR-T03: valid PDF SHA/page but wrong table row/column => ineligible claim.
- AR-T04: equal Ethernet/RS-485 without explicit relation => no compatibility assertion.
- AR-T14: SourceBundle changes mid-turn => old pinned bundle for active request, safe migration next turn.
- AR-T15: valid Fact ID with wrong edition, qualifier or physical-page support => rejected.

## 9. Offline acceptance scenarios for proposed contracts

| ID | Scenario | Required result |
|---|---|---|
| E-01 | Alias maps to one verified device | Exact entity ID, no guessed URL |
| E-02 | Alias maps to two variants | ambiguous_entity_or_variant |
| F-01 | Exact sourced "24 В" with qualifier | supported, correct unit and evidence |
| F-02 | Source has no IP rating | insufficient_evidence, **not** false/IP54 |
| F-03 | A PDF extraction lacks bytes SHA256 or physical page | blocked, cannot be final citation |
| F-04 | Two conflicting ratings same applicability | conflict with both source IDs |
| F-05 | Different source variants have different ratings | separately qualified, not merged |
| R-01 | Identical interface, no explicit compatibility | insufficient_evidence for compatibility |
| R-02 | Explicit relation with conditional accessory | supported only when condition preserved |
| R-03 | Relation object missing from bundle | blocked |
| S-01 | Mixed source bundles in one answer | fail closed |
| S-02 | Canonical URL invented from slug | blocked |
| S-03 | Retrieval/checksum error | processing_error, never "not specified" |
| S-04 | User claims new technical specification | remains user assertion, no new Fact |
| G-01 | Source-verified item not expert-approved in benchmark | possible scoped runtime candidate per policy, **not** approved benchmark Ground Truth |

All examples and tests in this document are **contract specifications only**, not implemented or executed. Use deterministic synthetic fixtures before any real source material; real source test is separately subject to owner-approved scope/custody.

## 10. Future formalization

A later coding stage may implement equivalent relational/typed JSON contracts, schema validation and canonical identity rules using an agreed technology. **Do not assume a particular storage engine, embedding provider or library now.** JSON Schema 2020-12 supports conditional required fields and type checks, useful to express site-vs-PDF locator alternatives; these specifications are not a ready-to-run JSON Schema.

The provenance concept of binding derived entities to their sources is compatible with W3C PROV-O, but full RDF/PROV-O serialization is **not required** for a small first pilot.

**Public normative references:**
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- JSON Schema 2020-12: https://json-schema.org/draft/2020-12/json-schema-core
- JSON Schema validation: https://json-schema.org/draft/2020-12/json-schema-validation

## 11. Governance

**OPEN FOR OWNER ARCHITECTURE REVIEW**, no model calls, no DS-02 implementation, no production, no Corpus Freeze, no Merge. Do not publish private Core benchmark/GT, real visitor IP/dialogue data or restricted PDF originals in this public repository. NEW RAG remains independent; Saturn site remains READ-ONLY.
