# DS-LV-02/P6 — Synthetic Files API Text/Rich Parsing (Proposal Only)

**Date:** 2026-11-17  
**Status:** **P6 OFFLINE PREFLIGHT PASS; P6-TEXT CONTROLLED EXECUTION NEXT, NO PAID CALL YET**

## Objective
Determine whether direct DeepSeek Files API can ingest a simple **synthetic public fixture** and make text- and rich-layout-parsed content available for model answers, with evidence of file lifetime, provenance and privacy controls. This is **not** a Saturn PDF corpus test and does not approve uploading company files.

## Scope and potential provider transactions
- Create a new synthetic one-page PDF/Office-style fixture locally, containing a unique arbitrary table and unambiguous labels; record SHA-256. Do not use real company private documents, private benchmark Core/GT, personal information, logos or customer data.
- Compare `purpose=text_recognition` with `purpose=rich_layout_recognition` using **two separate uploads** with recorded file IDs.
- For each upload, set retention policy explicitly using `expires_after[anchor]=created_at` and `expires_after[seconds]=3600`; verify exact API contract in official Files docs before coding.
- Each parsing approach requires a separate model request referencing the returned file ID, plus explicit `DELETE /files/{file_id}` and verification that deletion succeeded. The two approaches must use identical questions and independently approved Ground Truth for the synthetic table.
- Count upload, parsing/recognition, read/generation and deletion operations separately; confirm billable pages and estimated token usage.
- A safe error path **must attempt deletion** of any successfully uploaded file even if later parsing or generation fails. Missing confirmation must be escalated to the owner immediately.
- Require explicit owner approval for sending even synthetic content to DeepSeek and for paid requests. Do not assume P5 budget applies.

## Before GO
1. Research exact upload/delete/retention and billable page contracts; separately assess file-type support and expiry semantics.
2. Prepare offline fixture and client simulation only; upload nothing to provider.
3. Propose total HTTP request count, worst-case achievable control, money limit and retention risks.
4. Wait for owner approval before any upload or paid call. P7..P9, Merge, DS-02 and production not authorized.

**P5 outcome:** tool-capability accepted with review notes. Full answer source correctness remains to be reviewed separately.

## Controlled implementation under blanket owner GO (2026-11-17)
The owner authorized phases P6–P9 with prudent limits. Formal `DS-LV-02-P6-P9-OWNER-BLANKET-GO.md` allocates **P6 total $0.02 organizational risk** and at most **8 external HTTP attempts** (4 per independent variant). Non-retry, no actual Saturn PDFs, one-hour retention + required DELETE/GET proof. Test script `scripts/validation/ds_lv_02_p6_files.py` generates a synthetic one-page PDF and has `--self-test`, `--execute-text`, `--execute-rich` (separate owner-controlled Linux invocations); **only --self-test may run until preflight is accepted**, even under blanket GO. The file includes fake FENIX-17/ORBIT-5 capacities and two unlabeled red/blue squares; rich detection of figures is not guaranteed. Do not treat color absence as tool failure without reviewing returned parse behavior.

## P6 Offline Linux preflight closure — 2026-11-17
Owner WSL outputs: `py_compile` PASS; `--self-test` PASS, 0 network/$0; fixture local SHA256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286` `OK`; 1 PDF page; text extraction confirms both synthetic rows. Python local SHA256 `35c2e9b8ca89b2de75395f8097b3061e1d4417e3b56c1855c99ee48f7808c0a4`. Accepted as **offline readiness only**; report `../evidence/DS-LV-02-P6-OFFLINE-PREFLIGHT.md`. Next **P6-TEXT only**, ≤4 HTTP; GET/DELETE must be verified before P6-RICH is considered.
