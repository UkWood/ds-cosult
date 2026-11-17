# PROJECT STATE — DS-консультант

Обновлено: 2026-11-17. Статус: **DS-01C STRUCTURAL POPULATION PASS — GROUND TRUTH/PDF/PROVIDER GATES PENDING**.

## Принятые владельцем решения
- DS-консультант независим от NEW RAG; `UkWood/Saturn-Main-Site` строго READ-ONLY.
- `UkWood/ds-cosult` — долговременная память, история, ТЗ, исследования и код; PR/Merge после приёмки.
- DS-01 Comparative Experiment Protocol v0.1 и последовательность DS-01A→DS-01B→DS-01C→DS-02/Pilot→Freeze→DS-04 утверждены.
- **AI Tunnel — основной gateway**: `https://api.aitunnel.ru/v1`, Bearer `sk-aitunnel-…` (ключ НЕ хранится), OpenAI Chat Completions. ADR-0003.
- Версии моделей: `deepseek-v4.1-flash`, pinned `deepseek-v4.1-flash-1017` — кандидаты; API совместимость и capability не проверены на пользовательском ключе.
- Варианты сравнения W/A-AT/B-AT/C0-AT, B-text/B-entity; native DeepSeek tools НЕ считать автоматически доступными через AI Tunnel.

## Source baseline кандидат
`UkWood/Saturn-Main-Site` commit `084d759487bfab6e111549c9b5469711ac5fc13e`; tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`.

## Выполнено
- Исходные 438 Markdown-записей проинвентаризированы по коллекциям.
- 60 Core кандидатов уникальны (5×12), 12 Pilot, 8 диалогов, 24 документных задачи. 17 atomic fact candidates; **0 expert approved**.
- Публичный PDF preflight: СОС-95 195 физ. страниц; СЛДКС-1 83; ЕАСДКиУ 79 — данные из PDF reader, нет bytes SHA-256.
- Уточнены особенности AI Tunnel: отдельный gateway search, PDF parser, reasoning, downstream provider pinning, billed cost_rub. Подготовлен документированный conformance gate без платных вызовов.
- Долговременная архитектурная документация ведётся в Draft PR #1, без Merge.

## Blockers
1. Репозиторий PUBLIC: закрытые Core/GT, реальные секреты и ограниченные документы не публиковать.
2. **Нет authenticated AI Tunnel conformance**: нет actual secret, approved budget и подтверждённого модельного маршрута/инструментов; не отправлялись платные запросы.
3. **PDF SHA-256 отсутствует**, физические страницы по веб-просмотру не равны pinned file bytes; 24 doc tasks blocked.
4. Инженерные отношения и некоторые import fields требуют экспертизы.
5. 0 expert-approved GT; DS-CORPUS-1.0 не заморожен; DS-02 coding НЕ разрешён.
6. Предварительные долларовые лимиты DS-01 не превращать в рублёвые расходы без решения владельца.

## Следующее
1. DS-GATE-AT: подтверждение шлюза, модели, tools, provider pin, reasoning, PDF и стоимости по публичным test fixtures. Только после одобрения ограниченного validation assignment.
2. CF-00/CF-04: скачать/хешировать PDF, разметить physical pages, проверить отношения, принять GT.
3. После приёмки prepare DS-02 minimal harness; затем Pilot calibration и Final Freeze, после которого Core.
4. PR #1 оставить Draft до владельческой проверки. NO MERGE. NO PRODUCTION.
