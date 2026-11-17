# DS-LV-02/P6 — Final Independent Architecture Acceptance

**Date:** 2026-11-18 (evidence runtime 2026-11-17 UTC)  
**Project:** DS-консультант, independent from NEW RAG  
**Decision:** **P6 PASS WITH REVIEW NOTES** — both text_recognition and rich_layout_recognition capabilities demonstrated on the same pinned synthetic one-page PDF.  
**Billing status:** estimated only; provider invoice not verified.  
**Owner GO:** P6 allocated HTTP allowance **9/9 exhausted**; no repeats.

## 1. Scope and provenance

Synthetic one-page PDF byte identity SHA-256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286`, 1031 bytes, contains the source facts:

- FENIX-17: 12.4 L, TX-731.
- ORBIT-5: 6.8 L, RB-204.
- Two unlabeled vector squares: one solid red, one solid blue.

No Saturn PDF, technical source document, private Core/GT, user/customer data or production data was uploaded.

Owner's P6-TEXT run: 2026-11-17T20:34:54Z, one original 4-request Files API cycle. Provider DELETE 200/deleted true. After an overly strict post-delete per-ID GET=404 expectation yielded HTTP400, the owner ran one separate **read-only list diagnostic** at 20:52:28 UTC: full `text_recognition` list empty (`has_more:false`) **before** the file's 21:34:56 UTC expiry. See `DS-LV-02-P6-TEXT-CLEANUP-CLOSURE.md`.

Owner's P6-RICH run: 2026-11-17T21:11:27Z, safe pinned corrected RICH-only script `scripts/validation/ds_lv_02_p6_rich_safe.py`, passed WSL offline preflight before execution.

## 2. Evidence matrix

| Criterion | P6-TEXT | P6-RICH |
|---|---|---|
| `POST /files` status | HTTP200 | HTTP200 |
| `POST /chat/completions` | HTTP200 | HTTP200 |
| File parsing purpose | `text_recognition` | `rich_layout_recognition` |
| FENIX-17 12.4 L TX-731 | **correct** | **correct** |
| ORBIT-5 6.8 L RB-204 | **correct** | **correct** |
| Graphic count/color | correctly states unavailable; no invention | **two squares, red and blue** |
| `DELETE /files/{id}` | HTTP200 `deleted:true` | HTTP200 `deleted:true` |
| Independent complete list | absent before TTL, via separately authorized GET | absent immediately, HTTP200 `has_more:false`, 0 items |
| Model finish | stop | stop |
| Prompt tokens | 184 | 567 |
| Completion tokens | 96 | 69 |
| Total model tokens | 280 | 636 |
| Model bill + one parsed page (peak estimate) | **$0.0003954** | **$0.0004779** |
| Runtime latency | 4,595 ms | 5,179 ms |
| Provider invoice | unknown | unknown |

P6-RICH owner-provided redacted JSON is preserved in `docs/evidence/DS-LV-02-P6-RICH-RESULT.json`; original P6-TEXT evidence retained separately. RICH file-ID is kept private in the WSL journal; only SHA-256 `358a6b7747272cd25f54e637c033daec75d5feead78b3671bce4289ab43be55f` recorded.

## 3. Independent validation

Official DeepSeek documentation (rechecked 2026-11-18):
- https://api-docs.deepseek.com/guides/files_api/ says `text_recognition` hides figures from the chat model and `rich_layout_recognition` exposes text plus figures, with increased input tokens and automatic figure extraction;
- https://api-docs.deepseek.com/guides/document_parsing/ notes that not every figure is guaranteed detected;
- https://api-docs.deepseek.com/quick_start/pricing/ states file parsing **$0.225 / 1000 pages**, model tokens additionally billed at Flash rates.

The two model answers are directly consistent with pinned PDF ground truth and expected difference between Files purposes. This confirms the capability for **simple geometric figures in a synthetic PDF**, **not** accuracy for complicated technical schematics or real Saturn device documents.

## 4. Cost and budget reconciliation

RICH peak estimate:
- One parsed page $0.000225;
- prompt 567 × $0.30 / 1,000,000 = $0.0001701;
- completion 69 × $1.20 / 1,000,000 = $0.0000828;
- total **$0.0004779**.

TEXT peak estimate previously recorded **$0.0003954**. **P6 total peak estimate = $0.0008733** for two parsing+chat cycles; supplemental read-only List GET has no separately listed successful OCR/parse/search unit fee in the consulted pricing. **This is a rate-based estimate, not provider invoice; do not assert actual debit = $0.0008733.**

P6 request accounting: TEXT 4 + separate independent list check 1 + RICH 4 = **9/9 allowed HTTP requests used**.

Organizational P6 risk budget **$0.02** was not numerically breached by recorded estimates; global $0.05 for P6–P9 remains. These are not technical provider-enforced dollar caps.

## 5. Acceptance remarks

- **PASS** — both documents recognized, model used returned file IDs to answer; textual facts correct.
- **PASS** — P6-RICH recognized two accurately colored squares absent from TEXT response.
- **PASS** — provider acknowledged deletion both times; independent full lists showed absence before expiration. Original GET400 P6-TEXT is **preserved** as a failed *diagnostic assumption*, resolved with separate list evidence.
- **IMPORTANT** — owner-reported redacted outputs are the only real-execution telemetry, not raw provider payload; no direct billing proof.
- **IMPORTANT** — successful figure detection on a simple PDF does not imply reliable grounding for Saturn schematics, complex diagrams, electrical labels, drawings, tables or actual PDF standards.
- **MINOR** — RICH prompts consumed more tokens (567 vs 184), while per-page parsing price same; use RICH selectively when diagrams matter.
- **MINOR** — the original Text script expected GET404 without documentation support; this was corrected in RICH-only script, without changing or rerunning original Text evidence.

## 6. Decision and next gate

**P6 COMPLETE — PASS WITH REVIEW NOTES**, after closing CR-P6-01. P6 live authorization exhausted; no further P6 HTTP requests or reuploads.

**P7 OCR remains staged: only its OFFLINE preflight may run next.** One OCR POST (`/v1/tools/ocr`, synthetic PDF, `purpose=text_recognition`), $0.01 organizational and ≤1 HTTP, after separate WSL preflight acceptance. P8/P9 remain stage-gated; no Merge, no production, no DS-02, no NEW RAG or Saturn site writes.
