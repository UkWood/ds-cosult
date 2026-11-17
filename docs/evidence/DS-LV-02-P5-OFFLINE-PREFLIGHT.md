# DS-LV-02/P5 — Offline Linux/WSL Preflight Acceptance

**Date:** 2026-11-17  
**Status:** **PASS — OFFLINE PREFLIGHT ONLY (owner-provided terminal evidence)**  
**Test ID:** DS-LV-02/P5 — Deep Thinking + native Web Search  
**Paid P5:** **NOT AUTHORIZED; NOT EXECUTED**

## Source and execution

Source commit: `4009ad2d17d71c627deb61b0fca3c941f7a27e3a` in `UkWood/ds-cosult`, Draft PR #1.

Script: `scripts/validation/ds_lv_02_p5_thinking_search.py`; Git blob: `537eacb07930059cbd7d704cbda1f907e4fef60b`.

User-provided complete WSL transcript:
- `test ! -e logs/ds-lv-02-p5-attempted.marker` — success.
- `test ! -e logs/ds-lv-02-p5-redacted.json` — success.
- Download via pinned `raw.githubusercontent.com` commit using `curl --fail --retry 0` — success.
- `python3 -m py_compile scripts/validation/ds_lv_02_p5_thinking_search.py` — success, no errors.
- `python3 scripts/validation/ds_lv_02_p5_thinking_search.py --self-test` printed:
  ```
  DS-LV-02 P5 OFFLINE SELF-TEST: PASS
  NETWORK REQUESTS: 0 | API COST: $0
  ```
- Local SHA256, as reported by WSL: `4a9dd93517ae09a1e0f1ec61415d1ab65666cdb127a2d0dd2681c43941882608`.
- Final `DS-LV-02 P5 PREFLIGHT: PASS`.

The Python `--self-test` runs synthetic simulations of successful thinking+search, no actual search call, no thinking evidence, error JSON despite HTTP 200, and safe URL normalization/estimation. No model requests or owner key were used.

## Acceptance and limitations

**Architecture Session A ACCEPTS OFFLINE PREFLIGHT PASS** based on user-provided execution output.

This does **not** demonstrate any actual DeepSeek Deep Thinking + Web Search, retrieval accuracy, source provenance, generated response validity, request duration, provider billing, or cost controllability. The SHA-256 is **owner reported**, not independently rehashed from WSL bytes by Architecture Session A.

The P5 cost investigation in `docs/research/DS-LV-02-P5-SERVER-TOOL-BUDGET-REVIEW.md` found no verified server-side hard spend cap and notes provider-documented ~20 deep-thinking tool actions and potential multiple billed queries per search action.

### Approval gate

No paid P5 invocation has been authorized. Before real run: **separate explicit owner approval** with one Chat Completions HTTP POST, a numeric organizational risk limit, and clear acknowledgement that **the numerical amount is NOT technically enforced** and may be exceeded by uncontrolled server-side Search/Fetch/model work.

Do **not** use `--execute-after-owner-go` until such approval is documented. Do not reset/delete attempt markers to bypass an already used call.

P6–P9 remain unauthorized; no Merge, DS-02, production or new Ground Truth.
