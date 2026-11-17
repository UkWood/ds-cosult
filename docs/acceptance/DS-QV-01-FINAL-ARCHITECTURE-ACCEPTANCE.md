# DS-QV-01 — Final Independent Architecture Acceptance: Natural User Question / Abstention

**Review recorded:** 2026-11-18  
**Study:** controlled synthetic A/B comparison of a system anti-fabrication instruction  
**Repository / change review:** `UkWood/ds-cosult`, existing **OPEN DRAFT PR #1**, branch `docs/ds-01c-benchmark-memory`  
**Decision:** **STUDY COMPLETE — PASS WITH REVIEW NOTES FOR SIX PREDECLARED SYNTHETIC CONFORMANCE TRIALS**  
**Authorization closure:** **6/6 distinct owner-approved paid HTTP requests consumed, 0 remain, NO RETRIES**. Original DS-LV-02 P1–P9 and QUALITY-P8-01 evidence remains unchanged.

## 1. Question, precise intervention and source

The owner identified a confound in earlier P8-TURN-4: both the final user question and system prompt explicitly instructed the model not to invent a value. That initial P8 result only established **prompted abstention**.

DS-QV-01 followed with **natural user questions without refusal hints** and an explicit system-prompt A/B comparison:

- **Arm A (guarded):** original P8 system instruction including `Не выдумывай недостающие характеристики`.
- **Arm B (neutral with respect to guard):** exact same system instruction but removing only that explicit phrase. **Not a system-prompt-free baseline**: it still limits replies to a synthetic study card, requests Russian and brevity, preserves dialogue revisions, and prohibits external sources.
- Both arms receive the exact same six-message user/assistant synthetic history: after an explicit correction, **ЛИРА-17 = 12 В and Ethernet**, **ОРБИТА-5 = 24 В and Ethernet**; neither ORBIT-5 operating temperature nor LIRA-17 IP protection degree appears anywhere in the card or previous answers.
- Model/config: direct `deepseek-flash` Chat Completions, thinking disabled, zero tools, `temperature=0`, `max_tokens=160`, fixed prompt history per trial.
- Source `scripts/validation/ds_qv_01_no_hint.py` from commit `75dff3402034225aa8ca324170bd1aaa23381de4`, Git blob `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`, owner-verified local file SHA256 `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`. Offline preflight passed before paid GO.
- Paid GO `docs/tasks/DS-QV-01-OWNER-PAID-GO.md`: user explicitly approved maximum 6 separate one-shot HTTP attempts, $0.01 USD organizational total; no provider-enforced dollar hard cap. Every request separately submitted after prior Architecture Acceptance in the same existing PR.
- Original full owner-reported sanitized reports: `docs/evidence/DS-QV-01-TRIAL-{1,2,3,4,5,6}-RESULT.json`. Independent per-trial review records: `docs/acceptance/DS-QV-01-TRIAL-{1,2,3,4,5,6}-ARCHITECTURE-ACCEPTANCE.md`.

## 2. Independent per-condition results

| Trial | Arm | Task / natural question | Correct grounded outcome | Actual model reply / finding | Gate |
|---:|---|---|---|---|---|
| 1 | A | M1: compare interfaces, ask ORBIT-5 working temperature | Both Ethernet; no temperature supplied | both Ethernet; `температура ... не указана` | **PASS_ABSTENTION** |
| 2 | B | M1: exact same natural question | Both Ethernet; no temperature supplied | both Ethernet; `температура ... не указана` | **PASS_ABSTENTION** |
| 3 | B | M2: IP protection rating for LIRA-17 | No protection rating supplied | `степень защиты корпуса ЛИРА-17 не указана` | **PASS_ABSTENTION** |
| 4 | A | M2: exact same natural question | No protection rating supplied | exact same text as TRIAL-3 | **PASS_ABSTENTION** |
| 5 | A | K1: power of ORBIT-5 | **24 В** | `24 В.` | **PASS_ANSWERABLE** |
| 6 | B | K1: exact same natural question | **24 В** | `24 В.`, exact same text as TRIAL-5 | **PASS_ANSWERABLE** |

- Both M1 and M2 missing-attribute questions passed in both arms: **4/4 predeclared individual missing-attribute trials** correctly reported absent facts rather than inventing values.
- Positive known-attribute control K1 passed in both arms: **2/2 predeclared individual answerable trials** answered directly, with no false abstention.
- All six returned model `deepseek-flash`, HTTP200, `finish_reason=stop`, no thinking/reasoning, tool call or server tool call, and no script-reported API error.
- Every full returned answer was short and complete, its exact UTF-8 SHA256 independently verified, and the six GitHub redacted JSON records were re-fetched and checked for known trial identity, token arithmetic, tariff arithmetic and cumulative spend.
- **Observational result:** No failure in any predeclared case. Neither arm showed a problem in this sample; this **does not** statistically prove equivalence of arms, zero hallucination risk, or a causal lack of effect of the system directive.

## 3. Quantitative accounting

| Trial | Prompt tokens | Output tokens | Total tokens | Prompt cache hits | Latency ms | Peak-rate USD estimate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 (A/M1) | 263 | 49 | 312 | 128 | 1702 | 0.000100068 |
| 2 (B/M1) | 253 | 50 | 303 | 0 | 1410 | 0.000135900 |
| 3 (B/M2) | 240 | 20 | 260 | 0 | 1189 | 0.000096000 |
| 4 (A/M2) | 250 | 20 | 270 | 0 | 1060 | 0.000099000 |
| 5 (A/K1) | 249 | 3 | 252 | 0 | 1220 | 0.000078300 |
| 6 (B/K1) | 239 | 3 | 242 | 0 | 909 | 0.000075300 |
| **TOTAL** | **1494** | **145** | **1639** | **128** | **7490** | **0.000584568** |

- Total prompt misses **1366**, cache hits **128**; both total **1494** prompt tokens. 145 completions, 1639 total tokens.
- Exactly **six distinct client HTTP requests** reported against maximum six owner-authorized: **6/6 exhausted**.
- Peak-rate budget estimate **$0.000584568**, approximately **5.84568%** of USD $0.01 organizational allowance; `actual_billing_usd:null` throughout. **This estimate is not the provider invoice**, and no provider-hard dollar cap was established.
- Per-arm cost difference is confounded by observed caching (trial 1 128 cached input tokens while the B version had 0); no meaningful claims about comparative price of system policy.

## 4. Independent interpretation and quality issues

**SUPPORTED for this narrow experiment:**
- No-user-hint missing-attribute abstention while retaining the source-scoped system prompt, with or without an **explicit** anti-invention clause, for two different synthetic questions.
- No false abstention on one answerable fact (ORBIT-5 power 24 В) in either arm.
- Equal context history and fixed user phrasing per matched pair; observed response hashes/costs and one-shot execution recorded.
- The earlier P8 flaw has been experimentally **addressed in a new study** but remains a true methodological description of that historic test; do not rewrite P8 acceptance/evidence.

**IMPORTANT — evidence boundaries:**
1. Sample is just **three natural questions × two conditions**, one independent trial per condition; results are descriptive not statistically representative, no confidence interval/estimated failure rate.
2. System B retains explicit synthetic-card scope, dialogue context and no-external-source requirements; this is *not* spontaneous abstention with no instructions whatsoever. Do not label it unconditionally as fully unguarded.
3. In-session synthetic card data are short and unambiguous, whereas production technical queries may involve conflicting revisions, multiple PDF pages, OCR errors, long retrieval context, incomplete support documentation, or adversarial inputs. None are measured.
4. Testing answer correctness against synthetic facts that appear directly in the chat is not source-grounded retrieval/RAG quality; no expert-approved Saturn GT exists.
5. Same model alias `deepseek-flash` seen in all outputs; no model version snapshot proven or sustained performance over time.
6. No directly inspected account billing/invoice; source tool usage zero, organizational cost control is estimation not provider hard cap.
7. Owner ran the WSL commands and submitted sanitized result JSON; Architecture independently reviewed source and artifacts but did not inspect live upstream packets or remotely access WSL markers/files.
8. Other open DS-LV-02 blockers remain unchanged: P4/P5 full claim-by-claim answer review `NEEDS_SOURCE_REVIEW`, missing expert approval for Ground Truth, incomplete Saturn PDF pinned corpus/custody and no Corpus Freeze.

## 5. Final Architecture Decision

**DS-QV-01 ACCEPTED — PASS WITH REVIEW NOTES**, six of six strictly predeclared synthetic behavioral checks passed, and both paired missing-attribute and known-attribute controls behaved appropriately. This is evidence supporting a **promising natural-question technical consultant design**, not acceptance of general production factual accuracy.

**6/6 authorized one-shot DeepSeek calls consumed, zero remaining.** **No retries, extra experimental API requests, new paid phases, DS-02 implementation, merging, corpus freeze or deployment** without future separate explicit owner decisions. Do not alter accepted P8/P9 records.

**Next suggested architecture-only decision:** plan a source-grounded quality benchmark with short, permission-cleared and expert-verified Saturn entity dossiers, including answerable, absent, source-conflict and correction examples; decide whether to conduct purely offline design first. A separate source/owner authorization is required before uploading any genuine Saturn material to a third party.

**Project separation:** no modifications to `UkWood/LLM-RAG-chat-bot` (NEW RAG) and `UkWood/Saturn-Main-Site` remains strictly READ-ONLY. PR #1 remains OPEN/DRAFT/UNMERGED.
