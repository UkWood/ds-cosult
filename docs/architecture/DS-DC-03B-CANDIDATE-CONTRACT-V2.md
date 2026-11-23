# Candidate Contract V2 · Нормативная версия candidate-answer/2

DC-03B использует только этот V2 контракт. Документ инициативы DC-03A и 2-lab являются историческим дизайном и лабораторией, совместимость с ними обеспечивается сохранением старого кода. В рабочий CAL wire V2 не включён.

## Формат входа

Сервер передаёт version, уникальный request_id и wire_identity реестра, вопрос, parts как отображение отдельного ID в текст части вопроса, короткие entity IDs и source IDs с безопасными названиями, а также прежние полные материалы. Для V2 wire_identity — отдельный SHA-256 канонической структуры версии, запроса, манифеста, частей и записей реестра. ID в реестре имеют короткий порядковый префикс и суффикс пространства запроса. Модели не нужно воспроизводить SHA источника, Git blob, canonical ID или геометрию PDF.

Системное правило для будущей интеграции: «Не выдумывай недостающие технические характеристики». Используй только ID текущего запроса. Разделяй утверждение и дословные фрагменты. Сохраняй условие, отрицание, предел и модальность, не предполагай обязательной последовательности. Покрой каждую часть либо явно отметь её unresolved. В независимый benchmark-эталон модель доступа не получает.

## Формат ответа

Строгие поля верхнего уровня: version, request_id, wire_identity, claims, answer_claim_ids, unresolved. Ключи claim: id, entity, kind, subject, value, unit, comparator, qualifier, condition, parts и evidence. parts, answer_claim_ids и unresolved — массивы ID. Claim ID уникальны. Ссылки проверяются по реестру. Для evidence допустимы role, source, page, quote и необязательный hint с table/row/column, индексы от нуля. page — физическая страница от единицы. Quote является дословной строкой ячейки после сведения whitespace и NFC. Hint проверяется, пропуск hint разрешён. Связь устанавливается сервером по типу и ролям фрагментов.

| kind | Необходимая структурная опора | Технические поля |
|---|---|---|
| quantity | subject, value, unit; при наличии condition/qualifier | value — десятичная строка, comparator eq |
| quantity_limit | те же роли, оператор в ячейке value | value — строка, comparator le/ge/lt/gt |
| quantity_range | те же роли, обе границы в одной value | value — массив из двух десятичных строк, comparator range |
| symptom | symptom в таблице известных troubleshooting-ролей | subject — фраза симптома, qualifier observed; condition, value, unit, comparator пусты |
| possible_cause | symptom и cause одной строки | subject — причина, condition — симптом, qualifier possible; value, unit, comparator пусты |
| conditional_action | cause и action одной строки | subject — действие, condition — причина, qualifier conditional; value, unit, comparator пусты |

Разрешены обычные ASCII знаки плюс/минус, десятичная точка или запятая и точное Decimal-сравнение. Тысячные разделители, единицы с конвертацией, Unicode-минус и неподдерживаемые формы отсеиваются в semantic_pending. Единицы регистрозависимы. Текст технических условий сравнивается целиком с NFC, whitespace и lower, без подмены слов, снятия отрицания или fuzzy matching. Близость фрагментов не доказательство.

Результат verifier для каждого claim содержит schema_valid, source_identity_verified, applicability_verified, evidence_verified, relation_verified, technical_status, covered_parts, reason_codes и восстановленные locators. Supported требует всех нужных проверок. Contradicted реализован для другого числа при проверенной идентичности остальных числовых атрибутов, включая форму оператора, единицу и условие. Неопределённость остаётся semantic_pending. Недопустимые поля, типы и ссылки дают invalid. Ошибка общей схемы или идентичности блокирует весь пакет.

Для DC-03C доступен список confirmed_claim_ids, включающий только запрошенные для ответа поддержанные утверждения. Доказанное покрытие требует независимой привязки claims к частям, а не пустого unresolved или декларации модели. Свободный answer_candidate в V2 отсутствует. Shadow-адаптер V1 сохраняет оригинал и строит лишь производное диагностическое представление. Он не выдаёт производное за модельный V2-ответ. [A-DS-DC-08](A-DS-DC-08-STRUCTURED-EVIDENCE-VERIFICATION.md)
