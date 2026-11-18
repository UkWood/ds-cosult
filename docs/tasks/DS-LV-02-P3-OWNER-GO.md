# DS-LV-02/P3 — Formal Owner GO for URL Reading

**Дата:** 2026-11-17  
**Статус:** **OWNER GO EXERCISED — 1 HTTP POST / P3 ACCEPTED WITH REVIEW NOTES**  
**Проект:** DS-консультант, независимый от NEW RAG  
**Цель:** P3 — native `deepseek_read_url` smoke, без Search/Files/OCR и последующих фаз.

## Owner decision

После архитектурного вопроса «Подтверждаете GO для одного платного вызова `deepseek_read_url` с лимитом $0,01 USD?» владелец ответил: **«Разрешаю»**.

Разрешён ровно **1 платный HTTP POST** с организационным пределом **$0.01 USD**. Это **не гарантированный технический hard spending cap** у DeepSeek; серверная стоимость может включать модельные токены и Fetch. Пользователь уведомлён об этом непосредственно перед GO.

## Exact scope

- Endpoint `POST https://api.deepseek.com/chat/completions`.
- Model `deepseek-flash`, `thinking.type=disabled`.
- Only `tools:[{"type":"deepseek_read_url"}]`.
- Last user message contains only one URL to be read: `https://example.com/`; expected page title **Example Domain**.
- `max_tokens=256`, `stream=false`.
- **NO retry, NO redirect, NO second call**, even after timeout or transient HTTP error.
- Key through `getpass` in owner's local Linux/WSL terminal. No key, raw encrypted signature, hidden reasoning, raw response or private Core/GT in GitHub.
- local script `scripts/validation/ds_lv_02_p3_url_read.py`, pinned script commit `4b6bdf5058946337021aade831d09cf34831ecaa`; offline preflight PASS, SHA-256 reported `1de63e655bc84c19fce73076442280946ff099d06d5b3ae8898b4a8cd8fc26e2`.
- The script was written before numerical GO and outputs static `authorization:"P3_BUDGET_OWNER_GO_REQUIRED_BEFORE_EXECUTION"`. **This string is historical and must not be interpreted as a denial of the later explicit GO**. The authoritative owner consent is in this document, with matching question and answer. Do not alter previously verified local script just to change a metadata label.
- Report requires actual `message.server_tool_calls` completed `deepseek_read_url/read_link`, page URL and encrypted signature presence, content `Example Domain`, billed `usage.server_tool_use.tool_fetch` if provided; HTTP 200 alone is not conformance PASS.

## Cost

As of 2026-11-17 official peak Flash token prices: input cache-miss $0.30 per million; output $1.20 per million. Successful web Fetch $0.00075 per fetched page. 500 prompt tokens + 256 completion tokens + one fetch = illustrative $0.0012072. **Actual billed amount must be separately verified with provider billing**, and repeated/extra server-side Fetch operations are not mechanically prevented by an HTTP one-call cap.

## Stop policy

Once P3 script is executed once, **GO exhausted**, regardless of HTTP or model outcome. `logs/ds-lv-02-p3-attempted.marker` makes re-runs fail. P4–P9 **NOT AUTHORIZED**. No merge, production, DS-02 or benchmark freeze.

## Actual result — 2026-11-17 19:16:47 UTC
One permitted HTTP POST completed, tool `deepseek_read_url/read_link` invoked/completed, source title `Example Domain`, token total 419, fetch count 1, latency 1709 ms. Estimated billing $0.0009207 not reconciled. Architecture acceptance: `../acceptance/DS-LV-02-P3-ARCHITECTURE-ACCEPTANCE.md`. **GO exhausted, no retries.**
