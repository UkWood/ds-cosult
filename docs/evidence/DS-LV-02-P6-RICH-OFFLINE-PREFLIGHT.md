# DS-LV-02/P6-RICH — Offline WSL Preflight Acceptance

**Дата записи:** 2026-11-18  
**Тип:** synthetic PDF / Files API `rich_layout_recognition` (offline preparation only)  
**Architecture result:** **OFFLINE PREFLIGHT PASS**  
**Live P6-RICH:** **NOT YET EXECUTED**.

## Pinned source and WSL evidence

Pinned Git commit: `b6f6f056990f698b170a880f54277f8157ab12a9` in `UkWood/ds-cosult`, Draft PR #1.

- Script: `scripts/validation/ds_lv_02_p6_rich_safe.py`.
- Git blob SHA `83659995ba1d2c35795c8a5cb0d28afa58e1c251` (read back from PR branch unchanged).
- User-reported local WSL SHA256 `5ac81b7552d543c73303fb01ec71e1a2e4bb643c520c23d9ba62322dcb47e83b`.
- Pinned synthetic one-page PDF SHA256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286`.
- User terminal shows both `test ! -e logs/ds-lv-02-p6-rich-attempted.marker` and `test ! -e logs/ds-lv-02-p6-rich-redacted.json` succeeded.
- `curl --fail --retry 0` downloaded script from pinned commit without errors.
- `python3 -m py_compile scripts/validation/ds_lv_02_p6_rich_safe.py` succeeded.
- `python3 ... --self-test` printed:
```
DS-LV-02 P6 RICH SAFE OFFLINE SELF-TEST: PASS
FIXTURE SHA256: 069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286
NETWORK REQUESTS: 0 | API COST: $0
```
- `sha256sum -c`: `fixtures/ds-lv-02-p6-synthetic.pdf: OK`.
- Final marker: `DS-LV-02 P6-RICH PREFLIGHT: PASS`.

**Date caveat:** the WSL transcript did not contain its own UTC execution timestamp; `2026-11-18` is this acceptance record's date, not a claimed precise WSL execution time.

## Architecture review of pinned Python source

Reopened exact script in GitHub after owner report; no change to source Git blob. Verified:
- `--self-test` works without network/key; `--execute-rich` is the **only live mode**; original P6-TEXT code is separate, unchanged, never retried.
- Runtime requires archived P6-TEXT report and independent `GET /files` list result with matching file-ID SHA, `deleted:true` ack and complete absent file list **observed before expiry**.
- Local synthetic fixture bytes are verified before upload, no real Saturn files, private Core/GT or customer data.
- One-upload-per-variant attempt marker `os.O_EXCL`, no redirects/retries, hidden key, private local file-ID journal, 3600s expiry.
- Rich cycle planned: `POST /files` `purpose=rich_layout_recognition` → one Chat Completions with `file_id` → `DELETE /files/{id}` → **one filtered complete `GET /files`** for absence, at most **4 HTTP attempts**.
- Independent absence gate requires valid complete `object:list` response, `has_more:false`, target absent; otherwise false/stop, not an invented GET404.
- `answer_preview` and usage are diagnostic only; later benchmark accuracy requires examining actual returned technical facts.

## Decision and execution scope

**Accept P6-RICH offline readiness PASS** from owner-provided terminal output.

P6 HTTP used so far: **5/9** (4 P6-TEXT + 1 diagnostic), leaving **4/9** for exactly one P6-RICH cycle, under organizational P6 allowance **$0.02 total**, first/second variant target **$0.01 each**, P6–P9 organizational **$0.05 total**. Organizational targets are **not provider-enforced dollar caps**.

Proceed with one live `--execute-rich` **only** after verifying owner-reported script SHA256 and fixture SHA256 and absence of rich attempt marker/report/private journal. User enters `P6-APPROVED` and API key locally via getpass. **No re-run after error, timeout, unexpected output, or cleanup uncertainty.**

P7–P9 staged, no parallel test, no Merge, no DS-02, no writes to NEW RAG / Saturn site.
