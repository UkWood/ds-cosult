# DS-01C — Candidate Set Validation Report v0.1

Дата: 2026-11-17. Исходный pinned site commit: `084d759487bfab6e111549c9b5469711ac5fc13e`.

**Статус: STRUCTURAL POPULATION PASS / GROUND TRUTH ACCEPTANCE PENDING.**

## Проверенные количественные требования
| Проверка | Результат |
|---|---:|
| Core кандидатов | 60 — PASS |
| По каждой из 12 категорий | 5 — PASS |
| Уникальность текста Core вопросов | 60/60 — PASS |
| Открытых Pilot вопросов | 12 — PASS (формулировки кандидаты) |
| Многошаговых сценариев | 8 — PASS |
| Реплик пользователя в каждом диалоге | 5 — PASS |
| Декларированных PDF | 12 — PASS (сами байты не проверены) |
| Документных задач | 24 — PASS (все blocked до PDF) |
| Извлечённых fact candidates | 17 — PASS (не expert-approved) |
| Неизвестных source keys в реестре | 0 — PASS |
| Expert-approved Ground Truth | 0 — NOT STARTED |

## Состояния 60 Core кандидатов
- `source_extracted`: 26;
- `behavior_candidate`: 9;
- `context_candidate`: 5;
- `blocked_pdf`: 5;
- `blocked_visual`: 5;
- `needs_scope_audit`: 5;
- `metadata_conflict_candidate`: 1;
- `blocked_pdf_conflict`: 1;
- `blocked_fixture`: 3.

Все 60 имеют статус `NOT_EXPERT_APPROVED`; заморозка `false`.

## Воспроизводимость чернового пакета
Локально сформирован частный архив кандидатов; **не сохранён в PUBLIC репозитории**. Его SHA-256 на текущей версии: `d6513b373f3ce10da44fe7c6a3e925ec5a40cd15636320c73fbb8e57cd540a58`.
Содержит полный набор Core/Pilot/диалогов/документных задач и предварительные утверждения в JSON и Markdown. Архив должен быть сохранён в защищённой памяти проекта после решения вопроса доступа. Локальная доступность файла в конкретной сессии не означает долговременного хранения GitHub.

## Acceptance Review — Consolidated Findings

**BLOCKER-01:** PUBLIC GitHub не подходит для публикации закрытого Core/GT: скрытые вопросы и ответы могут повлиять на независимость последующих тестов. Требуется private или отдельный закрытый контрольный корпус.

**BLOCKER-02 (уточнён 17.11):** три PDF из 12 визуально прочитаны, физические страницы и отдельные таблицы/схемы сверены в веб-просмотре; **у всех 12 отсутствуют pinned original bytes SHA-256, полные карты страниц и независимая экспертиза**. 10 Core PDF/VIS и 24 document tasks по-прежнему не готовы к финальному запуску.

**BLOCKER-03:** ни один из 60 Core эталонов не утверждён экспертом, scope для 5 UNK не проверен; четыре конфликтных сценария (1 PDF + 3 синтетических) требуют реальных конфликтов/фикстур и независимого оформления.

**IMPORTANT-01:** 17 source-extracted фактов должны быть сопоставлены с версиями первичных документов; особенно статусы оборудования, модификации и числовые ограничения.

**IMPORTANT-02:** подтвердить равенство доступных доказательств для B-text/B-entity, не использовать Core для оптимизации промптов.

## Решение по этапу
- **Population Gate:** PASS (структурная комплектность).
- **Ground Truth Gate:** NOT PASSED.
- **Final Corpus Freeze:** NOT AUTHORIZED.
- **DS-02 code:** NOT AUTHORIZED.
- **Merge of PR #1:** NOT AUTHORIZED.

Все дальнейшие ревизии должны создавать новые commit SHA и сохранять историю замечаний.

## Дополнение — проверка страниц и Pilot evidence
- PDF-P01 СОС-95: физическая p.9 / табл.2.
- PDF-P02 СЛДКС-1: физическая p.7 / табл.1 и p.18 / рис.1.
- PDF-P03 ЕАСДКиУ: физическая p.3 / назначение, p.4 / табл.1 и p.12 / рис.1.
- 11 открытых evidence seeds собраны в `DS-01C-PDF-EVIDENCE-SEEDS.md`; это **web-visual candidates**, не signed Ground Truth.
- P09/P10 уточнены в `DS-01C-PILOT-P09-P10.md`.
- Локальная процедура закрепления bytes: `docs/tasks/DS-01C-LINUX-PDF-BYTE-PIN.md`.
