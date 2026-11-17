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
- Повторный PDF preflight: СОС-95 195, СЛДКС-1 83, ЕАСДКиУ 79; **визуально проверены выбранные таблицы и схемы на физических страницах 9 / 7,18 / 3,4,12**; 11 evidence seeds, Pilot P09/P10 уточнены. **Исходные bytes SHA-256 не получены**.
- Проверена официальная документация прямого DeepSeek API: native web search, deep thinking search, URL reading, Files API (text/rich), Search/Fetch, OCR. Подготовлен DSAPI-01..12 conformance gate без оплачиваемых вызовов.
- Готово самодостаточное задание **DS-LV-01** для отдельной Linux/WSL Validation Session: PDF bytes pin + ровно один условно разрешаемый API connectivity smoke check; **ни один шаг ещё не исполнен**.
- Долговременная архитектурная документация ведётся в Draft PR #1, без Merge.

## Blockers
1. Репозиторий PUBLIC: закрытые Core/GT, реальные секреты и ограниченные документы не публиковать.
2. **Нет authenticated Direct DeepSeek API conformance**: владелец подтвердил, что ключ API у него имеется, но платные проверки, поддержка инструментов и лимит расходов ещё не утверждены; ключ не передавался.
3. **PDF SHA-256 отсутствует**: визуальные web evidence seeds не являются pinned file bytes; 24 doc tasks всё ещё blocked, независимая экспертиза GT не пройдена.
4. Инженерные отношения и некоторые import fields требуют экспертизы.
5. 0 expert-approved GT; DS-CORPUS-1.0 не заморожен; DS-02 coding НЕ разрешён.
6. Предложенные ранее лимиты $20/$100 и актуальную стоимость DeepSeek проверить и утвердить перед реальными платными прогонами.

## Следующее
1. DS-API-CONFORMANCE DSAPI-01..12: модель, thinking, native tools, Files/OCR, Search/Fetch, безопасность, стоимость — только после отдельного разрешения.
2. В отдельной Linux/WSL Validation Session выполнить **DS-LV-01** (см. `docs/tasks/DS-LV-01-LINUX-WSL-VALIDATION.md`): сначала бесплатное закрепление PDF, затем при отдельном GO владельца один платный smoke-запрос DeepSeek. Историческое задание PDF pin сохранено; DS-LV-01 — объединяющее актуальное.
3. После приёмки prepare DS-02 minimal harness; затем Pilot calibration и Final Freeze, после которого Core.
4. PR #1 оставить Draft до владельческой проверки. NO MERGE. NO PRODUCTION.
