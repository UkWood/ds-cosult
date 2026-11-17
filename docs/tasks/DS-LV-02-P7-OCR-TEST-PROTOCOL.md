# DS-LV-02/P7 — Direct OCR One-Page Conformance Test

**Date:** 2026-11-18  
**State:** **PLANNED / OWNER BLANKET GO ACTIVE / OFFLINE PREFLIGHT NOT YET RUN**  
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
