# DS-QV-01 — Owner GO: Six One-Shot Natural-Question DeepSeek Trials

**Date:** 2026-11-18  
**Decision:** **OWNER PAID GO GRANTED / STAGED EXECUTION AUTHORISED**  
**Source of owner approval:** after the completed and independently accepted DS-QV-01 WSL offline preflight, Architecture directly proposed: “Подтверди, пожалуйста: разрешаешь выполнить до 6 платных HTTP-запросов DeepSeek API с общим организационным лимитом $0,01 USD для DS-QV-01?”  
**Owner reply (verbatim):** **«Разрешаю. Делай.»**

## 1. Binding authorization and exclusions

- **Authorized:** up to **6 separate HTTP POST attempts** to the official direct DeepSeek Chat Completions API **under the new DS-QV-01 study**, total **USD $0.01 organizational spending ceiling** (not technically enforced by DeepSeek; actual provider billing remains unknown until independently reconciled).
- **Model:** `deepseek-flash`. `thinking.type=disabled`, `tool_choice=none`, no declared tools, `temperature=0`, `stream=false`, `max_tokens=160`.
- **Six fixed pre-registered conditions:** Arm A (system anti-fabrication instruction included) versus Arm B (that clause removed only); two missing-attribute user queries and one answerable positive control. Natural user questions contain **no direct no-data/refusal hint**.
- **Source:** `docs/tasks/DS-QV-01-NATURAL-QUESTION-ABSTENTION-PROTOCOL.md`; the unchanged frozen synthetic P8 three-turn context is checked with assistant response SHA-256; no real Saturn sources or user secrets.
- **Local executable:** `scripts/validation/ds_qv_01_no_hint.py` from immutable source commit `75dff3402034225aa8ca324170bd1aaa23381de4`, Git blob `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`, locally owner-verified SHA256 `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`.
- **Offline preflight:** PASSED on owner's Ubuntu WSL. Source checksum before/after installation, `py_compile` and `--self-test` PASS; **zero DeepSeek HTTP / $0**. Report `docs/evidence/DS-QV-01-OFFLINE-PREFLIGHT-REPORTED.md`, independent Architecture approval `docs/acceptance/DS-QV-01-OFFLINE-PREFLIGHT-ARCHITECTURE-ACCEPTANCE.md`.

## 2. Execution gates and safeguards

1. This GO authorizes **only the predeclared six one-shot conditions**, not any extra retry or different question. Owner's current direct approval is numeric for all six; individual script-level `Enter ... APPROVED` confirmations are **not required**.
2. Architecture issues **one** WSL command, starting **only with `--trial-1`**. Local one-attempt marker is exclusively created before the POST. No automatic retries, HTTP redirects, script replacements or marker deletion.
3. Architecture independently reviews each owner's sanitized JSON; subsequent trial eligible **only if** previous result is acceptable and recorded as evidence/Acceptance in **existing GitHub Draft PR #1**, keeping original output immutable.
4. Stop immediately on unexpected HTTP, transport error, wrong model, cost-budget uncertainty/overrun, incomplete output, missing previous report/marker, or data privacy issue. A failed/timeout HTTP attempt consumes its authorized call; it is **not** a permission to retry.
5. Per-turn billing is a **token tariff estimate**; provider actual billing **unknown**. The script's `MAX_ORGANIZATIONAL_USD=0.01` is not a true provider account cap or an authoritative invoice. A future request is forbidden when projected/running estimates would exceed the organizational allowance.
6. Hidden API key via local `getpass` only, no key in shell arguments/history/GitHub; `0600` local redacted logs; synthetic public fixture only. **Do not** expose private P8 history, technical Saturn GT or real documents.
7. The old DS-LV-02 P8 **4/4** and P6–P9 **14/14** HTTP permissions remain **exhausted**, and neither is reset or reused by this new GO. The original evidence, separate P8/P9 judgments and QUALITY-P8-01 are immutable.
8. No Merge, DS-02, Corpus Freeze, production deploy, source write to `UkWood/Saturn-Main-Site` (READ-ONLY), or changes to independent NEW RAG.

## 3. Current authorization ledger

- DS-QV-01 paid authorization: **6 maximum one-shot HTTP**, **$0.01 USD organizational total**, **0 used / 6 available** at time of GO.
- **Next permitted step:** checksum-gated owner WSL command `python3 scripts/validation/ds_qv_01_no_hint.py --trial-1`.
- **TRIAL-2 through TRIAL-6 remain stage-gated** until each previous independent Architecture Acceptance. No new source/fixture or other experiment is authorized.

This document records the owner approval and **does not** represent a trial execution or a real provider debit.
