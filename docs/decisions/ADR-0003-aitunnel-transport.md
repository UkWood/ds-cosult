# ADR-0003 — AI Tunnel как основной API-транспорт проекта

Дата: 2026-11-17  
Статус: **ACCEPTED — transport choice specified by project owner**  
Capability conformance: **PENDING**, не считать принятой реализацией.

## Контекст
Исходный DS-01 v0.1 предполагал прямой DeepSeek API (`deepseek-flash` и нативные DeepSeek tools). Владелец определил фактический канал подключения:
- Base URL: `https://api.aitunnel.ru/v1`
- Авторизация: `Authorization: Bearer <secret>`
- Формат ключа: `sk-aitunnel-…`
- Протокол: OpenAI Chat Completions.
Указанный пользователем `sk-aitunnel-xxx` — **пример маски**, НЕ рабочий ключ. Секреты в репозиторий и чат не помещать.

## Решение
1. Основной API провайдер DS-консультанта: **AI Tunnel**. Вызывать `POST https://api.aitunnel.ru/v1/chat/completions`. Не делать прямой DeepSeek API неявным fallback.
2. Предварительный model ID: `deepseek-v4.1-flash`. Для повторяемости проверить поддерживаемый закреплённый ID `deepseek-v4.1-flash-1017`; до authenticated проверки это только кандидат, его идентичность официальному `deepseek-flash` не доказана.
3. W — официальный DeepSeek Web; A-AT — DeepSeek through AI Tunnel с доступными функциями шлюза; B-AT — тот же модельный backend через AI Tunnel плюс application-directed trusted RAG; C0-AT — базовая модель без retrieval. Диагностическая абляция B-text/B-entity сохраняется.
4. Нативные `deepseek_web_search`, `deepseek_read_url`, Search/Fetch, OCR и Files API **не считать автоматически доступными через AI Tunnel**. Использовать только отдельно документированные и протестированные эквиваленты или отмечать unsupported.
5. Для A-AT gateway web search обозначается `aitunnel:web_search`. Для PDF gateway принимает content part `type: file` и предоставляет `file-parser` с разными движками. Это НЕ тот же экспериментальный механизм, что нативный DeepSeek PDF pipeline.
6. Межвариантное сравнение фиксирует model ID, конкретный downstream provider, параметры reasoning, фактический tool engine, PDF parser, провайдерские fallback и стоимость.
7. Gateway способен молча игнорировать неподдерживаемые параметры и автоматом менять downstream provider. Перед benchmark требуются pin провайдера (если доступен), `provider.require_parameters: true`, `provider.allow_fallbacks: false` и проверка фактического поведения. Не использовать параметры наугад и не считать сам факт HTTP 200 доказательством применённого режима.
8. Цена в gateway измеряется в рублях: `usage.cost_rub` и журналы поставщика; старые исследовательские долларовые лимиты DS-01 — предложения, а не автоматические рублёвые бюджеты. Для оплачиваемых испытаний нужен отдельный рублёвый предел.
9. Приватность и условия дальнейшей передачи данных через промежуточного провайдера проверить до отправки непубличных материалов.
10. Кода, платных запросов, Merge и production данное решение не санкционирует.

## Изменение исходного DS-01
Это **транспортное дополнение**, не тихая замена принятого протокола. H-01 оценивает практический пользовательский опыт DeepSeek Web против **A-AT**, включая влияние шлюза; утверждения об идентичности прямому DeepSeek API без отдельного доказательства недопустимы.

## Дальнейшая приёмка
- DS-GATE-AT-01: модель и её идентификатор;
- DS-GATE-AT-02: reasoning / tool calls / usage;
- DS-GATE-AT-03: search & URL retrieval;
- DS-GATE-AT-04: PDF pipeline, parser and page provenance;
- DS-GATE-AT-05: provider pinning, budget, privacy;
- DS-GATE-AT-06: preflight reports signed before DS-02/Pilot.

## Ссылки на документацию
- https://aitunnel.ru/docs
- https://aitunnel.ru/docs/models
- https://aitunnel.ru/docs/provider
- https://aitunnel.ru/docs/web-search
- https://aitunnel.ru/docs/pdf
- https://aitunnel.ru/docs/reasoning
- https://api-docs.deepseek.com/guides/web_tools/
- https://api-docs.deepseek.com/guides/search/
