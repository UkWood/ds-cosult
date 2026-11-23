# DS-DC-02-CAL-R · Передача Architecture Session A

**CAL-INC-01 OBSERVABILITY FIX COMPLETE — READY FOR OFFLINE ACCEPTANCE AND INCIDENT RECONCILIATION**, с оговоркой о сверке внешней матрицы. Отдельный отчёт Linux Validation Session со списком OBS-01–OBS-20 отсутствовал среди доступных материалов. Ниже приведены воспроизведённые проверки по сценарию задания. До получения списка покрытие по исходным номерам OBS не подтверждено.

База `a5f3012e1fb9798848914a0f00908524981475c4`, существующий Draft PR #4. Реальные обращения DeepSeek — 0, расход $0. Исходные операции CAL-01 и permit не читались, не изменялись и не использовались в тестах. [Draft PR #4](https://github.com/UkWood/ds-cosult/pull/4)

## Инцидент и реализация

21 ноября 2026 в 14:38:50 МСК началась первая загрузка РЭ БКД. Через 10 073 мс операция стала `provider_unknown`. Подтверждённых upload, bindings и Chat POST — 0. Удержано $0,014625 за попытку на 65 страниц. Отменено $0,333375 за три незапущенных upload и chat. Остаток локального бюджета $2,485375. Причина и внешнее начисление неизвестны. `response_received` в исходной записи отсутствует. Следующая платная операция остаётся заблокированной.

- NativeD1 различает транспорт, HTTP-статус, чтение, декодирование, схему, метаданные и финансовую интерпретацию. Ledger атомарно сохраняет диагноз рядом с состоянием операции. Для ответа с заголовками сохраняется HTTP-статус, включая HTTP 200 с невалидным телом.
- Сырой error body, сообщения исключения, хедеры, секреты, handles и произвольные вложенные usage-поля в диагноз не попадают. Из error envelope извлекается лишь числовая категория, совпадающая с документированным HTTP-статусом, в пределах 4 КиБ. Если тип или число не распознаны, поле остаётся null. Черновик CAL записывается в прежний приватный журнал после проверок usage и контрактных полей, usage сохраняется в нормализованной форме. Содержание `reasoning_content` не записывается.
- Неизвестный результат продолжает удерживать резерв и блокировать платную серию. Сохранены отмена незапущенных операций, дедупликация, GO, exact wire, corpus pin и строгий ordinary Context Guard. Новых механизмов разблокировки нет. [A-DS-DC-05](../architecture/A-DS-DC-05-PROVIDER-OBSERVABILITY.md)

## Сверка контракта

Все шесть официальных страниц вернули proxy CONNECT 200 и HTTP 200. Документированный порядок `purpose` перед file совпадает с HTTPX multipart в NativeD1. `text_recognition` подходит для PDF. `expires_after[anchor]=created_at` и `expires_after[seconds]=3600` входят в документированный диапазон 3 600–2 592 000. `expires_at` присутствует при заданном сроке и отражает Unix-время. Оставлена проверка `expires_at - created_at == 3600`. API не заявляет отдельную точность округления или допустимое расхождение между полями. Ранее DS-LV-02 P6 использовал тот же порядок и запрашивал 3600, но его обезличенный отчёт не содержит `created_at`, поэтому точную разность по нему вычислить нельзя. [File Parsing](https://api-docs.deepseek.com/guides/document_parsing/) · [Files API](https://api-docs.deepseek.com/guides/files_api/) · [Create File](https://api-docs.deepseek.com/api/create-file/) · [P6-TEXT](../evidence/DS-LV-02-P6-TEXT-RESULT.json)

Документация определяет `filename` как имя файла и `bytes` как размер исходного файла. Точный echo имени, полный regex, предельная длина ID и допуск часов в 30 секунд остаются локальными проверками безопасности. В официальных примерах используется префикс `file-api-`. P6 проверял этот префикс и expiry, но полного ID и достаточных данных для сравнения метаданных в доступных результатах нет. Отдельный артефакт DS-LAB-06 Native PDF в рабочем репозитории не найден. Оснований ослабить проверки в этой поставке нет. [Create File](https://api-docs.deepseek.com/api/create-file/) · [Retrieve File](https://api-docs.deepseek.com/api/retrieve-file/) · [List Files](https://api-docs.deepseek.com/api/list-files/)

Провайдер документирует 120 с на загрузку и 120 с на разбор, до ответа при разборе может не быть данных. Параметры клиента оставлены прежними: connect 8 с, write/read/pool 250 с для upload, ограничения HTTPX по отдельным фазам, не общий deadline. Отключение клиента может не остановить успешную обработку и начисление. HTTP 408/504 и длительность 10 073 мс сами по себе не устанавливают причину или финансовый результат данного инцидента. [File Parsing](https://api-docs.deepseek.com/guides/document_parsing/) · [Error Codes](https://api-docs.deepseek.com/quick_start/error_codes/)

## Диагностическая матрица по доступному заданию

| Проверка | Ожидаемый и подтверждённый результат |
|---|---|
| Connect/read/write timeout до headers, общая сетевая ошибка | transport, фиксированный reason, response_received=false |
| Read timeout после headers | response_read, статус 200, response_received=true |
| HTTP 400/401/402/408/413/429/500/504 | http_status, номер, unknown для CAL. Подтверждена безопасная числовая категория 402, произвольные значения и вложенные данные отброшены. Для 504 использован HTML body |
| Повреждённый JSON и JSON неподходящего типа с HTTP 200 | json_decode и response_schema_validation соответственно |
| id, object, purpose, filename, bytes, created_at, expires_at | По каждому проверено отсутствующее поле, неверный тип и несовпадающее значение |
| TTL и конфликт file ID | ttl_mismatch и id_collision, новой привязки нет |
| Исключение финансового интерпретатора | financial_accounting, безопасный код, удержание полного резерва |
| Прежняя форма ledger | Читается без диагностических полей, запрет последующей операции при unknown сохранён |
| Финансовая последовательность CAL upload при каждом неопределённом fault | Одна попытка upload, удержаны $0,014625, ноль Chat POST и новых bindings. Повтор с новым request ID отклонён |
| Строгий типичный сценарий CAL-PREP | Существующие тесты подтверждают порядок Q01/Q02, блокировку неизвестного/неполного usage и overage, отсутствие автоповтора и сохранение обычного допуска |

Полный suite: **192 passed, 0 skipped**, одно предупреждение Starlette/httpx. Включены прежние 165 тестов и 27 новых fixture-проверок. Исходная матрица консультаций — 6 PASS / 6 BLOCKED, дополнительные 7 PASS / 1 BLOCKED. Freeze совпал байт-в-байт. Для воспроизведения использовать полный fixture corpus, выполнить `python -m pytest -q --tb=short` и `python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" --evaluate-dc02 /tmp/dc02-calr-eval` без ключа. [Тесты](../../tests/test_dc02.py) · [Runbook](../runbooks/DS-DC-02-LIVE.md)

При дальнейшей сверке нужны доказательства провайдера по исходной операции и решение Architecture Session A о сценарии A, B или C. Сверка не разблокирует CAL-01 или CAL-02 автоматически. [Проект Incident Recovery](../runbooks/ds-dc-02/CAL-INC-01-RECOVERY-DRAFT.md)
