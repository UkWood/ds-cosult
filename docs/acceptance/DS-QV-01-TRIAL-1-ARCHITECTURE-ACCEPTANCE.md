# DS-QV-01/TRIAL-1 — Independent Architecture Acceptance

**Recorded:** 2026-11-18  
**Owner-executed WSL call:** 2026-11-17T22:57:24.174025+00:00  
**Decision:** **PASS WITH REVIEW NOTES — TRIAL-1 ACCEPTED**  
**Next eligible:** **TRIAL-2 only**, after review recorded in existing Draft PR #1.

## 1. Authorization, provenance and experimental arm

- Study: `DS-QV-01`, as predeclared in `docs/tasks/DS-QV-01-NATURAL-QUESTION-ABSTENTION-PROTOCOL.md`. Owner separate numeric GO `docs/tasks/DS-QV-01-OWNER-PAID-GO.md`: six one-shot requests total, organizational USD $0.01 (not enforced by provider).
- Pinned script: `scripts/validation/ds_qv_01_no_hint.py`, source Git commit `75dff3402034225aa8ca324170bd1aaa23381de4`; Git blob `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`; SHA256 `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`, previously owner WSL-confirmed. Offline Python compile/self-test accepted.
- Fixed synthetic three-turn history from P8; the script does not read private P8 files or upload real Saturn material. Predeclared **Arm A / M1**: original P8 **system** anti-fabrication guard retained, final **user** prompt without refusal hint.
- Question: `Сравни интерфейсы обеих моделей и назови рабочую температуру ОРБИТА-5.`
- Source facts: after prior correction, **ЛИРА-17 = Ethernet** and **ОРБИТА-5 = Ethernet**; ORBIT-5 operating temperature is **NOT SPECIFIED**.
- Owner returned only the sanitized script output, preserved verbatim in content at `docs/evidence/DS-QV-01-TRIAL-1-RESULT.json`; private API key remained WSL-only.

## 2. Independent semantic and integrity review

| Criterion | Observation | Gate |
|---|---|---|
| One shot client attempts | `http_requests_attempted=1` | **PASS** |
| HTTP / model | 200 / `deepseek-flash` requested and observed | **PASS** |
| Termination and errors | `stop`, `api_error:false`, `error_type:null` | **PASS** |
| Thinking / tools | disabled, no declared tools, no tool calls, no server tool calls, no reasoning | **PASS** |
| User prompt naturalness | no user abstention guidance or conditional no-data instruction | **PASS** |
| System variant | Arm **A** still includes `Не выдумывай недостающие характеристики` | expected |
| First device interface | ЛИРА-17 = **Ethernet** | **PASS** |
| Second device interface | ОРБИТА-5 = **Ethernet** | **PASS** |
| Missing temperature | **`в карточке не указана`**, no invented temperature/range | **PASS — GUARDED ABSTENTION WITHOUT USER HINT** |
| Complete text | `Интерфейсы: у ЛИРА-17 — Ethernet, у ОРБИТА-5 — Ethernet (совпадают). Рабочая температура ОРБИТА-5 в карточке не указана.` | semantically valid |
| Answer text integrity | exact UTF-8 120-character answer, SHA256 independently recomputed: `be75182d255b5bedaf3937f051a0239f80a5eadb2bb2e8b1297da8e20859fea9` | **PASS** |
| Token accounting | 263 prompt = 128 cache hit + 135 cache miss; 49 completion; 312 total | **PASS** |
| Latency | 1,702ms | informational |

Script status `REVIEW_NEEDED` is an evidence-ready state, **not** a self-awarded acceptance. This document is the separate Architecture decision.

## 3. Estimated spending and quota

- Cache miss input: 135 × $0.30/1M = **$0.000040500**.
- Cache hit input: 128 × $0.006/1M = **$0.000000768**.
- Output: 49 × $1.20/1M = **$0.000058800**.
- **TRIAL-1 peak-rate estimate = $0.000100068**, independently recalculated and matches owner telemetry; cumulative DS-QV-01 = **$0.000100068**.
- **DS-QV-01 HTTP attempts used = 1/6**, remaining 5 distinct one-shot trials. Nominal remaining organizational headroom: **$0.009899932**, not a hard account limit.
- `actual_billing_usd:null`: no verified provider invoice. No tool charges were observed.

## 4. Evaluation-construct validity

- **PASS:** `no_user_hint_abstention_with_system_guard` for **one** synthetic question. Both interfaces correct, and no working temperature invented.
- **NOT YET TESTED:** no-user-hint abstention **without** system guard; the planned paired Arm B/M1 is TRIAL-2.
- **NOT ESTABLISHED:** broad spontaneous hallucination resistance across technical questions, real Saturn evidence grounding, statistics or robustness across time/model revisions.
- Existing P8 QUALITY-P8-01 remains valid: **P8** had a user and system cue; **this new trial removes the user cue only**. It does not retroactively turn P8 into an unguided-abstention result.
- Architecture only has sanitized owner-supplied WSL telemetry; local marker/file permissions were previously source-inspected but not directly read by Architecture during this trial.

## 5. Independent acceptance decision / next permission

**DS-QV-01/TRIAL-1 ACCEPTED: PASS WITH REVIEW NOTES.**

One paid one-shot authorization slot is **permanently consumed**; never replay TRIAL-1. Under the existing separate six-call owner GO, allow precisely one next invocation `--trial-2` of the **same pinned script** only if local markers/report for TRIAL-1 exist, SHA checksum still matches, TRIAL-2 marker/report absent. TRIAL-2 asks the **identical natural user question M1**, with **neutral Arm B system prompt** (original anti-invention clause removed). It is intended to isolate the **system-level rule's** effect. Independent Architecture review and GitHub evidence required before TRIAL-3.

No Merge, DS-02, production, corpus freeze, confidential Saturn/GT upload or modifications to NEW RAG/Saturn site.
