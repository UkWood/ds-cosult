# DS-LV-02/P7 — Revised OCR Script WSL Offline Preflight Acceptance

**Date recorded:** 2026-11-18  
**Test:** Direct DeepSeek OCR, one synthetic PDF page; revised operator UX with no typed confirmation phrase  
**Decision:** **OFFLINE PREFLIGHT PASS — ACCEPTED**  
**P7 paid status:** **NOT EXECUTED**

## Source pin and exact user-provided evidence

The owner executed the revised P7 script from pinned Git commit `6779014bfd21e4749e1ff090ad4b52154530c342`, `scripts/validation/ds_lv_02_p7_ocr.py`, Git blob `b2901a91df937999558a38b357b745c23f4f7f7a`.

Owner-reported local SHA-256 of the revised script: `7829870d2fe42fb33f1ba7c70b3f739e899a5ab6c10fe076903d3f12e5b6c18c`.

Ubuntu WSL observations:
- `test ! -e logs/ds-lv-02-p7-ocr-attempted.marker`: passed.
- `test ! -e logs/ds-lv-02-p7-ocr-redacted.json`: passed.
- Pinned `curl --fail --retry 0` download: no errors.
- `python3 -m py_compile scripts/validation/ds_lv_02_p7_ocr.py`: no errors.
- `python3 scripts/validation/ds_lv_02_p7_ocr.py --self-test`:
  ```
  DS-LV-02 P7 OCR OFFLINE SELF-TEST: PASS
  FIXTURE SHA256: 069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286
  NETWORK REQUESTS: 0 | API COST: $0
  ```
- Final `DS-LV-02 P7 REVISED PREFLIGHT: PASS`.

The fixture SHA-256 is checked inside the self-test by `pinned_pdf()`, and is the same one-page synthetic PDF used by P6. No API key was required; **no external DeepSeek requests or charges in preflight**.

## Independent source review

Reopened committed script via GitHub after WSL output; verified:
- **No `input("...P7-APPROVED")`** and no other redundant typed approval phrase.
- Retains TTY check, hidden `getpass` key entry, exclusive `O_EXCL` attempt marker, no redirects, no retry.
- Local fixture SHA-256 pin, single-page guard, no real Saturn PDF or private benchmark files.
- One `POST https://api.deepseek.com/v1/tools/ocr` with multipart `purpose=text_recognition` and the pinned PDF, no `POST /files` and no chat call.
- `--self-test` works offline and `--execute-once` is the only live mode.
- Response evaluated for page count, page index, text, finish_reason and required synthetic literals; raw OCR response and credentials not printed.
- HTTP failure and unexpected error JSON are not treated as a PASS.

This is **offline readiness only**. Actual OCR request/recognition, page-billing, latency and returned API schema are untested until live P7.

## Architecture decision

**ACCEPT P7 revised offline preflight PASS.** Proceed to exactly **one paid P7 OCR POST**, under the owner's already recorded P6–P9 blanket GO, **organizational $0.01 USD P7 allowance** (not a provider hard cap), maximum **1 HTTP attempt**. No explicit typed `P7-APPROVED` confirmation is required; the user manually runs the pinned `--execute-once` command and enters only their API key locally.

Before execution recheck the owner's reported script SHA-256 and fixture SHA-256, absence of attempted marker and report. This live command exhausts P7 GO even if error/timeout; **no automatic/manual repeats**. P8 remains gated until P7 independently reviewed.

No Merge, DS-02, production or NEW RAG/Saturn-Main-Site edits. Original P7 and original P6 scripts preserved in Git history.
