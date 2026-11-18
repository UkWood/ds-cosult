# ADR-0004 — Прямой DeepSeek API как основной провайдер

**Дата:** 2026-11-17  
**Статус:** ACCEPTED — решение владельца проекта  
**Заменяет:** ADR-0003 (AI Tunnel, **SUPERSEDED**)  
**Основание:** приоритет нативных возможностей DeepSeek без промежуточного шлюза.

## Контекст
Первоначально DS-01 предполагал прямой DeepSeek API. Затем владелец рассмотрел AI Tunnel как gateway и принял ADR-0003. После оценки рисков сторонних инструментов веб-поиска, парсинга PDF и reasoning владелец **отменил выбор AI Tunnel** и сообщил о подключении прямого DeepSeek API.

Это не является результатом измеренной сравнительной оценки доверенности провайдеров: решение архитектурное, мотивировано уменьшением числа промежуточных компонентов и прямым использованием официально документированных функций.

## Решение
1. **Единственный основной LLM/API-провайдер исследования — официальный DeepSeek API.**
2. OpenAI-compatible `base_url=https://api.deepseek.com`, Chat Completions: `POST https://api.deepseek.com/chat/completions`; `Authorization: Bearer <DEEPSEEK_API_KEY>`.
3. Модель `deepseek-flash`; согласно официальной документации на 2026-11-17 alias обслуживается DeepSeek-V4.1-Flash-1017. Точную версию, возвращаемую API, и дату проверки фиксировать в каждом запуске.
4. Варианты снова именуются **W** (ручной DeepSeek Web), **A** (прямой API + native tools), **B** (тот же прямой API + Entity-Centric Conversational RAG, evidence verification), **C0** (прямой API без внешних знаний), абляции **B-text/B-entity**.
5. Нативные `deepseek_web_search` и `deepseek_read_url` включаются только в предусмотренных режимах. `deepseek_web_search` при включённом thinking обеспечивает deep thinking search; выбор фактического вызова остаётся за моделью. Считать `tools` declared ≠ `tools` invoked.
6. Для управляемого поиска и проверки источников допустимы отдельные официальные DeepSeek `/v1/tools/search` и `/v1/tools/fetch`; внешняя выдача **не** становится доверенным техническим фактом без проверки.
7. PDF и документы: оригинальные DeepSeek Files API + `text_recognition` / `rich_layout_recognition`, отдельно официальный OCR API. Files API document upload требует соответствующего `purpose`, ссылки на `file_id`, нельзя подменять содержимое URL произвольным сырьём.
8. Внешний AI Tunnel **исключён из основной и резервной маршрутизации**, неиспользуемые сценарии A-AT/B-AT/C0-AT закрыты. Не выбирать gateway fallback без нового ADR.
9. Сохранить гарантии независимой экспертизы источников «Сатурна», immutable source IDs, документы с bytes SHA-256 и физическими страницами, строгий разбор `related`/совместимости.
10. API ключ `DEEPSEEK_API_KEY` только в защищённом локальном окружении, не в GitHub, промптах или логах. Устанавливать срок хранения файлов и по возможности удалять их после эксперимента; разрешения передачи данных обязательны.
11. Никакого разрешения на запуск платных API-запросов, DS-02 coding, Merge или production этим ADR не выдано.

## Что остаётся без изменений
DS-01 v0.1 (APPROVED), DS-01A рубрики, DS-01B/DS-01C кандидатный корпус, W/A/B/C0, Natural Workflow и Controlled Comparison, 12 Pilot/60 Core/8 диалогов/24 документных задач, независимые экспертные Ground Truth, утверждение каждого Gate и отсутствие Merge без владельца.

## Ограничения
- DeepSeek Web остаётся black box, равенство внутренней модели не гарантировано.
- Native tool search не принудителен; для строго контролируемых данных использовать application-directed retrieval.
- Rich-layout parsing не гарантирует обнаружение всех схем. Нельзя признавать интерпретацию PDF доказанной без проверки оригинальных страниц.
- Публичный репозиторий `ds-cosult` не должен содержать закрытый Core, Ground Truth, секреты и ограниченные первоисточники.

## Официальные источники
- https://api-docs.deepseek.com/guides/web_search
- https://api-docs.deepseek.com/guides/web_tools/
- https://api-docs.deepseek.com/guides/search/
- https://api-docs.deepseek.com/guides/files_api/
- https://api-docs.deepseek.com/guides/document_parsing/
- https://api-docs.deepseek.com/guides/ocr/
- https://api-docs.deepseek.com/guides/build_a_chatbot/
