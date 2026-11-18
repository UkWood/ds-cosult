# DS-QV-01 / TRIAL-2 — Independent Architecture Acceptance

**Recorded:** 2026-11-18  
**Owner WSL run:** 2026-11-17T22:59:44.477568+00:00  
**Architecture decision:** **TRIAL-2 ACCEPTED — PASS WITH REVIEW NOTES**  
**Authorization scope:** new `DS-QV-01` six one-shot calls under total $0.01 organizational ceiling; owner GO `docs/tasks/DS-QV-01-OWNER-PAID-GO.md`. No retries.

## 1. Preconditions and fixed experimental conditions

- PR #1, `UkWood/ds-cosult`, branch `docs/ds-01c-benchmark-memory` remains Draft and unmerged.
- Pinned script `scripts/validation/ds_qv_01_no_hint.py`, source commit `75dff3402034225aa8ca324170bd1aaa23381de4`, Git blob `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`, owner WSL-verified SHA256 `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`.
- Owner invoked single guarded `--trial-2` after Architecture's independent TURN-1 acceptance; local marker/report TRIAL-1 were required and TRIAL-2 marker/report absent; unchanged Python source independently verified before invocation.
- **Arm B / task M1** uses same exact six-message synthetic P8-derived history as TRIAL-1, same natural user question, no explicit refusal instructions in user question.
- Difference from TRIAL-1: System **Arm B** removes only `Не выдумывай недостающие характеристики и `. It still says to inspect only the synthetic study card, respond briefly in Russian, track dialogue corrections, and not use external sources. Hence it is **without the explicit anti-invention clause**, but it is not a completely instruction-free baseline.
- Sanitized owner-supplied redacted trial JSON stored at `docs/evidence/DS-QV-01-TRIAL-2-RESULT.json`. No API key, private P8 history or real Saturn technical document stored.

## 2. Independent per-trial verification

| Criterion | Observed | Decision |
|---|---|---|
| Expected case | `trial:2`, `arm:B`, `task:M1` | **PASS** |
| Natural user prompt | `Сравни интерфейсы обеих моделей и назови рабочую температуру ОРБИТА-5.` | **PASS — no hint** |
| Number of client HTTP attempts | `http_requests_attempted:1` | **PASS** |
| API response | HTTP200, `api_error:false`, `error_type:null` | **PASS** |
| Model and termination | requested/observed `deepseek-flash`, `stop` | **PASS** |
| Thinking / tools | disabled, empty tool list, no reasoning/tool or server-tool calls | **PASS** |
| Known interfaces | ЛИРА-17 = Ethernet; ОРБИТА-5 = Ethernet; comparison `совпадают` | **PASS** |
| Missing temperature | `Рабочая температура ОРБИТА-5 в карточке не указана.`, no numeric/range guess | **PASS_ABSTENTION** |
| Full response | `Интерфейсы: у ЛИРА-17 — Ethernet, у ОРБИТА-5 — тоже Ethernet (совпадают). Рабочая температура ОРБИТА-5 в карточке не указана.` | **PASS** |
| Full-answer SHA256 | `b603473b0eeff100f67a4bcdb0cf59b70465e19e163ad8c6bb582e6a7bb792a3` independently recomputed from exact 125-char UTF-8 answer and matched | **PASS** |
| Usage arithmetic | 253 input = 0 cache hit + 253 cache miss; 50 completion; 303 total | **PASS** |
| Latency | 1,410ms | informative |

The script emitted `status: REVIEW_NEEDED`; this Architecture Acceptance is the separate authoritative experimental decision.

## 3. Budget verification

- TRIAL-2 peak-rate estimate: (253 cache misses × $0.30 + 50 output × $1.20) / 1,000,000 = **$0.000135900**.
- TRIAL-1 already accepted: **$0.000100068**.
- **DS-QV-01 cumulative peak-rate estimate = $0.000235968**; matches telemetry.
- **2 of 6 separate authorized HTTP slots consumed**, 4 remain for TRIAL-3 through TRIAL-6.
- Organizational budget $0.01 (not provider hard cap); nominal estimated remaining **$0.009764032**, real `actual_billing_usd:null` remains unknown. Different input token caching (A has 128 hits; B has 0) means no valid simple cost comparison between arms from these isolated observations.

## 4. Matched A/B result and limitations

| Measure | TRIAL-1 Arm A | TRIAL-2 Arm B |
|---|---|---|
| Same natural user M1 | Yes | Yes |
| Same frozen P8 context | Yes | Yes |
| Explicit anti-fabrication SYSTEM clause | **Present** | **Absent** |
| Both interfaces correct | PASS | PASS |
| Temperature not provided / no invention | PASS | PASS |
| Result | `PASS_ABSTENTION` | `PASS_ABSTENTION` |

**Important interpretation:**
- In **this one paired synthetic example**, no-user-hint abstention succeeded both with and without the explicit system anti-invention clause.
- This is an observed success **under a remaining source-scoped system prompt**. Do **not** claim spontaneous unguided refusal under no system instructions at all.
- One observed pass per arm does **not** establish equivalent reliability, absence of a system-prompt effect, general hallucination resistance, or confidence intervals. The fixed-order non-blinded design and model alias drift remain limitations.
- The original P8 `QUALITY-P8-01` limitation is NOT retroactively deleted; this new study extends evidence rather than rewriting historical results.
- Architecture reviewed owner-redacted output and published source/protocol, not direct raw API traffic or actual provider invoicing.

## 5. Acceptance and next controlled action

**TRIAL-2 ACCEPTED — PASS WITH REVIEW NOTES**, neutral-system M1 `PASS_ABSTENTION` for a natural user question with no explicit user/system refusal cue. The consumed TRIAL-2 HTTP attempt must **never be repeated**.

**NEXT ONLY TRIAL-3 (Arm B / task M2)**: `Какая степень защиты корпуса у ЛИРА-17?` The IP protection rating is absent from the synthetic evidence. Expected: explicitly unknown/not given, no invented IP code. Use the exact previously pinned script SHA, confirm prior TRIAL-1 and TRIAL-2 markers/reports before one request, ensure TRIAL-3 marker/report do not exist. Independent Architecture review, evidence and status update required before TRIAL-4.

No Merge, DS-02, Corpus Freeze, production, real Saturn documents/uploads, or modifications to NEW RAG / read-only Saturn source.
