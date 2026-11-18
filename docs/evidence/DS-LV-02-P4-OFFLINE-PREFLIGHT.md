# DS-LV-02/P4 — Linux/WSL Offline Preflight

**Дата:** 2026-11-17  
**Test ID:** DS-LV-02/P4 native `deepseek_web_search`  
**Status:** **OFFLINE PREFLIGHT PASS (based on user-provided terminal output)**  
**Paid P4 status:** **NOT EXECUTED / NOT AUTHORIZED UNTIL EXPLICIT NUMERIC GO**

## Source and observations

Script fetched from pinned source commit `33a784c1f3f526a77226bfe2d26ab30e535fe3d1`:

`scripts/validation/ds_lv_02_p4_web_search.py`

The owner provided a complete WSL command output showing:
- `test ! -e logs/ds-lv-02-p4-attempted.marker` — passed, no marker at preflight.
- `test ! -e logs/ds-lv-02-p4-redacted.json` — passed, no P4 report at preflight.
- `curl --fail --silent --show-error --location --retry 0 --max-time 30` — completed without error output.
- `python3 -m py_compile` — returned without error.
- `python3 ... --self-test` — `DS-LV-02 P4 OFFLINE SELF-TEST: PASS`.
- Script output: `NETWORK REQUESTS: 0 | API COST: $0`.
- `sha256sum`: `c10bd4a6b22aedb74f059a1d089c089e6686f70c6b247c993b315bd2710ba0bd` (reported by local WSL).
- Final `DS-LV-02 P4 PREFLIGHT: PASS`.

The self-test validates synthetic scenarios for: successful completed search/citation matching, tool declared but not called, search results without matching citations, and JSON error despite HTTP 200. **No real search tool execution was tested.**

## Acceptance boundary

**Architecture Session A: ACCEPTED P4 OFFLINE PREFLIGHT ONLY.** Evidence is the local terminal output provided by owner, not an independent real API call or an independent SHA-256 recalc of the WSL file.

The script is unchanged in GitHub; local SHA-256 is owner-reported, not duplicated as a Git blob hash. Neither API key nor raw response supplied. No DeepSeek cost was incurred by this preflight.

**Next gate:** explicitly confirm **one paid Chat Completions HTTP POST**, proposed organizational spending limit **$0.01 USD**, with recognition that internally managed Search/Fetch may generate more than one billed unit. This is **not** a provider-enforced hard cap. P4 MUST NOT RUN without this numeric GO.

P1-P3 remain accepted under their limited scopes. P5-P9 NOT AUTHORIZED. No DS-02, Merge, site writes or NEW RAG changes.
