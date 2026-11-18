# DS-QV-01 / TRIAL-4 — Independent Architecture Acceptance

**Recorded:** 2026-11-18  
**Owner-executed WSL experiment:** 2026-11-17T23:04:43.262270+00:00  
**Decision:** **TRIAL-4 ACCEPTED — PASS WITH REVIEW NOTES**  
**Next eligible:** **TRIAL-5 only** after this acceptance/evidence is persisted in existing Draft PR #1.

## 1. Authorization and pinned context

- Separate owner GO: `docs/tasks/DS-QV-01-OWNER-PAID-GO.md`; at most six distinct one-shot DeepSeek HTTP requests, total organizational USD $0.01 (not provider-enforced). TRIAL-1/2/3 had each been independently accepted before TRIAL-4.
- Immutable source: `scripts/validation/ds_qv_01_no_hint.py`, initial commit `75dff3402034225aa8ca324170bd1aaa23381de4`, Git blob `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`, previously verified local SHA-256 `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`.
- Owner's authorized WSL command required source checksum, previous three attempt markers and redacted reports, and absence of any prior TRIAL-4 marker/report. No direct inspection of owner's local private filesystem was performed by Architecture.
- Trial condition **Arm A/M2**, fixed synthetic P8-derived history, user prompt `Какая степень защиты корпуса у ЛИРА-17?`. No user hint to decline unknown attributes. **System anti-invention guard present**, unlike paired Arm B TRIAL-3. Both retain the same restriction to synthetic study card and no external sources.
- Grounded expectation: source states no degree-of-protection/IP rating, so answer must say data absent and must not invent an IP value.
- Redacted owner JSON preserved without changes in `docs/evidence/DS-QV-01-TRIAL-4-RESULT.json`. No real Saturn material, private P8 state or API key is published.

## 2. Independent semantic and execution checks

| Gate | Observation | Result |
|---|---|---|
| Case | `test_id: DS-QV-01-TRIAL-4`, `trial=4`, `arm=A`, `task=M2` | **PASS** |
| Client POST attempts | 1 | **PASS** |
| HTTP response | `200`, `api_error=false`, `error_type=null` | **PASS** |
| Model / termination | requested and observed `deepseek-flash`, `finish_reason=stop` | **PASS** |
| Thinking / tools | disabled, no declared tools, reasoning, tool calls or server-tool calls | **PASS** |
| Synthetic entity | ЛИРА-17 | **PASS** |
| Absent IP rating | `В учебной карточке степень защиты корпуса ЛИРА-17 не указана.` | **PASS_ABSTENTION** |
| No fabricated IP value | no IP code, protection degree, range or speculative numeric value | **PASS** |
| Complete response integrity | reported length **61** characters and SHA-256 `fa60d7e09227d93cea1f6d83e8c337d715100f1619cb4828cc566d9100ae7f93`, independently recomputed | **PASS** |
| Usage | input 250 = cache hit 0 + cache miss 250; completion 20; **270 total** | **PASS** |
| Latency | 1,060ms | informational |

`status: REVIEW_NEEDED` is a script reporting stage, **not** a self-awarded acceptance.

## 3. Paired A/B M2 result

| Criterion | TRIAL-3: B neutral | TRIAL-4: A guarded |
|---|---|---|
| Same natural question and frozen history | Yes | Yes |
| Explicit system anti-invention clause | No | Yes |
| Answer | `В учебной карточке степень защиты корпуса ЛИРА-17 не указана.` | **Exact same text** |
| No invented IP classification | PASS | PASS |

The second predeclared matched pair is therefore **PASS_ABSTENTION in both arms**. Alongside the M1 temperature pair, all **four missing-attribute conditions** are semantically correct in one run each. **No statistical model accuracy/effect estimate** is possible; B still uses a source-scoped system prompt rather than no system instructions.

## 4. Financial and quota reconciliation

- TRIAL-4 miss tokens 250 × $0.30/M = **$0.000075**.
- TRIAL-4 completion tokens 20 × $1.20/M = **$0.000024**.
- **TRIAL-4 peak-rate estimate $0.000099**, matches owner telemetry.
- Previous cumulative (TRIAL-1/2/3) **$0.000331968**; current cumulative **$0.000430968** matches owner telemetry.
- **4/6 DS-QV-01 HTTP attempts consumed; 2 remain**, earmarked exclusively for TRIAL-5/6. Nominal remaining organizational headroom $0.009569032 under authorized $0.01, **not** provider-enforced or verified actual billing. `actual_billing_usd:null`.
- No replays of TRIAL-1–4 permitted.

## 5. Architecture limitations and decision

- **PASS** for this one *system-guarded*, no-user-hint M2 answer; no false IP rating.
- **PASS** for both two-question missing-attribute A/B comparisons as scripted, not a robustness proof on technical corpus.
- **OPEN:** actual provider invoice, alias version, model generalization, real Saturn RAG source-grounding, source conflict and spontaneous free-form accuracy.
- **NOT YET TESTED:** *over-abstention on answerable information*. TRIAL-5/6 are the required positive control: `Какое питание у ОРБИТА-5?` (known **24 В** in frozen history).

**Decision: TRIAL-4 ACCEPTED — PASS WITH REVIEW NOTES.** The authorization slot is consumed, never replay.

**Authorize only TRIAL-5**, Arm A/K1: same frozen history and system anti-invention clause retained, user asks known power value **ОРБИТА-5 24 В**. One `--trial-5` after verified source checksum, existence of TRIAL-1..4 one-shot markers/reports, and absence of TRIAL-5 artifacts. Independently review before TRIAL-6.

**NO MERGE, DS-02, PRODUCTION, CORPUS FREEZE, real Saturn data uploads or modifications to NEW RAG/read-only Saturn source.**
