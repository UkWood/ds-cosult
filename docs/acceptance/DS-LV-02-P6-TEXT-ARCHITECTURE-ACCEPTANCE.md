# DS-LV-02/P6-TEXT — Architecture Acceptance and Cleanup Anomaly

**Date:** 2026-11-17  
**Project:** DS-консультант / Direct DeepSeek  
**Result:** **PARTIAL PASS — TEXT EXTRACTION PASS; DELETION ACKNOWLEDGED; INDEPENDENT ABSENCE VERIFICATION INCONCLUSIVE**  
**Next subgate:** P6-RICH **STOPPED** until cleanup diagnosis accepted.

## 1. The authorized P6-TEXT request

Under the owner's P6–P9 blanket GO, P6-TEXT was allocated **≤4 external HTTP attempts** and **$0.01 organizational first-variant allowance** (not a provider hard cap). Owner completed one attempt sequence without retries, on locally pinned one-page synthetic PDF.

- Upload `POST /files`, `purpose=text_recognition`: **HTTP 200**, file ID successfully received and hashed in redacted output; lifetime `expires_after=3600s` acknowledged.
- Chat `POST /chat/completions`: **HTTP 200**, model `deepseek-flash`, finish `stop`, prompt 184 + completion 96 = 280 tokens.
- Delete `DELETE /files/{file_id}`: **HTTP 200**, `deleted:true` and same ID: provider explicitly acknowledged deletion.
- Subsequent GET `GET /files/{file_id}`: **HTTP 400**; local script only logged status and discarded JSON error body. `deletion_verified_absent=false`.

Script final status: `STOP_DELETION_VERIFICATION_UNCONFIRMED`. **The scripted stop condition operated correctly under its original overly specific 404 expectation.**

## 2. Grounded text answer

The model answered:
- FENIX-17 — capacity 12.4 L, code TX-731;
- ORBIT-5 — capacity 6.8 L, code RB-204.

Both match byte-pinned PDF text layer. The model stated the graphic was unavailable and did not invent the two colors or number of shapes. That is a **reasonable/appropriate limitation for text_recognition**, not a factual failure. The synthetic PDF actually contains two vector squares (red and blue) but their colors are not declared as text.

This is a positive Files API text parsing + model reference capability result, independent of cleanup finding.

## 3. Official API contract review

Re-read on 2026-11-17:
- https://api-docs.deepseek.com/api/delete-file/ — **HTTP 200** with `deleted:true` and `id` is specified **success response** to DELETE.
- https://api-docs.deepseek.com/api/retrieve-file/ — **GET success HTTP 200** is documented. The reference **does not specify** the exact response code for a deleted ID.
- https://api-docs.deepseek.com/quick_start/error_codes/ — **HTTP 400** is general Invalid Format; without body it cannot be used as proof of absence.
- https://api-docs.deepseek.com/api/list-files/ — **GET /files** can list files with `purpose=text_recognition`, `limit≤1000`, `has_more` pagination marker.

**Quality finding CR-P6-01 (IMPORTANT):** The test's mandatory `GET /files/{id} = 404` expectation is not independently grounded in the provider documentation. Do not reinterpret GET 400 as a documented 404-like success, nor override the original JSON's `deletion_verified_absent=false`. The actual DELETE acknowledgement is genuine and should be retained as a separate **provider-deletion PASS**, while **independent absence gate** remains UNRESOLVED.

Exact file expires according to response at **2026-11-17T21:34:56Z**. This is a fallback retention boundary, not evidence of a deletion already completed or verified.

## 4. Cost and custody

`estimated_peak_cost_usd=0.0003954` includes illustrative one-page parsing fee ($0.000225) plus 184 prompt and 96 completion tokens at published peak Flash rates. Actual provider bill **unknown**, no retry.

The private original ID is only in the owner's WSL journal. The GitHub record stores its SHA-256, not the ID, API key, or any other account files.

## 5. One extra read-only diagnostic under delegated prudent limits

Original P6 budget set 8 HTTP attempts total (4 Text + 4 Rich). To resolve the privacy cleanup ambiguity, Architecture amends the **HTTP count only**:
- P6 **≤9** HTTP requests (4 Text already used, **1 extra read-only list**, 4 Rich reserved);
- P7 **≤1**, P8 **≤4**, P9 **0** → total **≤14**;
- **same $0.05 total organizational budget**, P6 **same $0.02** sub-budget, no additional upload or chat.
- This is a cautious procedural adjustment within the owner's blanket authorization to set prudent limits. If the diagnostic shows unresolved retention, **STOP and request new consent for further corrective network operations**.

A new script `scripts/validation/ds_lv_02_p6_list_check.py` performs a single filtered `GET /files?limit=1000&order=desc&purpose=text_recognition`, checking the one locally stored target `file_id` (SHA256 must match existing redacted evidence). It returns **only redacted status**, total records count, `has_more`, whether target ID appeared. No raw file IDs, other filenames or entire list saved or printed.

- **PASS independent absence** only on HTTP 200, `object:list`, correct `data[]`, `has_more:false`, target not present.
- **FAIL** if target is listed; **INCONCLUSIVE** if list paginated, invalid, or failed.
- The diagnostic may verify target absence but not uniquely prove whether absence resulted from DELETE or expiry. DELETE had already returned successful acknowledgement.

The new script has offline `--self-test`; **do not perform live `--check-target` until offline preflight accepted**. One read-only GET, exclusive attempt marker, no retry. P6-RICH remains blocked until architecture reviews output.

## 6. Acceptance decision

**P6-TEXT processing: PASS**, **provider deletion acknowledgement: PASS**, **independent file absence: INCONCLUSIVE**. Overall **PARTIAL WITH REVIEW NOTES**, not a full clean P6 gate.

Do not modify or rerun original P6-TEXT script; keep its output immutable. Do not bypass P6-RICH guard before explicit architecture re-review; neither P7 nor P8 should start early. No MERGE or production.
