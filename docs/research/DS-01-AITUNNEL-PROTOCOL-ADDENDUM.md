# DS-01 — API Transport Addendum AT-01 v0.1

Дата: 2026-11-17. Статус: **TRANSPORT ACCEPTED; EXPERIMENTAL CAPABILITIES UNVERIFIED**. Подчиняется принятому DS-01 v0.1.

## Новая архитектурная граница
User → DS experiment runner → AI Tunnel Chat Completions → selected downstream DeepSeek provider → answer.
В B-AT retrieval доверенных источников выполняет приложение, не шлюз; результаты предварительно сформированы из pin-корпуса. Web search, включённый для A-AT, может обслуживаться собственным gateway engine (native/Exa/другой) — это видно из явной конфигурации и логов, но не считается прямым нативным поиском DeepSeek без проверки.

## Названия вариантов
| Variant | Engine | Tools | Примечание |
|---|---|---|---|
| W | DeepSeek Web | web native | Ручной пользовательский эталон, версия модели может быть неизвестна |
| A-AT | AI Tunnel DeepSeek | gateway web search, PDF pipeline | Проверка поведения AI Tunnel, а не прямого DeepSeek App Experience |
| B-AT | Та же модель/provider | локальный trusted retrieval, dossiers, verification | Исключить произвольный поиск gateway из основного режима |
| C0-AT | Та же модель/provider | none | Диагностический контроль |
| B-text/B-entity | Та же модель/provider | идентичный evidence set | Только форма контекста отличается |

## Методологические правила
- Natural Workflow: W/A-AT/B-AT/C0-AT, сравнивать качество пользовательского ответа; возможные различия поисковых движков — часть реального продукта.
- Controlled: B-text/B-entity с теми же фактами, токен-бюджетами, gateway provider, exact model, reasoning и проверкой. При дрейфе любого критичного параметра пару маркировать non-comparable.
- B-pre/B-post: один и тот же исходный ответ до/после independent verification.
- Отдельный direct-DeepSeek вариант возможен только после отдельного разрешения и подтверждённой возможности доступа.
- DeepSeek native tool behavior и AI Tunnel tool behavior не считать эквивалентными без отдельной конформанс-проверки.
- C0, B и A используют один gateway и зафиксированную версию модельного backend насколько это доступно; W внешняя чёрная коробка.

## Обязательное логирование
`gateway=aitunnel`, `gateway_base_url`, `requested_model`, `observed_model`, `downstream_provider`, `provider_policy`, `reasoning_request`, `reasoning_observed`, `tool_engine`, `tool_call_count`, `pdf_parser`, `pdf_source_sha256`, `usage_tokens`, `usage.cost_rub`, `request_id`, `finish_reason`, `latency_ms`, `failures`. Убирать секреты и личные данные из raw-log.

## Security & cost
- Ключ только в окружении, не в коммитах, отчётах и чатах; конфигурация репозитория хранит только названия переменных.
- Ограничить бюджет ключа, whitelist моделей, latency, timeout, max_tokens, max tool uses. Для фиксированного режима проверять настройки gateway и downstream.
- Перед передачей непубличных материалов проверить разрешение и цепочку обработки третьими сторонами.
- Тариф фиксировать снимком публичного каталога на дату запуска и фактическими рублями в usage; разрозненные FAQ по стоимости нельзя использовать для расчёта ожидаемой цены.
- Не проводить платные тесты до утверждения preflight и бюджета.

## Gate
Прежние DS-01A и DS-01C требования к Benchmark и Ground Truth сохраняются. Сначала gateway conformance, затем DS-02 Pilot, затем DS-CORPUS Freeze; менять числа 12/60/8/24 без отдельного решения запрещено.
