# PROJECT STATE — DS-консультант

Обновлено: 2026-11-17. Статус: **DS-01C STRUCTURAL POPULATION PASS — GROUND TRUTH/PDF/PROVIDER GATES PENDING**.

## Принятые владельцем решения
- DS-консультант независим от NEW RAG; `UkWood/Saturn-Main-Site` строго READ-ONLY.
- `UkWood/ds-cosult` — долговременная память, история, ТЗ, исследования и код; PR/Merge после приёмки.
- DS-01 Comparative Experiment Protocol v0.1 и последовательность DS-01A→DS-01B→DS-01C→DS-02/Pilot→Freeze→DS-04 утверждены.
- **Прямой DeepSeek API — основной транспорт**: `https://api.deepseek.com`, модель `deepseek-flash` (по документации V4.1-Flash-1017), `DEEPSEEK_API_KEY` только в локальном окружении; **ADR-0004 ACCEPTED**.
- **ADR-0003 (AI Tunnel) SUPERSEDED**: шлюз исключён из экспериментального контура, сохранён только как историческая запись.
- Сравниваем W / A / B / C0; B-text/B-entity — диагностическая абляция. Возможности прямого API документированы, но **фактически ещё не проверены**.

## Source baseline кандидат
`UkWood/Saturn-Main-Site` commit `084d759487bfab6e111549c9b5469711ac5fc13e`; tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`.

## Выполнено
- Исходные 438 Markdown-записей проинвентаризированы по коллекциям.
- 60 Core кандидатов уникальны (5×12), 12 Pilot, 8 диалогов, 24 документных задачи. 17 atomic fact candidates; **0 expert approved**.
- Публичный PDF preflight: СОС-95 195 физ. страниц; СЛДКС-1 83; ЕАСДКиУ 79 — данные из PDF reader, нет bytes SHA-256.
- Проверена официальная документация прямого DeepSeek API: native web search, deep thinking search, URL reading, Files API (text/rich), Search/Fetch, OCR. Подготовлен DSAPI-01..12 conformance gate без оплачиваемых вызовов.
- Долговременная архитектурная документация ведётся в Draft PR #1, без Merge.

## Blockers
1. Репозиторий PUBLIC: закрытые Core/GT, реальные секреты и ограниченные документы не публиковать.
2. **Нет authenticated Direct DeepSeek API conformance**: владелец подключает прямой API; фактические вызовы, поддержка инструментов и лимит расходов ещё не утверждены.
3. **PDF SHA-256 отсутствует**, физические страницы по веб-просмотру не равны pinned file bytes; 24 doc tasks blocked.
4. Инженерные отношения и некоторые import fields требуют экспертизы.
5. 0 expert-approved GT; DS-CORPUS-1.0 не заморожен; DS-02 coding НЕ разрешён.
6. Предложенные ранее лимиты $20/$100 и актуальную стоимость DeepSeek проверить и утвердить перед реальными платными прогонами.

## Следующее
1. DS-API-CONFORMANCE DSAPI-01..12: модель, thinking, native tools, Files/OCR, Search/Fetch, безопасность, стоимость — только после отдельного разрешения.
2. CF-00/CF-04: скачать/хешировать PDF, разметить physical pages, проверить отношения, принять GT.
3. После приёмки prepare DS-02 minimal harness; затем Pilot calibration и Final Freeze, после которого Core.
4. PR #1 оставить Draft до владельческой проверки. NO MERGE. NO PRODUCTION.
