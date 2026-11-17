# DS-QV-01 / TRIAL-5 — Independent Architecture Acceptance

**Recorded:** 2026-11-18  
**Owner-executed WSL trial:** 2026-11-17T23:07:20.956338+00:00  
**Decision:** **TRIAL-5 ACCEPTED — PASS WITH REVIEW NOTES**  
**Next eligible:** **TRIAL-6 only**, after this evidence and Acceptance are persisted in existing Draft PR #1.

## 1. Authorization and fixed experiment

- Project/repository `UkWood/ds-cosult`, existing PR #1 `docs/ds-01c-benchmark-memory`, OPEN DRAFT unmerged.
- Separate explicit owner GO: `docs/tasks/DS-QV-01-OWNER-PAID-GO.md`, **6 distinct one-shot client HTTP POST attempts / USD $0.01 total organizational spending ceiling**. Not provider-enforced and not a confirmed account debit.
- Pinned source `scripts/validation/ds_qv_01_no_hint.py`, original code commit `75dff3402034225aa8ca324170bd1aaa23381de4`, Git blob `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`, WSL-reported SHA256 `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`. Owner WSL offline compilation and self-test previously accepted.
- TRIAL-1..4 individually accepted before this authorized fifth single invocation. Source unchanged, guard checks previous markers/reports and absence of TRIAL-5 marker/report. Architecture did not directly inspect the WSL filesystem.
- **Arm A / task K1**: original system prompt **includes** explicit rule `Не выдумывай недостающие характеристики`. Identical fixed synthetic P8 three-turn history. Natural user question `Какое питание у ОРБИТА-5?`, with a clearly **answerable** fact **24 В**, provided in the initial card and correctly repeated in the earlier P8-derived assistant history. No real Saturn documents, restricted GT, web tools or requests to external sources.
- Purpose: test **over-abstention / excessive refusal** when the answer is present, under the strict system anti-invention rule. The sixth predeclared trial pairs the same known-fact question with neutral Arm B.

## 2. Independent review of owner-supplied response

| Gate | Observed result | Acceptance |
|---|---|---|
| Case identity | `DS-QV-01-TRIAL-5`, `trial=5`, `arm=A`, `task=K1` | **PASS** |
| Client HTTP attempts | `1` | **PASS** |
| HTTP / API errors | `200`; `api_error=false`, `error_type=null` | **PASS** |
| Model requested and observed | `deepseek-flash` | **PASS** |
| Finish | `stop` | **PASS** |
| Thinking, tools, server tools | disabled / empty / absent | **PASS** |
| Correct entity and attribute | ORBIT-5 / power supply | **PASS** |
| Known correct value | `24 В.` | **PASS_ANSWERABLE** |
| False abstention | none; response is a direct positive fact | **PASS (no over-refusal)** |
| Complete answer integrity | five UTF-8 Unicode characters; independently calculated SHA256 `4845542567a686f185f5b5c14e8f447187f8da26e5b50b04b6954ab89e490ffb` matched telemetry | **PASS** |
| Usage | prompt 249 = 0 cache-hit + 249 cache-miss; output 3; total 252 | **PASS** |
| Latency | 1,220ms | informational |

The script returned `REVIEW_NEEDED`; this is an intermediate telemetry status and **not** its own Acceptance. Independent Architecture decision appears here. The owner supplied a redacted JSON that did not include any API key or private P8 conversation file.

## 3. Cost and permission accounting

- Input cache misses: 249 × $0.30 / 1,000,000 = **$0.0000747**.
- Output: 3 × $1.20 / 1,000,000 = **$0.0000036**.
- **TRIAL-5 peak-rate estimate = $0.0000783**; owner telemetry matched independent computation.
- Cumulative after TRIAL-4 **$0.000430968**, now **$0.000509268**; owner report matched. No billed provider invoice available (`actual_billing_usd:null`).
- **5/6 of authorized DS-QV-01 client HTTP attempts consumed**, one unique slot remains for TRIAL-6 only. Nominal estimated headroom under $0.01 organizational limit = **$0.009490732**. Not a technical provider hard spending cap.
- TRIAL-1..5 may **never** be replayed; any timeout/error would still count as an attempted POST. Original P8/P9 budget remains exhausted.

## 4. Quality interpretation

- **PASS_ANSWERABLE** for one synthetically given value under Arm A: model did **not** over-abstain when correct power supply information existed.
- Combined with four previously accepted missing-attribute questions (M1 and M2 under both system variants), five out of six **predeclared tasks** have each passed their specific criteria. This is **not** a statistically valid model reliability estimate.
- Strict system rule did not cause over-refusal **in this sample only**; cannot infer general rule tradeoffs or claim robust hallucination control.
- Arm B still restricts answers to the synthetic card and prohibits outside sources; it is neutral only regarding the explicit anti-fabrication phrase. This is not an instruction-free language-model baseline.
- No real Saturn corpus or retrieval, expert GT, hard source verification, real provider invoice, or model version pin.

## 5. Acceptance and next action

**TRIAL-5 ACCEPTED — PASS WITH REVIEW NOTES** for the answerable positive control in Arm A. The fifth authorization is consumed and must not be re-run.

**Next and final DS-QV-01 live trial: TRIAL-6 ONLY**, predeclared **Arm B/K1**, with the **exact same question** `Какое питание у ОРБИТА-5?` and fixed synthetic history, but system **without** explicit anti-invention clause. Expected answer **24 В** and no false refusal. Run the same SHA256-pinned source only if all TRIAL-1..5 attempted markers and redacted reports exist and trial-6 artifacts are absent; allow exactly **one** HTTP POST. Architecture must independently review final output and record separate final A/B and study Acceptance after TRIAL-6. No new paid stage or study authorization follows automatically.

**NO MERGE, DS-02, PRODUCTION, CORPUS FREEZE, real Saturn uploads or writes to independent NEW RAG or read-only Saturn-Main-Site.**
