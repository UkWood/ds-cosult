# PROJECT STATE — DS-консультант

**Обновлено:** 2026-11-17  
**Текущий статус:** **DS-LV-02/P2 STANDALONE SEARCH PASS; DS-01C GROUND TRUTH & CORPUS FREEZE PENDING**

## Решения владельца
- DS-консультант — независимый проект. `UkWood/Saturn-Main-Site` — READ-ONLY; NEW RAG не изменять.
- `UkWood/ds-cosult` — долговременная память, история, решения, требования и код.
- Основной API: **прямой DeepSeek** `https://api.deepseek.com`, `deepseek-flash`; ADR-0004, AI Tunnel ADR-0003 SUPERSEDED.
- DS-01 protocol accepted: W/A/B/C0, B-text/B-entity; Pilot 12, Core 60 (по 5 на категорию), 8 диалогов и 24 document tasks.
- Merge только после явного разрешения владельца; PR #1 остаётся Draft. **P1 и P2 PASS**, индивидуальные платные разрешения исчерпаны. **P3 подготовка согласована, платный запуск пока не разрешён: отсутствует утверждённый числовой бюджет**. P4..P9, DS-02 coding, production и Corpus Freeze не разрешены.

## Доказательный baseline сайта — кандидат
`UkWood/Saturn-Main-Site` commit `084d759487bfab6e111549c9b5469711ac5fc13e`, tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`.

## DS-01C benchmark
- 60 Core candidates, 12 Pilot, 8 dialogue scenarios, 24 document tasks, 17 extracted fact candidates — структурный PASS.
- **0 expert-approved GT**; технические отношения и утверждения по графам требуют отдельной экспертизы.
- Три PDF имеют **Linux-reported locally checked SHA-256**, подробный JSON-manifest `docs/evidence/DS-LV-01-PDF-MANIFEST-REPORTED.json`.
- Шесть физических страниц PNG визуально проверены **в Linux Validation Session**, другие девять PDF ещё не закреплены. ЕАСДКиУ рис.1 — частично неоднозначен.
- Отчёт архитектурной приёмки: `docs/acceptance/DS-LV-01-ARCHITECTURE-ACCEPTANCE.md`.

## DS-LV-01 acceptance
- LV-ENV-01: PASS (Ubuntu WSL2, Poppler).
- LV-PDF-01: PASS **по отчёту с локальными SHA256**.
- LV-PDF-02: PASS WITH REVIEW NOTES (6 PNG).
- LV-API-01: PASS — 1 direct API call (`deepseek-flash`), HTTP 200, 21 tokens, 1064 ms, no tools, no uploads.
- Один платный запрос был **явно одобрен владельцем** с лимитом $0.01 USD. Денежное списание не проверено по billings.
- **Оригинальные PDF/PNG и локальный evidence-manifest в Architecture Session A не поступили**; независимое побайтовое перепроверение не выполнено.

## Remaining blockers
1. `ds-cosult` PUBLIC: нельзя публиковать закрытый Core/GT, секреты и ограниченные источники.
2. Нет expert-approved Ground Truth, DS-CORPUS-1.0 не frozen.
3. Native DeepSeek **thinking = PASS for one smoke test**; standalone Search **P2 PASS / ACCEPTED**; web/URL/Files/OCR/Fetch/continuity **UNTESTED**.
4. Из 12 запланированных документов лишь 3 byte-pinned по Linux-отчёту, 9 ожидают проверку.
5. Независимый custody/audit локальных исходных PDF/PNG и манифеста не получен; billing не сверён.
6. Технические отношения, версии оборудования и неоднозначные стрелки в ЕАСДКиУ требуют экспертной оценки.

## DS-LV-02/CF-04 readiness update (2026-11-17)
- Официальные контракты нативных Web Tools, Files API, OCR, Search/Fetch и актуальная тарифная страница повторно изучены.
- Подготовлен исполнимый **по стадиям** протокол DS-LV-02 v0.2 с отдельными subgates P0..P9, наблюдаемой проверкой `server_tool_calls`, обработкой ошибок HTTP 200 и учётом billed tool units; **никаких новых API-вызовов не было**.
- Сформирован `docs/research/DS-01C-CF04-GT-EXPERT-PACKET.md`: 11 открытых кандидатов с точными SHA/page/scope, статус подписей специалистов **0/11**.
- Тарифы DeepSeek на дату подготовки: model tokens + отдельные Search/Fetch + PDF/OCR; фиксированный бюджет и hard stop для multi-search не доказаны. Для paid subgate требуется отдельный GO владельца.

## Owner GO — DS-LV-02 P1
- 17.11.2026 владелец ответил «Разрешаю, продолжай» на предложение P1: 1 платный вызов, максимум $0.01. Это разрешение записано в `docs/tasks/DS-LV-02-P1-OWNER-GO.md`; скрипт в `scripts/validation/ds_lv_02_p1_thinking.py`.
- **Статус P1: EXECUTED / PASS / ACCEPTED.** 17.11.2026 18:46:55 UTC: один direct API запрос HTTP 200, правильный ответ 9.8, `reasoning_content_present=true` (184 символа), `reasoning_tokens=65`, total 118 tokens, 1443 мс. Cost estimate $0.0000975, billing unverified. Отчёт: `docs/acceptance/DS-LV-02-P1-ARCHITECTURE-ACCEPTANCE.md`; sanitized evidence: `docs/evidence/DS-LV-02-P1-RESULT.json`. Текст reasoning не сохранялся, ключ не передавался; разрешение на один вызов ИСЧЕРПАНО.

## DS-LV-02/P2 owner authorization
- Владелец согласовал один прямой Search API вызов с бюджетом $0.01; `POST /v1/tools/search`, `count=1`, `need_content=false`. Published charge estimate $0.00075 for successful nonempty result, actual billing unverified.
- Safe test script: `scripts/validation/ds_lv_02_p2_search.py`; scope & GO: `docs/tasks/DS-LV-02-P2-OWNER-GO.md`. **P2 executed and accepted:** 2026-11-17 19:00:23 UTC, HTTP 200, `result_count=1`, valid official DeepSeek documentation URL, 862 ms, estimated $0.00075, actual billing UNKNOWN. Отчёт: `docs/acceptance/DS-LV-02-P2-ARCHITECTURE-ACCEPTANCE.md`, JSON: `docs/evidence/DS-LV-02-P2-RESULT.json`. Разрешение исчерпано, P3 не разрешён.

## P3 preflight preparation (2026-11-17)
- User: «Согласовано продолжай». P3 scope/offline preparation approved; no numeric budget was previously proposed. Paid P3 NOT AUTHORIZED until owner confirms proposed **1 HTTP POST and $0.01 USD** with acknowledged server-side fetch billing risk.
- Verified official docs (Chat Completions + `deepseek_read_url`), JSON `message.server_tool_calls`, true billed `usage.server_tool_use.tool_fetch`, and separate model token charges.
- Read-only one-page fixture `https://example.com/`; safe `scripts/validation/ds_lv_02_p3_url_read.py` with `--self-test` (zero network), one-attempt marker, getpass, redacted report.

## Next stage
- **CF-01/CF-04:** route 11 evidence seeds to two-person expert review using `docs/research/DS-01C-CF04-GT-EXPERT-PACKET.md`; don't publish hidden Core/GT, don't invent signatures; remaining PDF/relations still open.
- **DS-LV-02:** staged conformance v0.2 `docs/tasks/DS-LV-02-EXECUTION-PROTOCOL.md` (P0 offline); **P1 PASS; P2 Search PASS; P3 OFFLINE PREFLIGHT READY, PAID GO PENDING BUDGET; P4..P9 NOT AUTHORIZED**. P3: `docs/tasks/DS-LV-02-P3-URL-READING-PROPOSAL.md`.
- **DS-02 Minimal Harness / Pilot:** only after separate Architecture decision and approved gates; no implementation begun.
- **Draft PR #1 remains OPEN, NO MERGE / NO PRODUCTION.**
