# DS-LV-02/P6 — WSL Offline Preflight Acceptance

**Date:** 2026-11-17  
**Scope:** one synthetic PDF, P6 Files API text/rich parsing — OFFLINE ONLY  
**Decision:** **ACCEPTED — P6 OFFLINE PREFLIGHT PASS (owner-provided WSL terminal evidence)**  
**Paid status:** **NO P6 API requests executed** at this point.

## Source provenance

- Pinned source commit `d7bd20557b362b90c5676f9b6f18dce2cf7fc9ca`.
- Python file `scripts/validation/ds_lv_02_p6_files.py`, Git blob `3ef0b10108d8133ed4088c0adad4071aaea01ca4`.
- Owner-reported WSL `sha256sum` for script: `35c2e9b8ca89b2de75395f8097b3061e1d4417e3b56c1855c99ee48f7808c0a4`.
- Exact local synthetic fixture `fixtures/ds-lv-02-p6-synthetic.pdf`: SHA256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286`.

## Owner-provided observations

| Gate | Evidence / outcome |
|---|---|
| `logs/ds-lv-02-p6-text-attempted.marker` absent | `test ! -e` succeeded |
| `logs/ds-lv-02-p6-rich-attempted.marker` absent | `test ! -e` succeeded |
| Download pinned Python with `curl --fail --retry 0` | no error |
| Python `-m py_compile` | no error |
| `--self-test` | **DS-LV-02 P6 OFFLINE SELF-TEST: PASS** |
| Calls and cost | **NETWORK REQUESTS: 0 / API COST: $0** |
| PDF SHA-256 | `sha256sum -c`: `fixtures/ds-lv-02-p6-synthetic.pdf: OK` |
| `pdfinfo` | **Pages: 1** |
| `pdftotext` | `Device FENIX-17; Capacity 12.4 L; Code TX-731` |
| `pdftotext` | `Device ORBIT-5; Capacity 6.8 L; Code RB-204` |
| Python SHA-256 | `35c2e9b8ca89b2de75395f8097b3061e1d4417e3b56c1855c99ee48f7808c0a4` |
| Final terminal marker | `DS-LV-02 P6 PREFLIGHT: PASS` |

## Architecture acceptance

Preflight is **PASS** for synthetic PDF byte identity, one-page page count, extractive text consistency, self-test diagnostics and local script compilation **per owner-provided WSL output**. The GitHub script was re-opened in read-only mode and its implementation inspected. The owner-reported runtime SHA-256 has **not been independently recalculated from WSL filesystem by Architecture Session A**.

This proves no live DeepSeek Files API behavior yet: upload/parsing, expiry, model answer, file deletion and billing remain untested.

Official docs independently reviewed 2026-11-17:
- https://api-docs.deepseek.com/guides/files_api/
- https://api-docs.deepseek.com/guides/document_parsing/
- https://api-docs.deepseek.com/api/delete-file/
- https://api-docs.deepseek.com/api/create-chat-completion/

The upload form includes purpose before file, lifetime 3600 seconds, returns `file-api-` ID with `expires_at`. The Chat Completions user content references `{"type":"file","file_id":"..."}`, and cleanup expects DELETE `deleted:true` followed by GET reporting 404.

**Next permitted subgate:** P6-TEXT, one owner-approved cycle with at most 4 HTTP requests, not exceeding P6 budget allocation (organizational $0.010 for first of two variants; actual provider hard cap not available). Use existing pinned script unchanged, and do not retry any attempt.

**Stop conditions:** missing/uncertain upload ID, missing expiry, Chat error, delete status not acknowledged, GET not 404, cost issue or any unexpected request. Even after an error, do not start P6-RICH until Architecture Session A independently accepts and verifies deletion.

No P7–P9 execution in this subgate, no Merge, DS-02, or writes to NEW RAG / Saturn site.
