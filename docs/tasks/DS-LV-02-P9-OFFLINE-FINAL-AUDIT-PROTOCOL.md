# DS-LV-02/P9 — Final Offline Conformance & Evidence Audit Protocol

**Recorded:** 2026-11-18  
**Status:** **PREPARED / NOT EXECUTED — P9 OFFLINE ONLY**  
**Prior gate:** P8 final Architecture Acceptance: `docs/acceptance/DS-LV-02-P8-FINAL-ARCHITECTURE-ACCEPTANCE.md`  
**Authorization:** Owner blanket P6–P9 GO; P9 **0 HTTP requests / $0 API spend**.

## 1. Goal and strict safeguards

Perform a retrospective evidence audit of prior DeepSeek conformance tests without initiating any provider action, replay, upload, download, background task or secret-bearing diagnostic. Keep P1–P8 owner-provided redacted JSON immutable; do not rewrite an originally inconclusive result to make it pass. All results and Architecture findings reside in current Draft PR #1, branch `docs/ds-01c-benchmark-memory`. No Merge/production/DS-02/Corpus Freeze.

**Linux step must be completely offline:** read-only local `~/ds-consult-validation` files, no `curl`, `wget`, `requests`, `urllib`, provider SDK, API key or shell xtrace. Do not print or commit the local private P8 conversation JSON. No redundant typed approval. The single owner-visible command will validate pinned script and private P8 state, and print **only sanitized summary**. Audit cannot view actual DeepSeek billing ledger.

## 2. Evidence scope

| Stage | Permanent redacted evidence / acceptance | Status to audit |
|---|---|---|
| P1 | `docs/evidence/DS-LV-02-P1-RESULT.json` + `docs/acceptance/DS-LV-02-P1-ARCHITECTURE-ACCEPTANCE.md` | Thinking PASS, 1 call |
| P2 | `docs/evidence/DS-LV-02-P2-RESULT.json` + P2 acceptance | Search PASS, 1 call |
| P3 | `docs/evidence/DS-LV-02-P3-RESULT.json` + P3 acceptance and fixture drift note | URL read PASS with review notes; no claim of source H1 |
| P4 | `docs/evidence/DS-LV-02-P4-RESULT.json` + P4 acceptance | Web search capability PASS with notes; full answer not independently verified |
| P5 | `docs/evidence/DS-LV-02-P5-RESULT.json` + P5 acceptance | Deep Thinking + Web Search tool capability PASS; **full final factual grounding NEEDS_SOURCE_REVIEW** |
| P6 | `docs/evidence/DS-LV-02-P6-TEXT-RESULT.json`, `DS-LV-02-P6-TEXT-LIST-RESULT.json`, `DS-LV-02-P6-RICH-RESULT.json` + P6 final acceptance | TEXT & RICH PASS, original GET400 preserved, 9/9 HTTP, independent complete file-list absence |
| P7 | `docs/evidence/DS-LV-02-P7-OCR-RESULT.json` + P7 acceptance | Dedicated OCR PASS WITH REVIEW NOTES, 1/1 HTTP |
| P8 | `docs/evidence/DS-LV-02-P8-TURN-1..4-RESULT.json` + each turn acceptance + P8 final acceptance | Four-turn dialogue PASS WITH REVIEW NOTES, 4/4 HTTP; offline verify local state/markers |
| P9 | This audit protocol and eventual offline WSL report | **NOT STARTED** until user runs local offline check |

## 3. Checks and evidence-quality requirements

1. Independently confirm PR #1 remains OPEN/DRAFT, source is unchanged, no Merge; record current HEAD as audit baseline.
2. Read all existing redacted artifacts **without rewriting them**. Validate HTTP counts, observed model/tool actions, finish reasons, JSON schema, token accounting, cost estimate and historical owner authorizations. Be explicit where scripts saved only truncated answer previews or telemetric metadata.
3. For P8 specifically, the owner runs a single offline WSL read-only Python check: pinned Python SHA256; existence of four exclusive attempted markers, four redacted files, single private `completed_turns=4` file; contiguous turn indices; private answer SHA256 matches each redacted JSON; user question matches; preview matches the beginning; model/HTTP/finish & absent reasoning/tools; token splits; per-turn tariff arithmetic; cumulative monotonic spend; optional restrictive file modes. Print sanitized summary only, not dialogue or key.
4. Request accounting **for blanket-go P6–P9** must reconcile P6 9 + P7 1 + P8 4 + P9 0 = **14/14 authorized HTTP**, with no remaining retry quota. Budget P6 $0.02, P7 $0.01, P8 $0.02, P9 $0 = $0.05 organizational (not provider-enforced).
5. Rate-based expense estimates may be reconciled using already accepted peak estimates (P6 $0.0008733, P7 $0.000225, P8 $0.000319968). Combined P6–P8 peak-rate estimate: **$0.001418268**. **No invoice/actual debit evidence**; report `billing_verified=false`. Never present this figure as provider-measured spending.
6. Public GitHub must not receive API keys, private P8 dialog state, non-public Saturn originals, confidential GT or reasoning text; only sanitizer-generated redacted telemetry and architecture notes. P6 deletion: distinguish provider ack and full-list verification from permanent byte erasure certification.
7. P5 full 1259-character answer remains only partially source-reviewed; `factual_answer_gate=NEEDS_SOURCE_REVIEW` **remains open**. P4 full source grounding also unverified; no after-the-fact PASS for accuracy without complete source material.
8. 0 expert-approved Ground Truth and no Corpus Freeze. 3/12 Saturn PDFs pinned by Linux report and others unverified; do not equate synthetic conformance with production readiness.

## 4. Acceptance outcome

A P9 audit can yield `PASS WITH REVIEW NOTES` **for evidence and protocol reconciliation**, while preserving important open blockers above. A mismatch in local P8 state, answer hashes, file access, request limits or budget calculations triggers `CHANGES REQUESTED` or `INCONCLUSIVE`; do not resolve by repeating DeepSeek requests.

After the offline WSL check, create `docs/evidence/DS-LV-02-P9-OFFLINE-WSL-AUDIT.md` and `docs/acceptance/DS-LV-02-P9-FINAL-ARCHITECTURE-ACCEPTANCE.md` in existing PR. Update `PROJECT_STATE.md` and `ARCHITECTURE_LOG.md`; post summary in PR. Separate architectural go/no-go for real corpus/entity dossiers requires an explicit future owner decision.

**No P9 DeepSeek calls under any circumstances.**
