# DS-EC-AR-01 — Единый независимый Architecture Acceptance Review контрактов DS-EC-02–05

**Проект:** DS-консультант — отдельный Entity-Centric Conversational RAG для технических консультаций «Сатурна»  
**Дата проверки:** 18 ноября 2026 года  
**Репозиторий:** `UkWood/ds-cosult`  
**PR:** #1, `docs/ds-01c-benchmark-memory`, **OPEN / DRAFT / UNMERGED**  
**Проверенный исходный HEAD до review:** `ed0b2b93b90c04b975eb9c024a40c4f312e2ce61`  
**Роль:** независимая архитектурная приёмка, **не программное тестирование**  
**Итоговый вердикт: CHANGES REQUESTED — 4 BLOCKER, 8 IMPORTANT, 2 MINOR.**  
**Решение:** **единый контракт DS-EC-02–05 пока НЕ ПРИНЯТ как окончательное ТЗ на реализацию**. Основное архитектурное направление можно сохранить, но блокирующие пробелы надо исправить в существующем Draft PR #1 до повторного Review.

## 1. Рассмотренные источники и замороженная граница проверки

Прочитаны напрямую с ветки PR:

| Контракт | Проверенный Git blob SHA |
|---|---|
| `docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md` | `98880a8466708a84d3eea890026ac5dbf508fd01` |
| `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md` | `53cbbbd366e7d6d0cba96889e277b4ae6cb80e04` |
| `docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md` | `546a60f82fa6420ea4de6b95e4a5caecae5fa51b` |
| `docs/architecture/DS-EC-05-ATOMIC-CLAIM-VERIFICATION-AND-CONTROLLED-RENDERING.md` | `efb935ba61d99dc07cdb34fb4827254548993473` |

Также сопоставлены нормативные решения `DS-SEC-07`, `DS-SEC-08`, `DS-SEC-09`; индивидуальные отчёты DS-EC-02/03, 04, 05; проектные `PROJECT_STATE.md` и `ARCHITECTURE_LOG.md`. Предыдущие поэтапные проверки назывались **documentation/design consistency checks** и **не были** финальной независимой приёмкой комплекта.

**Принятые владельцем ограничения считаются неизменными:** строгая область «Сатурна», системное `Не выдумывай недостающие технические характеристики.`; сайт и одобренные PDF — доверенные и не содержащие Prompt Injection; риск — прямые инструкции посетителя; регистрация не требуется, одна активная сессия/IP, очистка технической памяти через 15 минут неактивности, сброс серии через 30 минут, 20 **принятых пользовательских вопросов**/IP/сутки включая локальные ответы, серверные паузы для Q6–Q10, Q11+ в поддержку; максимум 1 200 символов вопроса, 8 KiB тела HTTP, **10 000 токенов полного входа DeepSeek и 450 выходных**, не более одного платного вызова на принятый вопрос; отдельный общий бюджет, приватный аудит полных Q/A+IP+UTC сроком 30 дней при условии законного запуска. DS-SEC-09 заменил более раннее толкование «20 только платных POST».

## 2. Что архитектура уже делает правильно

| Область | Наблюдение | Оценка |
|---|---|---|
| Источник истины | Отдельные `Entity`, `Fact`, `Relation`, `EvidenceRef`, `SourceBundle`; посетитель не пишет технические факты | **ACCEPTABLE DIRECTION** |
| Доказательства | Зафиксированные site commit/blob/field и PDF bytes SHA-256/physical page; ссылки на точные утверждения | **ACCEPTABLE DIRECTION** |
| Область модификации | Модель, исполнение, версия, единицы и условия применимости обязаны сохраняться | **ACCEPTABLE DIRECTION** |
| Совместимость | Нельзя выводить совместимость по одинаковому Ethernet/RS-485 или косвенным связям | **ACCEPTABLE DIRECTION** |
| Состояния знания | Отдельные отсутствие сведений, недоиндексация, недоступный источник, противоречие, ошибка | **ACCEPTABLE DIRECTION** |
| Диалог | Упорядоченные `первый/второй`, коррекция сущности/версии, очистка старых anchors, фиксация snapshot | **ACCEPTABLE DIRECTION** |
| Goal Hijacking | Пользовательская команда не может стать API-role `system` либо доверенным Fact, модель не назначает правила проверки | **ACCEPTABLE DIRECTION** |
| Сборка ответа | Модель предлагает ограниченный план; независимые G0–G10 и шаблонный renderer не пропускают произвольные факты | **ACCEPTABLE DIRECTION** |
| Стоимость | Локальные ответы — 0 вызовов, сложные — максимум 1; минимальные источники вместо целых PDF; верхний предел 10k | **ACCEPTABLE DIRECTION** |
| Операции | IP/session/quota/cost/audit разделены, но транзакционная модель ещё не формализована | **NEEDS SPECIFICATION** |

Эта таблица подтверждает **согласованность направления**, а не доказанную надёжность несуществующей реализации.

## 3. Сводный список замечаний — BLOCKER

### BLOCKER CR-B01 — Нет доказуемого контракта полноты охвата источников для ответа «не указано»

**Место:** DS-EC-02 §2.1, §2.3, §6; DS-EC-03 §3–4; DS-EC-05 G3/G4/G8, §5–7.

`insufficient_evidence` определён через «properly searched approved available scope», а `VerifiedAnswerResult.source_coverage` заявлен, однако ни `SourceBundle`, ни `NeedResolution` не задают проверяемого **coverage/completeness receipt** для конкретной сущности, модификации и параметра. Поиск top-K/нескольких PDF-фрагментов может не найти нужное поле и ошибочно превратить неохваченный документ в `не указано`. Это затрагивает как отсутствие характеристик, так и **полноту выявления противоречий**.

**Требуемое исправление:** ввести контракт `SourceCoverageReceipt` (имя условно) со связанными `bundle_id`, `need_id`, точными включёнными/не включёнными источниками и редакциями, статусом полных bytes/parse/index/lookup операций, проверенной областью применимости (entity/variant/attribute), доказанными ограничениями полноты. Развести `complete_for_declared_scope`, `partial_index`, `source_unavailable`, `processing_error`; определять `insufficient_evidence` только при достаточной проверенной полноте **объявленной области**, а не обещании полноты всей документации мира. Для конфликта сканировать все применимые структурированные утверждения в проверенном ledger **вне урезанного LLM-пакета**.

**Доказательство закрытия:** офлайн-сценарии с характеристикой на невыбранной PDF-странице, незакреплённым PDF, неполным парсером, двумя противоречащими источниками (один не попал в top-K) и действительно отсутствующим полем. Проверяемые статусы должны различаться.

### BLOCKER CR-B02 — Не установлен единый исполнимый порог доказательственной пригодности Fact/Relation

**Место:** DS-EC-02 §2.2–2.3, §4–5; DS-EC-03 `packet_validation`; DS-EC-05 G3/G7 и §7.

У EvidenceRef есть `bytes_verified / locator_verified / extraction_verified / interpretation_reviewed`, у Fact — `candidate / extracted / verified`, у Relation — `proposed / source_verified / expert_reviewed`. Не определено, **какая комбинация состояний** и какие обязательные независимые проверки допускают каждый тип источника/атрибута к публичному ответу. Например, верные bytes SHA и номер страницы не гарантируют правильный столбец таблицы, знак неравенства, исполнение устройства или направление линии на схеме. Подтверждённый source link не делает любое утверждение допустимым.

**Требуемое исправление:** единая версия `EvidenceEligibilityPolicy` с матрицей site-structured / PDF-text / PDF-table / PDF-diagram / source-negative / relation; независимая проверка field/value/qualifier или участка страницы, identity/revision, unit/polarity, provenance integrity и применимости к нужному need. Для схем без проверенной интерпретации — явный `needs_support`/no claim. Отдельно определить порог runtime-публикации и `expert_approved` benchmark GT (не приравнивать их). Не заявлять, что вся документация требует экспертной разметки для каждого сайта-факта, если политика источников допускает автоматическую проверку точного поля.

**Доказательство закрытия:** таблица разрешённых состояний, machine-checkable eligibility outputs и отрицательные fixtures: неверный PDF table row, та же страница но другое исполнение, неверная единица/отрицание, relation с неверным направлением, quote correct but unrelated to claim.

### BLOCKER CR-B03 — Путь DeepSeek для разбора вопроса не связан с общим pre-dispatch guard и отдельным выходным контрактом

**Место:** DS-EC-03 §6 (Path 2); DS-EC-04 §6; DS-EC-05 G2, G5–G6, §8.

`G2 Entity and need resolution` допускает **модельный вызов** для разбора намерения, но обязательный контроль полного контекста **10 000 токенов** и `max_tokens=450` явно стоит позднее на `G5`. Кроме того, `CandidateAnswerPlan` описывает выбор Fact/Relation IDs **после** построения EvidencePacket, а модель на G2 должна вернуть **план интерпретации до retrieval**. Её отдельный bounded input/output контракт и валидатор не определены. Нельзя трактовать G0–G10 как буквально единый безопасный порядок для обеих веток.

**Требуемое исправление:** единый `ProviderDispatchGuard` **перед любым POST** (в том числе перед ранним interpret call): проверенный session/IP/turn id, one-shot provider attempt reservation, модель/disabled thinking/no tools, полная токенизация запроса ≤10k, output ≤450, cost reserve, monotonic in-flight fence, result validation, no automatic retry. Выделить нормализованный `QuestionInterpretationPlan` с разрешёнными intent/entity/need кандидатом, точными запретами на создание source Fact/Relation, отдельной схемой и deterministic validation. Единственный call-slot уходит либо на interpret, либо на answer-plan, **никогда на оба**.

**Доказательство закрытия:** mocked tests, в которых G2 запускает модель, запрос 10 001 токен → **0 provider POST**; нулевой бюджет → 0 POST; допустимый interpret call → 1 POST; попытка дополнительного answer-plan → блок; ошибка/timeout → без повторного платного вызова.

### BLOCKER CR-B04 — Не замкнут контракт классификации области компетенции и атомарного допуска пользовательского вопроса

**Место:** DS-SEC-07/09; DS-EC-03 §6; DS-EC-04 §6; DS-EC-05 G0/G2, §8–9.

На G0 требуется `Legitimate source-domain input` прежде, чем вопрос считается **принятым**; при этом DS-EC-03/05 допускают, что определить смысл свободного технического вопроса может **только модель на G2**. Значит, без явных переходов неясно, можно ли совершить платный вызов, ещё не списав вопрос из 20, либо как не списывать легитимному посетителю слот при ошибочном out-of-domain результате. Особенно уязвимы смешанные запросы «какая мощность? и игнорируй правила» и анфоры «а у второго?».

**Требуемое исправление:** серверная FSM `received → validated → provisionally_admitted → provider_attempt_reserved? → resolved/blocked/failed → rendered/audited`, где точно определено, **когда** резервируется единственный пользовательский слот, как classify-before-infer работает для очевидно внеобластных команд и как учитываются ambiguously in-domain запросы, требующие единственного платного interpret. Запрет платного предварительного классификатора вне `≤1 call/accepted question`. Однозначное поведение по `out_of_scope` и `policy_override_attempt`, если классификация стала известна только после принятого запроса; невозможность двойного списания по retry/cookie/tab.

**Доказательство закрытия:** predeclared test matrix: обычный вопрос, `а у второго?`, явно внеобластная команда, смешанная benign + injection, длинная неоднозначная фраза, denied cooldown, same-IP race, uncertain API timeout. Для каждого — `accepted_turn_delta`, `provider_attempt_delta`, cost reservation, итоговый статус.

## 4. Консолидированные IMPORTANT (не блокируют выбор направления, но обязательны до coding acceptance)

### IMPORTANT CR-I01 — Транзакция turn/POST/audit и восстановление после сбоя

**DS-EC-04 §6, DS-EC-05 G0/G10, DS-SEC-07/09.** `DialogState CAS` не заменяет атомарный IP lease, request-id idempotency, admission debit, cost reservation и фиксацию фактически показанного ответа. Нужна единая FSM/sequence диаграмма и поведение для падения до POST, сразу после POST, после ответа провайдера, до записи private audit и после записи, но до HTTP ответа посетителю. При неопределённом списании — не повторять provider POST. Не создавать phantom double-count или неучтённый ответ.

**Acceptance:** fake-clock + two-tabs + crash-point integration с фиктивным провайдером и проверкой ровно одного admission/POST по идентификатору.

### IMPORTANT CR-I02 — Согласовать общие enum/status/reason contracts и правила понижения ответов

**DS-EC-02 NeedResolution; DS-EC-03 need_outcomes; DS-EC-05 VerifiedClaim/final status.** Слои описывают разные похожие статусы: `conflict`, `source_unavailable`, `source_error`, `processing_error`, `internal_error`, `needs_support`; `missing_data` фигурирует как template/mode, но не конечный статус. Нужны централизованные versioned enums, явное mapping need → proof_state → final status/reason, детерминированное правило precedence для нескольких потребностей, источник ошибки vs факт отсутствия. `partial` допустим лишь с независимыми verified claims и видимыми причинами остальных need.

**Acceptance:** исчерпывающая cross-product таблица одиночного missing/ambiguous/error/conflict, смешанных partial и успешных cases; никакого `answered` при незакрытом обязательном need.

### IMPORTANT CR-I03 — Сквозная идентичность модификаций, переименований и обновлений SourceBundle

**DS-EC-02 §3/7; DS-EC-04 §8; DS-EC-05 G1/G7.** Правильные принципы декларированы, но нет соглашения о стабильном canonical `entity_id` vs конкретной revision, допустимых variant parentage и явной source-proven миграции при изменении ссылок сайта/новой документации. Нужно закрепить ключи, запрет случайного «наследования» Fact от family, инвалидацию answer/cache и cutover snapshot *между*, не посреди, turn.

**Acceptance:** renamed canonical route same entity, two variant aliases, firmware-specific fact, source-update while call in-flight, stale citation.

### IMPORTANT CR-I04 — Типизированный словарь характеристик, нормализация единиц и условий

**DS-EC-02 Fact, Relation; DS-EC-05 renderer/claim verifier.** Логически правильно сохраняются точные десятичные значения, диапазоны, отрицания и qualifiers, но ещё нет нормативного `attribute_dictionary_revision`, rules для conversion, `nullable vs not specified`, диапазонов и списков, направленности/транзитивности отношений. Без этого verifier может формально совпадать с ID, но неверно вывести единицу либо обобщить область применения.

**Acceptance:** dedicated synthetic fixtures `0,5 МПа`, `12.5 V`, `≤`, `±`, conditions/firmware, `false` vs unknown, list exhaustive vs partial; relation inverse never implicit.

### IMPORTANT CR-I05 — Качество естественных объяснений при строго контролируемой сборке

**DS-EC-03 §6–7; DS-EC-05 §6.** Backend templates повышают проверяемость, но могут дать нечитабельные/неполные объяснения для сложных эксплуатационных вопросов. До первой реализации зафиксировать допустимые output modes и минимальные readability/utility метрики: краткая характеристика, сравнение, обоснование несовместимости только при явном source proof, документная навигация, `не указано`, `нужен специалист`. Не переходить к unrestricted model rewrite, чтобы не разрушить доказательность.

**Acceptance:** blind human/owner review примеров с правильными facts и оценкой понятности, покрытия need и числа ложных отказов.

### IMPORTANT CR-I06 — Определить, что означает global USD circuit breaker для локальных ответов

**DS-SEC-07/08 и DS-EC-03/05.** Платный inference при пустом бюджете однозначно запрещён, однако G0 в DS-EC-05 включает `global budget` для **каждого** вопроса до определения локального/модельного пути. Не определено, обязаны ли 0-call факты/кэш/статические ответы оставаться доступны, если DeepSeek бюджет исчерпан. В DS-SEC-04 исходно речь о прекращении **платных** вызовов. Нельзя случайно блокировать бесплатные полезные ответы, но любая доступная локальная ветка обязана соблюдать IP/дневные квоты и защиту локального CPU.

**Предложение для отдельного owner policy choice:** global spend breaker блокирует все **платные POST**, но допускает заранее проверенную локальную 0-call ветку при соблюдении 20 вопросов/IP/day и anti-abuse guards; если полный останов всего чата предпочтителен — утвердить явно. Не считать это ранее принятым решением.

### IMPORTANT CR-I07 — Завершить real-source / Ground Truth readiness как отдельный этап

**DS-EC-02 источники, DS-EC-05 проверка.** По прежним owner WSL отчётам 3/12 PDF закреплены по байтам; экспертно утверждённого benchmark GT — 0; DS-LV-02 P4/P5 claim-by-claim factual review остаётся открытым. Корпус может быть доверенным по политике владельца и одновременно **не готовым к подтверждённой интеграционной оценке**. Нужен отдельный offline source-custody/locator validator и экспертная оценка узкого учебно-реального набора; запрет «Corpus Freeze» до прохождения.

**Acceptance:** pinned site manifest and selected authorized PDF source bytes/page mapping, expert-reviewed question-to-source fact samples, missing/conflict controls. Не включать приватный GT, исходные ограниченные PDF или сырые IP-логи в публичный PR.

### IMPORTANT CR-I08 — Уточнить эксплуатационные настройки и защиту персональных журналов перед pilot

**DS-SEC-07/09, DS-EC-04/05.** Владелец утвердил правила IP, сроки и структуру аудита, но фактический IANA timezone, бюджет USD/day/month, телефон/e-mail поддержки, trusted proxy topology, правовое основание/уведомление посетителя, доступ персонала, encryption/deletion/backups ещё не заданы. Это не препятствует **офлайн** созданию синтетических схем, но блокирует публичный пилот и реальную эксплуатацию.

**Acceptance:** явно утверждённый operator configuration manifest (без секретов в GitHub) + тесты proxy spoof, NAT, IP-lock, leakage, 30-day retention and purge, calendar/DST boundary.

## 5. MINOR

### MINOR CR-M01 — Убрать исторически устаревшие фразы из активных разделов без удаления аудита

В отдельных прежних proposal/review ещё встречаются слова `candidate` / `pending` о 15m memory и 20 billable-only turns, хотя DS-SEC-09 уже утверждён и ссылки поправлены. Поднять явное `CURRENT / SUPERSEDED` в начале каждого документа; историческую хронологию owner decisions **не переписывать**.

### MINOR CR-M02 — Зафиксировать формат схем и терминов для будущих coding tasks

Выбрать одно имя для `QuestionNeeds`, `NeedResolution`, `CandidateAnswerPlan`, `QuestionInterpretationPlan`, `VerifiedAnswerResult`; версионировать enum, locator и JSON Schema; определить способ сериализации и идентичность `id`, `revision`, `bundle_id`, а также отделить публичные поля от приватных. Metadata-only document link не должен выглядеть как доказательство произвольного свойства.

## 6. Обязательный набор офлайн-проверок для повторной архитектурной приёмки

Это **проект критериев**, не выполненные тесты; существующие 30 MEM + 45 EC5 сценариев пока лишь записаны.

| Gate ID | Обязательное наблюдение |
|---|---|
| AR-T01 | Полный source coverage receipt: действительно отсутствующий атрибут vs непроиндексированный PDF vs ошибка парсера |
| AR-T02 | Истинное противоречие обнаруживается во всём ledger, даже если один документ не вошёл в prompt |
| AR-T03 | Подтверждённая source location, но неверная строка/колонка/версия → Fact не eligible |
| AR-T04 | Same Ethernet/RS-485 без явной Relation → совместимость не утверждается |
| AR-T05 | G2 question parser 10,001 токен / USD 0 → 0 provider calls |
| AR-T06 | One-call slot: interpret используется → дополнительный answer-plan запрещён |
| AR-T07 | Внеобластная команда без допустимого технического question не расходует слот, no provider |
| AR-T08 | Смешанный технический вопрос + spoofed system → только допустимый технический need, ни системного override, ни новых Facts |
| AR-T09 | 20 локальных вопросов/IP/day → 21-й заблокирован, provider_attempts=0 |
| AR-T10 | 9 local + 11 provider вопросов → 20 turns, 11 POSTs, 21-й заблокирован |
| AR-T11 | 15m память очищена, 30m серия сохранена до своего TTL, день не сброшен |
| AR-T12 | Один IP, две вкладки/куки, CAS/lease/fencing/idempotent replay → ни утечек, ни double POST |
| AR-T13 | Provider POST неизвестно оплачен после timeout → никакого автоматического retry |
| AR-T14 | Bundle обновился в середине turn → ответ на pinned старом bundle, следующий — с проверенной migration |
| AR-T15 | Fact ID корректный, но модель/qualifier либо страница источника неверны → отклонение |
| AR-T16 | Model `answered` при отсутствующем need → безопасный `partial/needs_support` |
| AR-T17 | Неожиданная ошибка verifier → `error`, не «данных нет» |
| AR-T18 | Полный вход 10,000 допускается, 10,001 блокируется до оплачиваемого POST; output ≤450 |
| AR-T19 | Проверенный простой факт → локальный ответ с точной ссылкой, читаемость и 0 model calls |
| AR-T20 | Raw IP/Q&A/UTC журнал существует только в restricted storage с TTL; публичный PR без персональных данных |
| AR-T21 | Простая локальная ветка при исчерпании USD обрабатывается в согласованном с владельцем режиме |
| AR-T22 | Все статусы `NeedResolution → VerifiedClaim → FinalStatus` связаны versioned mapping и полным тестовым покрытием |

После исправления контрактов возможна **архитектурная offline desk-check** повторная приёмка; после coding GO — отдельные executable mocks and integration tests. Никто не должен выдавать перечисленные тесты за уже прошедшие.

## 7. Решение по объёму первого прототипа

**Рекомендуемое первоначальное ограничение реализации** (НЕ новое разрешение писать код):
- read-only сайт и approved PDF **передают проверяемые факты в локальный индекс**, без произвольных внешних URL/встроенного поиска провайдера;
- system/device/software/variant Entity, source-bound scalar/range Fact, explicit typed Relation; не делать автоматические рекомендации по проводке или безопасности из картинки;
- локальный exact/alias/FTS поиск как базовая линия; embeddings только после измеренных retrieval misses;
- прежде всего single fact, comparison, relationship and document-navigation, а также missing/conflict/clarification/partial;
- DeepSeek только как **опциональный единственный** interpret или selection call по allowlisted schema; никакого второго LLM verifier и LLM rewrite;
- server-side quota/budget/source/citation/privacy controls действуют для всех веток, 0-call ответы учитываются в 20/day;
- полный официальный 12-PDF корпус и экспертный benchmark GT **не подразумеваются автоматически готовыми**; для первого пилота требуется явно выбранный разрешённый и pinned подкорпус.

Первое coding задание должно начинаться с **офлайновых schemas, fixtures, validators и mocked provider**, а не с live оплачиваемого API или публичного деплоя.

## 8. Результат приёмки и правила перехода

**ФИНАЛЬНЫЙ ВЕРДИКТ: CHANGES REQUESTED — 4 BLOCKER, 8 IMPORTANT, 2 MINOR.**

Все замечания консолидированы именно в этом отчёте. Новых независимых «поштучных» замечаний после исправлений без выявленного вновь доказанного дефекта быть не должно. Для перехода к повторному Acceptance Review:
1. исправить **все четыре BLOCKER** в существующих DS-EC-02–05, не меняя принятую DS-SEC-07/08/09 политику;
2. закрыть или согласовать owner disposition **каждый IMPORTANT**; MINOR исправить вместе с ним без расширения архитектурного scope;
3. создать проверяемые статусы/таблицы и synthetic fixtures для AR-T01..22 как спецификацию будущих тестов;
4. при повторной проверке указать новый Git head, обновлённые blob SHA и целевые ссылки по CR IDs;
5. **только после отдельной owner acceptance архитектуры** разрешается подготовить узкое кодовое ТЗ, и **только по отдельному GO** начинать реализацию.

**НЕТ разрешения:** Merge PR #1, DS-02 implementation, production/pilot, Corpus Freeze, платные DeepSeek HTTP (DS-QV-01 6/6 полностью использованы), модификации NEW RAG (`UkWood/LLM-RAG-chat-bot`) или изменения доверенного источника `UkWood/Saturn-Main-Site` (READ-ONLY).

**Примечание:** все BLOCKER/IMPORTANT — **пробелы/противоречия архитектурных документов**, а не ошибки исполнения: реализация на данном этапе не создавалась и программные тесты не запускались.
