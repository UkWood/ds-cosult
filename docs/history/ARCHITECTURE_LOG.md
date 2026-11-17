# Architecture Log — история DS-консультанта

> Консолидированная запись по сообщениям архитектурных сессий, не буквальный экспорт чата. Факты и статусы должны сверяться с утверждениями владельца; сохранять даже неудачные гипотезы и закрытые замечания.

## 2026-11-17
- **DS-00 — Architecture Discovery:** принят независимый проект; исследовательская гипотеза о совмещении DeepSeek API и Entity-Centric RAG. Результат: предварительное исследование, API-инструменты требуют проверки в реальных условиях. Не было кода, Merge или production.
- **DS-01 — Comparative Experiment Protocol v0.1:** подготовлен и затем явно принят владельцем. Варианты W/A/B/C0, диагностический B-text/B-entity, два режима сравнения, Pilot 12 / Core 60 / 8 диалогов / документы.
- **DS-01A — Benchmark & Ground Truth Specification v0.1:** сформулированы правила независимого эталона, 0–5 шкалы, атомарных утверждений и Corpus Freeze. Владелец принял последовательность контрольных точек.
- **DS-01B — Source Inventory:** READ-ONLY изучение Saturn-Main-Site. Кандидат site commit `084d759487bfab6e111549c9b5469711ac5fc13e`, tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`. Обнаружены 292 products, 25 systems/sections, 23 groups, 36 articles, 40 pages, 22 news (438 записей). Первые факты только `source_extracted`, без экспертного утверждения. PDF и ссылки ещё не заморожены.
- **Учреждение долгосрочной памяти:** владелец создал `UkWood/ds-cosult` и объявил его основным хранилищем истории, требований, решений, состояния и кода.
- **DS-01C — Benchmark Candidate Population:** текущая документарная итерация. Кандидаты не являются экспертно утверждёнными Ground Truth; закрытые вопросы и эталоны нельзя помещать в PUBLIC GitHub. Отдельная ветка/PR, без Merge.

- **AI Tunnel API (новое решение владельца):** основной транспорт `https://api.aitunnel.ru/v1`, Bearer формат `sk-aitunnel-…`, OpenAI Chat Completions. Ранее предполагаемый прямой DeepSeek API заменён на proxy; модельные алиасы и возможности нативных инструментов требуют верификации. ADR-0003 и DS-01 transport addendum; не было авторизованных платных запросов.
- **Gateway documentation review:** найдены gateway-specific `aitunnel:web_search`, file-parser/OCR, reasoning, downstream routing и способность игнорировать параметры при несовместимости. Добавлен preflight конформанс и требования фиксации провайдера.
- **PDF preliminary inspection:** публичные руководства СОС-95 (195 стр.), СЛДКС-1 (83 стр.) и ЕАСДКиУ (79 стр.) доступны к чтению; bytes SHA-256 не получены, документные GT по-прежнему BLOCKED.

- **Отмена AI Tunnel (решение владельца):** владелец отказался от стороннего шлюза и выбрал **прямой DeepSeek API** ради использования нативных tools/Files/OCR/search. **ADR-0004 ACCEPTED, ADR-0003 SUPERSEDED**. Транспортный addendum AT-01 и capability gate AI Tunnel оставлены в репозитории только как история. Протокол DS-01 и объёмы Benchmark сохраняются; прямые API-запросы ещё не проводились.

- **DS-01C — page-level evidence follow-up:** просмотрены и визуально проверены выбранные таблицы/схемы официально опубликованных PDF СОС-95, СЛДКС-1 и ЕАСДКиУ. Собраны 11 публичных PDF evidence seeds, уточнены Pilot P09/P10; оригинальные byte hashes недоступны из рабочей среды, оформлено отдельное Linux/WSL задание на SHA-256. Все GT по-прежнему кандидаты.

- **DS-LV-01 задание для Linux/WSL:** владелец подтвердил наличие прямого DeepSeek API ключа. Подготовлен самостоятельный validation handoff на закрепление трёх PDF и отдельную минимальную проверку Chat Completions только после согласования бюджета; до запуска оба трека UNTESTED, ключ хранится исключительно у владельца. Задание сохранено в памяти проекта, PR #1 остаётся Draft.

- **DS-LV-01 — Final Linux/WSL Validation Report:** 17.11.2026 представлен полный отчёт (534 строки). WSL2/Poppler — PASS; 3 PDF оригинала (195, 83, 79 стр.) закреплены локально через SHA-256 с двумя контрольными проверками — PASS по отчёту; 6 визуальных PNG — PASS WITH REVIEW NOTES (стрелки рис.1 ЕАСДКиУ AMBIGUOUS); один прямой платный вызов `deepseek-flash` с отдельным GO на $0.01 — HTTP 200, 21 token, 1064 ms. Billing не проверен.
- **DS-LV-01 — Architecture Session A Acceptance:** ACCEPTED WITH REVIEW NOTES, только в выполненном scope. PDF и манифест остаются на локальной машине Linux; независимый пересчёт SHA архитектурной сессией не выполнен. Advanced API, экспертные Ground Truth, DS-02 и Freeze НЕ разрешены. Отчёт и опубликованные SHA-256: `docs/acceptance/DS-LV-01-ARCHITECTURE-ACCEPTANCE.md`, `docs/evidence/DS-LV-01-PDF-MANIFEST-REPORTED.json`.
- **DS-LV-02 draft:** сформирован план конформанс-проверок нативных DeepSeek tools, без разрешения на новый платный вызов.

- **DS-LV-02 / CF-04 documentation refinement (2026-11-17):** current official DeepSeek Web Tools, Files API, Search/Fetch, OCR and pricing contracts reviewed. Staged P0..P9 conformance protocol prepared; HTTP 200 errors, `server_tool_calls`, tool billing and 1-hour file expiry/DELETE included. Public CF-04 review packet prepared for 11 pinned-source PDF assertions. All 11 still require independent specialist signatures, no new paid calls, no hidden Core publication.

- **DS-LV-02 / P1 GO (2026-11-17):** владелец ответил «Разрешаю, продолжай» на предложение одной Deep Thinking проверки с лимитом $0.01. Подготовлен безопасный Python smoke test с getpass, без tools, max_tokens=512, без повторов, с редактированным JSON-отчётом. На момент фиксации API-вызов ещё не выполнен; все остальные P2..P9 НЕ РАЗРЕШЕНЫ.

- **DS-LV-02/P1 выполнен и принят (17.11.2026 18:46:55 UTC):** один прямой запрос `deepseek-flash` с `thinking.type=enabled` (лимит $0.01): HTTP 200, ответ 9.8, `reasoning_content_present=true`, `reasoning_tokens=65`, total 118 tokens, latency 1443 мс; расчетный модельный тариф $0.0000975, actual billing не подтверждён. Acceptance: `docs/acceptance/DS-LV-02-P1-ARCHITECTURE-ACCEPTANCE.md`. Следующая платная фаза P2 пока НЕ РАЗРЕШЕНА.

- **DS-LV-02/P2 GO (17.11.2026):** владелец согласовал один прямой DeepSeek Search API HTTP POST c $0.01 ceiling; формализованы `count=1`, `need_content=false`, оценка $0.00075 и Python WSL скрипт с `getpass`/no retry/atomic marker. На момент записи P2 НЕ ИСПОЛНЕН; P3..P9 не разрешены.

- **DS-LV-02/P2 completed + accepted (2026-11-17 19:00:23 UTC):** owner-authorized 1 standalone Search API HTTP POST returned 200 and 1 official-documentation result (`https://api-docs.deepseek.com/news/news261113/#1`), no content fetch, latency 862 ms, fee estimate $0.00075, actual billing unknown. P2 ACCEPTED; detailed report `docs/acceptance/DS-LV-02-P2-ARCHITECTURE-ACCEPTANCE.md`, evidence `docs/evidence/DS-LV-02-P2-RESULT.json`. Authorization exhausted.
- **DS-LV-02/P3 proposal drafted:** model-directed `deepseek_read_url` on `https://example.com/`, explicitly NOT authorized and NOT executed; differentiate from managed Search/Fetch and `deepseek_web_search`.

- **DS-LV-02/P3 scope consent (2026-11-17):** user replied «Согласовано продолжай». Completed official documentation and tariff preflight; prepared offline-safe WSL script including synthetic self-tests, authentic `message.server_tool_calls` scrutiny and billed tool_fetch tracking. A numeric budget for P3 was not previously agreed; propose one POST / $0.01, but **NO PAID GO until explicit numeric acceptance**. No API request executed.

- **DS-LV-02/P3 offline preflight PASS (2026-11-17):** владелец подтвердил успешную Python compilation, три синтетические самопроверки (0 network, $0), локальный SHA-256 скрипта `1de63e655bc84c19fce73076442280946ff099d06d5b3ae8898b4a8cd8fc26e2`; evidence `docs/evidence/DS-LV-02-P3-OFFLINE-PREFLIGHT.md`. Платный P3 не запускался; отдельное подтверждение суммы $0.01 требуется.

- **DS-LV-02/P3 Paid GO (2026-11-17):** пользователь явно разрешил 1 прямой Chat Completions вызов `deepseek_read_url` с лимитом расходов $0.01 и принял, что он организационный, а не hard cap провайдера. Запись в `docs/tasks/DS-LV-02-P3-OWNER-GO.md`; P3 пока НЕ ИСПОЛНЕН. P4..P9 не разрешены.

## Перед следующим этапом
Нужны: независимая экспертиза Ground Truth, проверка отношений, 9 оставшихся PDF, закрытое хранение тестов, безопасный custody-пакет локальных PDF и отдельное разрешение/бюджет на native DeepSeek tools.
