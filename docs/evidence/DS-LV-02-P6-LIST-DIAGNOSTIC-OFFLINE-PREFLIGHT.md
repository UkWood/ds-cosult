# DS-LV-02/P6 — File List Diagnostic Offline Preflight

**Дата:** 2026-11-17  
**Сценарий:** `DS-LV-02/P6-TEXT-LIST-CHECK` / independent absence diagnostic  
**Architecture status:** **OFFLINE PREFLIGHT PASS**, based on user-provided WSL transcript  
**API calls:** **0** (self-test only); cost **$0**  
**Live list check:** **NOT EXECUTED**, awaiting one read-only GET under previously authorized blanket budget.

## Immutable source and local evidence

Source repository `UkWood/ds-cosult`, Draft PR #1, pinned script from Git commit `fe79a23d60af6bb5455ec0d6209b76657c147d61`.

Script `scripts/validation/ds_lv_02_p6_list_check.py`; Git blob SHA `ee630fe102de59d53fd98c8a0cedef64920fac96`.

Owner reported from Ubuntu/WSL:
- Both `test ! -e` checks passed for diagnostic attempt marker and redacted report.
- `curl --fail --retry 0` downloaded script from pinned raw GitHub URL without errors.
- `python3 -m py_compile scripts/validation/ds_lv_02_p6_list_check.py` returned cleanly.
- `python3 scripts/validation/ds_lv_02_p6_list_check.py --self-test` printed:
```
DS-LV-02 P6 FILE-LIST DIAGNOSTIC SELF-TEST: PASS
NETWORK REQUESTS: 0 | API COST: $0
```
- Local `sha256sum`: `d12025ca26ddd24b981d4ac27a0e17469d33f50c66e0db0abffd7c9facf3ee57` (owner-reported WSL file bytes).
- Final `DS-LV-02 P6 FILE-LIST PREFLIGHT: PASS`.

The above confirms only local source/syntax/synthetic evaluator checks, not the actual absence of the uploaded file.

## Official Files List contract

Verified official documentation: https://api-docs.deepseek.com/api/list-files/ (2026-11-17):
- `GET /files` accepts `limit` between 1–1000, `order=asc|desc`, `purpose=text_recognition`;
- HTTP 200 body `object:"list"`, `data:[]`, `has_more:boolean`;
- absent target in complete `has_more:false` filtered list is evidence that the target is not listed **at that time**; if `has_more:true`, absence is not proven, and a second GET requires a new architecture decision because the present budget permits only one diagnostic call.

The script's `--check-target` verifies private locally journaled `file_id` SHA-256 against the P6-TEXT report, then issues **exactly one read-only GET**. It reports only target presence status, count, pagination boolean, HTTP status, and time. It does not print or persist raw IDs, other filenames, raw response bodies or credentials. It marks the attempt before the request, prohibits retries and uses hidden API-key input. 
- `PASS_TARGET_NOT_IN_EXHAUSTIVE_LIST` requires HTTP200, valid list structure, `has_more:false` and target ID absent.
- `FAIL_TARGET_STILL_LISTED` means target was found; stop all subsequent file phases and investigate.
- `INCONCLUSIVE` otherwise; do not infer absence from API errors or incomplete listings.

**Important source/provenance caveat:** P6-TEXT upload specified file expiry at `2026-11-17T21:34:56Z`. If diagnostic is performed after expiry, absence may be due to automatic expiry rather than explicit DELETE. Provider `DELETE /files/{id}` separately returned HTTP200 `deleted:true` during original P6-TEXT; that provider acknowledgement remains valid independently.

## Decision and next action

Architecture **ACCEPTS OFFLINE PREFLIGHT PASS**. Proceed **only with one owner-authorized read-only `GET /files` diagnostic under the existing P6–P9 blanket GO**. Budget already adjusted P6 ≤9 HTTP, P6–P9 ≤14 in `docs/tasks/DS-LV-02-P6-P9-OWNER-BLANKET-GO.md`. No change to total organizational $0.05 (not a provider hard monetary cap).

P6-RICH and P7–P9 remain stage-gated until diagnostic result independently reviewed. Original P6-TEXT code, report and private file ID are not altered. No Merge, DS-02 or production.
