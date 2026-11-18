# DS-LV-02 — Direct DeepSeek Native API Conformance (Draft Scope)

Дата: 2026-11-17. **Статус: PROPOSED — NOT AUTHORIZED FOR API EXECUTION.**

## Основание
Принятый отчёт DS-LV-01 подтвердил только базовый `deepseek-flash` Chat Completions, без thinking, web search, URL reading, Search/Fetch, Files API или OCR. Ключ у владельца, не раскрыт.

## Objective
Независимо проверить, какие native API способности действительно доступны **на реальном аккаунте** и можно ли использовать их в экспериментах A/B/C0 без gateway. Главная цель — объективная матрица `SUPPORTED / PARTIAL / UNSUPPORTED / UNTESTED` с фактическим model observed, tool invoked, источниками, ценой и latency.

## Explicit exclusions
- Запрещено отправлять закрытые Core-вопросы, Ground Truth, непубличную документацию, коммерческие файлы без отдельного разрешения.
- Не строить RAG/DS-02 harness, не запускать Pilot/Core или production.
- Не использовать AI Tunnel или fallback.
- **Не выполнять ни одного платного запроса** только на основании этого документа.

## Test protocol (после отдельного GO)
| Test | Capability | Required positive evidence |
|---|---|---|
| DSAPI-03 | Thinking on/off | Фактический `thinking` и наблюдаемое поведение; отдельно фиксировать `reasoning_content`, если есть |
| DSAPI-04 | `deepseek_web_search` | Tool *actually called*, источники, поиск, response metadata; declared ≠ called |
| DSAPI-05 | Thinking + web | Tool invocation и многошаговый процесс, не судить по объёму ответа |
| DSAPI-06 | `deepseek_read_url` | Действительно прочитано содержимое доступного публичного URL |
| DSAPI-07 | Native Search/Fetch | Структурные фактические search/fetch responses, ссылки, реальная стоимость |
| DSAPI-08 | Files / text recognition | Загрузка **малого публичного/синтетического PDF**, file_id, текст/страница, удаление/retention |
| DSAPI-09 | Files / rich layout | По схеме/рисунку сверить обнаруженное с исходной страницей, не утверждать accuracy на HTTP 200 |
| DSAPI-10 | OCR | Отдельный тест на маленькой публичной странице, page mapping, bytes SHA |
| DSAPI-11 | Multi-turn continuity | Корректный referent и сохранение источников в 4–6 ходах |
| DSAPI-12 | Cost, failures, security | Реальные токены, счёт, ошибки, отсутствие секретов в логах |

## Preflight and budgets
1. Ознакомиться с актуальной официальной документацией DeepSeek, версиями эндпоинтов/моделей и тарифом.
2. Представить владельцу **подробный план числа вызовов**, предварительные оценки min/max стоимости, ограничения запроса `max_tokens`, лимит tool-use и список точно разрешённых payload.
3. Получить **новое явное GO** и лимит расходов. Разрешение для LV-API-01 ($0.01 / один вызов) **исчерпано и не переносится**.
4. Сначала один subgate, анализ результата, затем следующий — без автоматических повторов и batch paid calls.
5. Не сохранять ключ в GitHub, файлы, командную строку, stdout; только getpass или безопасная локальная переменная.
6. Подготовить консолидированный redacted report для Architecture Session A.

## Acceptance
Отдельные PASS/FAIL/UNTESTED по каждому тесту, реальные метаданные, воспроизводимость и независимые замечания. **Не присваивать PASS для неподтверждённого native tool**, даже если Chat Completions работает.

## Current disposition
Scope prepared only. OWNER GO NEEDED. NO MERGE. NO DS-02. NO PRODUCTION.
