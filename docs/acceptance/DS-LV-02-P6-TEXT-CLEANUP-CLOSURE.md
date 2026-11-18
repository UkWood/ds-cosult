# DS-LV-02/P6-TEXT — CR-P6-01 Resolution: Full List Absence Verified

**Project:** DS-консультант / one-page synthetic Text Files API  
**Diagnostic date:** 2026-11-17 20:52:28 UTC  
**Decision:** **CR-P6-01 RESOLVED — P6-TEXT PASS WITH REVIEW NOTES; P6-RICH ELIGIBLE FOR OFFLINE PREFLIGHT ONLY**  
**Evidence:** `docs/evidence/DS-LV-02-P6-TEXT-LIST-RESULT.json` (owner-provided redacted WSL result).

## 1. Independent one-call diagnostic

Within the earlier approved P6–P9 blanket scope and revised HTTP allowance, owner executed exactly one read-only `GET /files?limit=1000&order=desc&purpose=text_recognition`.

Result:
- `http_requests_attempted=1`, `list_http_status=200`;
- `target_file_listed=false`, `records_returned=0`, `list_has_more=false`;
- `absence_gate=PASS_TARGET_NOT_IN_EXHAUSTIVE_LIST`;
- SHA256 of the private locally journaled file ID `f947c363ad880788ae498498aed2c516e4bdc3610fea0b32ebb71f092823dbb4`, matching the original P6-TEXT redacted report;
- no raw file ID, other file identifiers or other account file content printed or logged, `latency_ms=576`;
- actual billing remains unknown.

## 2. Critical time relationship

- P6-TEXT run began at `2026-11-17T20:34:54Z`. Its **DELETE /files/{id} returned HTTP200 with `deleted:true`**, provider acknowledgement.
- Independent `GET /files` showed target absent at **20:52:28 UTC**.
- The server-reported file expiry was **21:34:56 UTC**, i.e. the independent observation was about **42m 27s BEFORE** automatic expiry.

Together, the provider's affirmative deletion response and full filtered list absence before TTL expiry provide **sufficient independent cleanup evidence for this controlled experiment**, without claiming a mathematical proof of the only possible cause of absence.

## 3. CR-P6-01 final acceptance

Original P6-TEXT output remains `STOP_DELETION_VERIFICATION_UNCONFIRMED`, including `verify_get_http_status=400` and `deletion_verified_absent=false`. It was produced by the old evaluator's unjustified `GET /files/{id} = 404` requirement; **DO NOT overwrite that JSON**.

The later diagnostic is a separate auditable evidence record and closes the independent absence criterion. **P6-TEXT overall: PASS WITH REVIEW NOTES**:
- Files upload and Text recognition PASS;
- chat readback from document PASS (FENIX-17 12.4 L TX-731; ORBIT-5 6.8 L RB-204);
- no fabrication of graphic color/count when unavailable to text-only parser;
- provider DELETE acknowledgement PASS;
- independent absence PASS before expiry;
- actual billing not independently verified.

## 4. Corrected P6-RICH implementation (no paid execution yet)

**Never rerun original P6-TEXT.** Keep old script `scripts/validation/ds_lv_02_p6_files.py` unchanged for audit.

Create a new standalone corrected RICH-only script `scripts/validation/ds_lv_02_p6_rich_safe.py`, which:
- confirms original P6-TEXT report and one-call List diagnostic, matching file-ID SHA and `timestamp_utc < expires_at_reported`;
- supports `--self-test` (zero DeepSeek calls), and only `--execute-rich` live (no TEXT mode);
- for P6-RICH uses **1 POST upload with `rich_layout_recognition`, 1 Chat, 1 DELETE and 1 filtered GET /files** for independent absence, within unchanged **4 HTTP max**;
- requires complete list `has_more=false`, valid items and target absent; errors and pagination are **INCONCLUSIVE** rather than PASS;
- keeps `expires_after=3600s`, private file ID journal, exclusive attempt marker, hidden key, no retries/redirects and safe redacted diagnostics;
- stops if deletion acknowledgement or independent absence fails. If server-side upload is ambiguous and ID unknown, no retry; expiry is safety fallback.

**P6-RICH is authorized in principle under blanket owner GO, but its live execution remains LOCKED until separate successful WSL offline compile/self-test and acceptance.** No new owner spend approval is required within existing P6 limit ($0.02 organizational), max HTTP P6 9 and total P6–P9 14.

## 5. Other restrictions

The synthetic test does not prove handling of real Saturn documents or PDF graphics. P7/P8/P9 remain stage-gated; no Merge, DS-02, production, no NEW RAG / Saturn site writes.

Official API references:
- https://api-docs.deepseek.com/api/delete-file/
- https://api-docs.deepseek.com/api/list-files/
- https://api-docs.deepseek.com/guides/files_api/
