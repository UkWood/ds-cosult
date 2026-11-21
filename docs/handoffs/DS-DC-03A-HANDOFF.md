# DS-DC-03A · CandidateAnswer & Evidence Contract Lab

База Draft PR #4 — 1fdeea45d184439eb01e9c2dfab385fda4702fbe. Проекты V2 и Technical Evidence Verifier готовы к архитектурному ревью. Для статуса **READY FOR CANDIDATE CONTRACT V2 ARCHITECTURE ACCEPTANCE** остаётся локальный replay и полный аудит подлинного Q01. Получен Final Live Calibration Report от Linux/WSL Validation Session. В нём есть текст ответа и описание полей. Исходный JSON CandidateAnswer и его SHA-256 отсутствуют. Поля по отчёту не реконструировались.

## Что установлено по Q01

- WSL отчёт подтверждает четыре PDF на 80 страницах и карточку изделия, 44 396 prompt tokens, 4 401 completion и stop. Это одно измерение.
- WSL воспроизвела invalid_locator. По её проверке у всех пяти локаторов совпали doc ID, SHA, редакция и физическая страница 60. Модель вернула claim.scope «БКД-ПК-RF.2», сервер ожидает saturn:device:bkd-pk-rf-2. Подбор документа в V1 требует одновременного равенства этих полей. Отказ происходит до проверки цитаты и строковых полей.
- GT01 подтвердил пять структурированных технических утверждений. По закреплённому PDF проверена физическая страница 60 через pdftotext -layout. В таблице 12 разные строки связывают неподключённую сеть с проверкой концентратора и возможный обрыв с проверкой кабеля. Фраза о «практическом порядке» из отчёта создаёт впечатление последовательности, которой таблица не задаёт. Графическая сверка остаётся отдельной проверкой. [GT01](../runbooks/ds-dc-02/ground-truth.md)

| Проверка | Известно | Открыто |
|---|---|---|
| Схема и scope | По WSL пять корректно оформленных локаторов и scope mismatch во всех пяти | Типы и полные поля исходного JSON |
| ID, редакция, координаты | По WSL совпадают PDF, SHA, ID, физическая страница и таблица | Локальный прогон подлинного JSON |
| Цитаты, Unicode, регистр | По отчёту literals соответствуют цитатам по содержанию, value в нижнем регистре | Точные codepoints, кавычки, case, результаты plain/layout по каждому локатору |
| Literal/value/unit, condition/qualifier | Unit пустой, qualifier выражает смысловую роль, условия могут находиться в соседних ячейках | Дословная проверка полей и независимая проверка их связей |
| Строки таблицы | Локальный layout подтверждает две отдельные связи причина → действие | Привязка исходных локаторов к ячейкам и ручная сверка геометрии |
| Покрытие и текст вне claims | WSL считает вопрос раскрытым, но отмечает фразу о порядке | Связь предложений с claim ID и проверка утверждения «иных действий» по всей таблице |

Возможные последующие ошибки из-за регистра, Unicode, объединения колонок и строковых условий остаются гипотезами до проверки исходного JSON.

## Экспорт и воспроизведение

В доверенной WSL экспортёр читает существующую settled-запись Recovery по точному wire и stop. Он извлекает только CandidateAnswer и отклоняет неизвестные поля, дубликаты JSON-ключей и известные признаки чувствительных строк. При наличии согласованного raw_draft сохраняются точные UTF-8 байты. Если сохранён только объект, экспортируется его каноническое представление. Пропущенные поля не добавляются. Эвристический фильтр не удостоверяет отсутствие произвольных персональных сведений в свободном тексте. Проверить файл локально до передачи.

```sh
umask 077
unset DEEPSEEK_API_KEY
python -m ds_dc.candidate_fixture --ledger "$DS_DC_LEDGER/ledger.json" \
  --output "$DS_DC_PRIVATE/q01-candidate.json"
sha256sum "$DS_DC_PRIVATE/q01-candidate.json"
```

Вместо --ledger можно указать --receipt с приватным JSON самого calibration_result. Передавать только проверенный файл и его SHA. Ledger, GO, contract, provider envelope и handles остаются в WSL. При чувствительном содержимом выполнять replay в WSL и передавать только безопасные диагностические результаты.

```sh
env -u DEEPSEEK_API_KEY python -m ds_dc.evidence_lab replay \
  --fixture "$DS_DC_PRIVATE/q01-candidate.json" --sha256 "$Q01_CANDIDATE_SHA" \
  --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE"
env -u DEEPSEEK_API_KEY python -m ds_dc.evidence_lab matrix
```

Replay проверяет SHA кандидата, canonical freeze и Q01 wire. Используется сборка материалов Pilot и неизменённый V1. Офлайн-аудит продолжает проверку всех claims после первого scope mismatch и отделяет механические результаты от задач смыслового ревью. Smoke-тест воспроизводит invalid_locator на явно синтетическом кандидате поверх закреплённого корпуса.

## Синтетическая матрица

Полный suite на закреплённом корпусе — **204 passed, 0 skipped** (196 прежних и 8 новых), одно предупреждение Starlette/httpx. Для повторного прогона используйте переменные SATURN_SOURCE, DS_DC_CACHE, SATURN_BKD_PDF и SATURN_SLD_PDF из runbook и команду python -m pytest -q --tb=short.

Все 12 исходов V2 совпали с ожидаемыми. V1 draft — результат существующей проверки до публикации.

| Сценарий | V1 | V2, причина |
|---|---|---|
| Точное уникальное человекочитаемое имя | invalid_locator | supported_fixture |
| Другая редакция | invalid_locator | invalid_locator |
| Неверная цитата | quote_mismatch | quote_mismatch |
| Цитаты из разных строк | draft | semantic_pending |
| Другое поколение | draft | inapplicable_source |
| Значение из другой строки | draft | semantic_pending |
| Другая единица | draft | semantic_pending |
| Потеря предела | draft | semantic_pending |
| Потеря условия | draft | semantic_pending |
| Верная ссылка при неверном тезисе | draft | semantic_pending |
| Лишний тезис в свободном тексте | draft | invalid_contract |
| Обязательная последовательность без опоры | draft | semantic_pending |

Реальные DeepSeek операции и повторы Q01 — 0. Исторические wire, обычный live-допуск, поиск, сборка досье, Native PDF, Deep Thinking, publication gate и финансовые механизмы сохранены. [Проект Candidate Contract V2](../architecture/DS-DC-03A-CANDIDATE-CONTRACT-V2.md) · [Technical Evidence Verifier и DC-03B](../architecture/DS-DC-03A-TECHNICAL-EVIDENCE-VERIFIER.md)
