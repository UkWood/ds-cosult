# DS-LV-02 — Simplified Operator Input Protocol

**Дата:** 2026-11-18  
**Решение владельца:** «Убери из следующих скриптов лишнюю проверку моих осознанных действий - Enter P...-APPROVED.»  
**Decision:** **ACCEPTED, EFFECTIVE IMMEDIATELY FOR P7–P9 AND FUTURE VALIDATION SCRIPTS**.

## Operator experience

- **Remove** scripted extra consent strings / typed phrases such as `P7-APPROVED`, `P8-APPROVED`, `P6-LIST-APPROVED` and the corresponding `input(...)` gate.
- The **explicit user approval in the project conversation and formal approved limits** is sufficient. Do **not** ask for a redundant magic phrase inside a WSL script.
- The invocation of a specific `--execute-once` flag after a Git-pinned offline preflight is intentional operator action. The user continues to run **one command at a time** and hands off output for architecture acceptance.
- Keep only `getpass` for local DeepSeek API-key input; do not print or persist the key. Keep a TTY check, but **no extra confirmation question**.
- Preserve **fail-closed security**: SHA-256 pinning for code/fixture, exclusive one-attempt marker, no retries or redirects, per-stage HTTP and organizational monetary allowances, read-only/offline modes, redacted JSON, and stage dependency gates.
- Never retry or bypass previously consumed `P6` attempts. Already accepted source scripts and raw logs `P1–P6` stay unmodified for audit.

## P7 specific application

The user successfully executed offline preflight on previous P7 script from commit `21c47b020b0951a3109c72b3d1cae8df4e5bb6af`, WSL SHA-256:

`43c889db1e4a2a5ef2729240eb6dd5ce50f4d7b86c1744644da62ef07a489024`.

Old P7 offline checks PASS (`py_compile`, `--self-test`, pinned PDF hash, 0 HTTP / $0), but the code is **superseded before a paid call** because user requested removing the typed approval string.

Only source change to `scripts/validation/ds_lv_02_p7_ocr.py`: delete the two-line interactive `input("...P7-APPROVED")` gate. Keep TTY check, local `getpass`, pinned synthetic PDF, exclusive one-attempt marker, single POST `/v1/tools/ocr`, and all existing safety logic.

**Mandatory consequence:** the P7 script file content SHA-256 changes. Before the live test, perform a **new zero-network WSL offline preflight** on this new Git-pinned version; do not use prior source SHA or call `--execute-once` until the new preflight has passed. The blanket GO remains valid; no extra cost authorization required. P7 paid **NOT EXECUTED** at the time of this decision.

## P8 / P9

When implementing P8 (up to four Chat Completions posts) or P9 (offline analysis), use the same no-magic-phrase operator protocol from the outset. P8 only after independent P7 acceptance; P9 only after P8. Keep the same organizational budgets and no-retry constraints.

No Merge, no DS-02, no new RAG changes and Saturn site remains read-only.
