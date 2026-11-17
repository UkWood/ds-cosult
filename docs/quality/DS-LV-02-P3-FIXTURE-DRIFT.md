# DS-LV-02/P3 — Fixture Drift & Evaluator False-Pass Risk

**Дата:** 2026-11-17  
**Severity:** IMPORTANT (quality of independent validation)  
**Scope:** P3 URL Reading test fixture + automatic scoring, not DeepSeek endpoint implementation.

## Finding

P3 script `scripts/validation/ds_lv_02_p3_url_read.py` checks for the substring `example domain` in the model answer after one completed `read_link`. This fails to distinguish **HTML document title** from **HTML H1**.

The current fetched page `https://example.com/` (2026-11-17) has `<title>Example Domain</title>`, body `<p>...` and **no H1**. Historic HTML examples contained H1, which misled test design.

DeepSeek returned (Chinese) **no explicit H1, page title Example Domain** — consistent with live page. Therefore: `P3_TOOL_CAPABILITY=PASS`, `H1_EXTRACTION_TEST=INVALID_FIXTURE`, `LANGUAGE=DEVIATION`. Do **not** call DeepSeek's refusal to invent an H1 a factual error.

## Required fix before broader testing

1. Use a controlled public **versioned fixture** with SHA-256-pinned HTML bytes and known exact `<title>`, `<h1>`, field relationships. Live `example.com` is useful for network smoke but not for a frozen positive-H1 benchmark.
2. Judge **tool invoked/completed** separately from **source claim fidelity**, **language**, **citation trace**, **cost**, **security**.
3. Three mandatory offline regression classes (run on synthetic HTML without API requests):
   - A: `<title>Example Domain</title>` + `<p>...</p>` with **no H1**. Correct answer: «H1 нет; название страницы Example Domain».
   - B: `<title>Example Domain</title>` + `<h1>Main heading X</h1>`. Correct answer: **Main heading X**, not document title.
   - C: Content mentions `Example Domain` but explicitly assigns incorrect H1. Result must **fail H1 fidelity**, irrespective of substring match.
4. Do not auto-mark PASS for a mere title-string occurrence or `HTTP 200`.
5. Persist the raw source bytes SHA and timestamp for future HTML fixture, but not DeepSeek encrypted `signature`, full reasoning or key.
6. Retain original P3 WSL script, original reported result and immutable SHA as **historical evidence**; implement any corrected tests in a new uniquely named script after architecture-approved scope.

## Source comparison limitations
- Independently re-fetched `https://example.com/` current semantic HTML (no H1).
- Public HTML source example at https://allrighttools.com/view-page-source/ corroborates page without H1, while older HTML snippets on the Internet contain H1.
- Independently reviewed source is **not a byte-for-byte copy of DeepSeek's own fetched source**, which is encrypted in tool `signature`; do not overclaim deterministic reproduction.

## Disposition
- Original P3 executed / accepted for **tool availability**.
- H1 positive extraction benchmark invalidated; not reusable without correction.
- No additional DeepSeek call permitted by exhausted P3 budget.

## Independent user-supplied static HTML snapshot (2026-11-17)

A separate user-uploaded file `Example Domain.html` was inspected, size **577 bytes**, SHA-256 `25ddf2c883e0d1958ea971d279a7e4f0fd446724ee3db7db19dadabd4a62e484`. It includes `<title>Example Domain</title>` and body paragraph `<p>...`, with **no H1**. This strengthens the observation that the original P3 H1 expectation was stale. The original file bytes are **not published** and do not prove exactly what DeepSeek's server-side Fetch saw.
