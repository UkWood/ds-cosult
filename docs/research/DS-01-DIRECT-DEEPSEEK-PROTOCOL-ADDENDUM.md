# DS-01 — Transport Addendum DS-API-01 v0.1

Дата: 2026-11-17. **Статус: ACTIVE (по ADR-0004)**. Заменяет AI Tunnel Addendum AT-01, не отменяет утверждённую методологию DS-01.

## Прямой экспериментальный контур
`User → Experiment Runner → https://api.deepseek.com → native DeepSeek model/tools`.

Вариант B дополнительно использует app-owned source registry, retrieval, entity dossiers, context planner и independent verifier. Вариант A использует native DeepSeek model-directed tools. Не сравнивать A с B как контролируемую пару: retrieval различается. Главная controlled пара B-text ↔ B-entity на одинаковой модели, доказательствах, лимитах и проверке.

## Обязательные варианты
| ID | Источник генерации | Инструменты | Назначение |
|---|---|---|---|
| W | DeepSeek Web | веб-возможности самого Web | ручной пользовательский эталон |
| A | Прямой DeepSeek `deepseek-flash` | `deepseek_web_search`, `deepseek_read_url`, Files API по задаче | App-like natural workflow |
| B | Тот же прямой DeepSeek | контролируемая выдача из доверенных Saturn sources | Entity-Centric Conversational RAG |
| C0 | Тот же прямой DeepSeek | нет tools, no external evidence | диагностический контроль |
| B-text/B-entity | Тот же прямой DeepSeek | те же факты и источники | абляция организации контекста |

## Native tool rules
- `thinking: {"type": "enabled"}` плюс `deepseek_web_search` — deep thinking search.
- `deepseek_read_url` читает URL последней пользовательской реплики; сочетание thinking+web search меняет поведение URL reading.
- Нельзя форсировать named `deepseek_web_search` или `deepseek_read_url` посредством `tool_choice`. Фиксировать `declared`, `called` и источник каждой ссылки.
- Для детерминированного corpus retrieval B опираться на app-owned pinned knowledge, не на случайный веб-поиск.
- В многошаговом диалоге сохранять provider-specific tool/citation blocks в истории, чтобы не терять контекст.

## File/PDF modes
- `text_recognition`: текст без фигур.
- `rich_layout_recognition`: текст + распознанные фигуры в порядке документа, часть фигур может быть пропущена.
- OCR API: отдельный диагностический режим извлечения текста/структуры по страницам.
- Документы в Files API возвращают `file_id` после успешной обработки; сохранять bytes SHA-256 оригинала, реальную версию, физические страницы и разрешения передачи файлов.
- Не утверждать фактическую точность OCR только на основании успешной загрузки.

## Измерения
`model_requested`, `model_observed`, `thinking`, `tool_declarations`, `tool_calls`, `citations`, `file_id`, `parser_purpose`, `usage`, `latency_ms`, `source_snapshot_id`, `raw_response`, `error`, `retry` — без секретов. Цены и долларовые лимиты перепроверить перед запуском, до платных тестов получить отдельное разрешение.

## Gate
DS-API-CONFORMANCE (AUTH/CHAT, THINKING, SEARCH, URL, PDF/Figures, OCR, SEARCH/FETCH, MULTI-TURN, COST/ERRORS, SAFETY) → DS-02 implementation acceptance → DS-03 Pilot → DS-CORPUS-1.0 Freeze → DS-04 Core. Структурный статус DS-01C не равен утверждённому Ground Truth.
