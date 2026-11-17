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

## Перед следующим этапом
Нужны: независимая экспертиза Ground Truth, проверка отношений, 9 оставшихся PDF, закрытое хранение тестов, безопасный custody-пакет локальных PDF и отдельное разрешение/бюджет на native DeepSeek tools.
