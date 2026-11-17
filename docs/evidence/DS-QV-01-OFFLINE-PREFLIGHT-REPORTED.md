# DS-QV-01 — Owner-Reported WSL Offline Preflight Evidence

**Recorded:** 2026-11-18  
**Test phase:** DS-QV-01 offline preflight ONLY  
**Source:** owner terminal output, `~/ds-consult-validation` (Ubuntu WSL)  
**Status:** **OFFLINE PREFLIGHT PASS — Architecture review separately required**  
**DeepSeek paid HTTP:** 0  
**DeepSeek API cost:** $0

## 1. Owner's executed steps

The owner pasted a complete WSL command transcript for the approved single offline preflight. The execution:

1. Applied `set -euo pipefail` and `umask 077`, changed directory to `~/ds-consult-validation`.
2. Refused overwriting an existing destination `scripts/validation/ds_qv_01_no_hint.py`.
3. Created a private temp file under `scripts/validation/`.
4. Downloaded immutable source from `https://raw.githubusercontent.com/UkWood/ds-cosult/75dff3402034225aa8ca324170bd1aaa23381de4/scripts/validation/ds_qv_01_no_hint.py` by `curl --fail --silent --show-error --location --retry 0 --max-time 30`.
5. Verified the temp file against expected source SHA256 **`1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`**: `OK`.
6. Renamed to final local path; `python3 -m py_compile` exited without errors.
7. Ran `python3 "$target" --self-test`; validated all six cases, three pinned P8 answer hashes, pairwise A/B system controls, and absence of user refusal hints with **zero provider requests**.
8. Final `sha256sum "$target"` matched the initial pinned checksum.

## 2. Sanitized original terminal excerpt

```text
scripts/validation/.ds_qv_01.lmmVLR: OK
DS-QV-01 OFFLINE SELF-TEST: PASS
FIXTURE: 3 P8 PINNED REPLIES | CASES: 6 | ARMS: A/B
NATURAL QUESTIONS: M1 M2 K1 | USER HINTS: NONE
MODEL: deepseek-flash | THINKING: disabled | TOOLS: none
NETWORK REQUESTS: 0 | API COST: $0
PAID TRIALS: REQUIRE SEPARATE OWNER NUMERIC GO
1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7  scripts/validation/ds_qv_01_no_hint.py
DS-QV-01 OFFLINE PREFLIGHT: PASS
```

## 3. Source provenance

- Source commit: `75dff3402034225aa8ca324170bd1aaa23381de4` (fixed GitHub raw URL).
- Git blob: `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`.
- SHA256 of complete UTF-8 source: `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`.
- Offline fixture loads **public synthetic history only**; existing P8 private JSON is not read or rewritten. No restricted Saturn data involved.
- The only reported network operation was retrieving public **GitHub source bytes**; "0 network requests" in `--self-test` refers specifically to **zero DeepSeek API/model calls**, not to the earlier public GitHub download.

## 4. Evidence boundary

Architecture saw the owner terminal transcript, **not** remote access to WSL. The transcript supports Python compilation and offline self-test success. It does not independently prove the runtime behaviour of any future paid trial, DeepSeek invoice, or statistical abstention reliability.

**No numeric paid GO has been received for DS-QV-01.** Existing DS-LV-02 quotas remain exhausted. No `--trial-N` was run; no DeepSeek key was requested or published.

The next step is independent Architecture acceptance of this offline evidence, then separate consent on trial count and organizational dollar ceiling before **any** paid API request.
