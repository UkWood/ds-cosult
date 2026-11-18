# DS-LV-02/P9 — WSL Offline Local-State Audit Evidence (Owner-Reported)

**Date recorded:** 2026-11-18  
**Audit stage:** DS-LV-02/P9  
**Result:** **OFFLINE LOCAL-CUSTODY CHECK PASS**  
**Network activity:** 0 DeepSeek HTTP calls.  
**Provider API expense:** $0 for this local verification.

## 1. Source of observation

The owner ran the previously agreed **single read-only Python audit command** in Ubuntu WSL, directory `~/ds-consult-validation`, and returned the following **sanitized terminal output** directly to Architecture Session A. Architecture Session A did not remotely execute the script in the owner's environment or independently obtain the raw local private history. No API key or private full conversation history was transmitted.

```text
P8 TURN-1: INTEGRITY PASS
P8 TURN-2: INTEGRITY PASS
P8 TURN-3: INTEGRITY PASS
P8 TURN-4: INTEGRITY PASS
P8 PRIVATE HISTORY INTEGRITY: PASS
P8 ONE-SHOT MARKERS: 4/4 PASS
P8 FILE PERMISSIONS: PASS
P8 TOTAL TOKENS: 871
P8 ESTIMATED PEAK USD: 0.000319968
DEEPSEEK HTTP REQUESTS: 0
DEEPSEEK API COST: $0
P9 LOCAL OFFLINE AUDIT: PASS
```

## 2. What the pinned offline command validated

- Original P8 Python source SHA-256 == `6ca43fe2031a542700e46c8bd4f931115100934d9d0cbde0e5be47e76af19b3e`.
- Local P8 private state exists, has `completed_turns=4`, contains exactly four contiguous conversation turns.
- Four individual exclusive attempted markers and four redacted result JSON files exist.
- The local state file, marker files and redacted results all have restrictive file mode **0600** at the time of observation.
- Each private assistant answer's SHA-256 equals both the published redacted report's digest and the independently recorded expected hash:
  - TURN-1 `bd4b441fac779bf5525f830aacb1092bb042772885d5b93732e5504afe71a6e3`.
  - TURN-2 `bfe3cda9a5671d64cbe70a26d355c1562dbba0a68a0286b7fcbab44c7e0dea19`.
  - TURN-3 `275c1dd9fe00d69e46bc0554aa2dce1114037c529aa5dd0d3c14611712d8f8da`.
  - TURN-4 `1554ceea51d7353087704121c9d57d740a16ae2ca58bae49b66af841a6302b50`.
- Matching turn IDs, user prompts, answer previews, statuses `TURN_COMPLETE_REVIEW_NEEDED`, one reported HTTP attempt each, HTTP 200, observed `deepseek-flash`, finish `stop`, no reported reasoning/tool calls/errors.
- Prompt/output/cache token arithmetic and per-turn peak pricing arithmetic; cumulative estimates match and **871** total P8 tokens.
- Aggregate peak-rate estimate for the four paid P8 turns: **$0.000319968** (not a confirmed invoice).

## 3. Scope and limitations

**Accepted local-state/custody observation:** owner-reported read-only verification is internally consistent with already preserved GitHub redacted evidence and the pre-reviewed pinned audit command.

**Not independently verified by this command:** DeepSeek account statements/billing, cryptographic attestation of upstream HTTP exchange, third-party file erasure, correctness of technical facts beyond synthetic scenario, unprompted anti-hallucination behavior, or complete source-grounding of the P4/P5 answers.

This local check **does not** access or upload any genuine Saturn documents, hidden Core/GT, or P8 private conversation data to GitHub. Do not commit the private WSL JSON or logs.

**Architecture final acceptance belongs in:** `docs/acceptance/DS-LV-02-P9-FINAL-ARCHITECTURE-ACCEPTANCE.md` following separate GitHub evidence reconciliation.

No paid P9 API execution, no Merge, DS-02, production or Corpus Freeze.
