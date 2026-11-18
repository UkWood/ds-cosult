# DS-LV-02/P7 — Direct OCR One-Page Conformance Test

**Date:** 2026-11-18  
**State:** **P7 LIVE PASS WITH REVIEW NOTES, 1/1 HTTP USED, NO RETRY**  
**Precedent:** P6 Files API Text/Rich accepted with review notes; P6 budget 9/9 used.  
**Stage allowance:** **$0.010 organizational / 1 HTTP POST max**; no retries; no provider-enforced monetary cap.

## Objective

Independently confirm the dedicated OCR tool endpoint `POST https://api.deepseek.com/v1/tools/ocr` returns per-page recognized text, without using `POST /files`, file_id, or a chat model request.

## Official contract verification

Source: https://api-docs.deepseek.com/guides/ocr/ and https://api-docs.deepseek.com/quick_start/pricing/ (rechecked 2026-11-18).

- `multipart/form-data` includes **exactly** `purpose` and `file` fields, no extra fields; `purpose=text_recognition`.
- Use the same pinned *synthetic one-page PDF* as P6 for cross-method comparison, SHA256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286`, 1031 bytes. No private company or benchmark files.
- OCR endpoint is separate from Files API and does **not** store the document in Files API; no post-OCR DELETE is relevant, and no chat question is sent.
- OCR response may have leading newline keepalives; `json.loads` accepts leading whitespace.
- A successful result must be `object=ocr.result`, `purpose=text_recognition`, `page_count=1`, one `pages[0]` with `index=0`, `text` string and `finish_reason=stop`. Response `usage` token counts are **for reference and not used for OCR billing**.
- Recognized raw page text may include coordinate markup `<｜ref｜>` and `<｜box｜>`; script records marker presence, not an invented clean transcript.
- Any HTTP error or HTTP200 error JSON is failure; incomplete `finish_reason=length` is partial, not PASS.
- One successfully OCR-parsed page has listed rate **$0.225 per 1000 pages = $0.000225** (estimated). Actual amount unknown until provider billing.

## Implementation and stop conditions

`scripts/validation/ds_lv_02_p7_ocr.py` has `--self-test` (zero requests, synthetics) and `--execute-once` (single paid POST). The paid mode is **NOT to be run before the WSL offline preflight has been reviewed**.

- Local hash check against pinned fixture before request; exclusive `logs/ds-lv-02-p7-ocr-attempted.marker`; no retries or redirects; local getpass.
- Redacted diagnostic records HTTP/status, page count, whether each expected synthetic literal appears, OCR text hash, leading excerpt, special coordinate marker presence, and usage for reference only. Never print API key or full raw OCR payload.
- OCR timeout is `185s` to cover official 180s limit; a timeout consumes the only authorization even if service might process afterwards.
- No real data, no repetition, no background service or production.

## Next action

1. Architecture logs P6 acceptance and commits P7 script.
2. Owner WSL downloads exact pinned P7 script, runs `py_compile`, `--self-test`, hash checks and reports script SHA256. **No P7 paid operation in this step.**
3. Architecture acceptance of offline preflight, then one authorized paid P7 call, then independent P7 acceptance.
4. Only afterward consider P8.

No Merge, DS-02, production, NEW RAG or Saturn source writes.

## P7 original offline PASS + removal of redundant confirmation prompt (2026-11-18)
Owner WSL successfully compiled and self-tested the original pinned script (SHA256 `43c889db1e4a2a5ef2729240eb6dd5ce50f4d7b86c1744644da62ef07a489024`), 0 API calls / $0, PDF SHA OK. Evidence `../evidence/DS-LV-02-P7-OCR-ORIGINAL-OFFLINE-PREFLIGHT.md`. Owner requested that further scripts omit `Enter P...-APPROVED` phrases; accepted decision `../decisions/DS-LV-02-OPERATOR-INPUT-POLICY.md`. P7 script has only the two lines for the redundant `input(...)` removed: now local `getpass` follows the TTY+fixture checks directly. No other protections removed. **New source SHA requires new zero-network preflight before the one paid P7 OCR request**; blanket GO / 1 HTTP / $0.01 organizational cap unchanged. P8/P9 will implement no typed confirmation gate.

## Revised script independently accepted offline — recorded 2026-11-18
Revised `ds_lv_02_p7_ocr.py` commit `6779014bfd21e4749e1ff090ad4b52154530c342` owner SHA256 `7829870d2fe42fb33f1ba7c70b3f739e899a5ab6c10fe076903d3f12e5b6c18c` passed `py_compile`, `--self-test`, fixture byte identity checks; DeepSeek requests 0 and API cost $0. Owner confirmation phrase removed as requested, getpass retained. `../evidence/DS-LV-02-P7-REVISED-OFFLINE-PREFLIGHT.md`. **Next one paid `--execute-once` call only** with P7 organizational $0.01, 1 HTTP limit. No retry; P8 gated until result reviewed.

## P7 paid execution completed and accepted — recorded 2026-11-18
One direct OCR POST success HTTP200, 1/1 page, finish stop, all six expected synthetic markers, 485 OCR usage tokens informational only, $0.000225 estimated page fee. Actual billing unknown; no Files API storage. `../evidence/DS-LV-02-P7-OCR-RESULT.json`; `../acceptance/DS-LV-02-P7-ARCHITECTURE-ACCEPTANCE.md`. **P7 CLOSED — 1/1 call consumed.** Next P8 four-turn synthetic Chat Completion dialogue offline preflight, no paid work yet.
