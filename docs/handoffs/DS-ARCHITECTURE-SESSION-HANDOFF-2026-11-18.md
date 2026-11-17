# DS-консультант — Architecture Session A: передача в новый чат

**Дата:** 2026-11-18. **Статус:** handoff, никаких новых API-вызовов и Merge.
**Проект:** независимый Alternative Saturn AI Consultant — Entity-Centric Conversational RAG.
**Точная точка возобновления:** P8: offline preflight PASS, TURN-1 разрешён, **но его платный результат НЕ получен в прежнем чате**.

## 1. Управление

- Продолжай в роли Architecture Session A (архитектура, планирование, задания Linux/WSL, независимый Acceptance Review, сохранение решений/результатов в GitHub).
- Единственный рабочий репозиторий — **UkWood/ds-cosult** (именно `ds-cosult`), **Draft PR #1**: https://github.com/UkWood/ds-cosult/pull/1, ветка `docs/ds-01c-benchmark-memory`. PR по последней проверке OPEN, Draft, не merged.
- Последний head **до** этого handoff: `eff0e74c3a5793476638a753994e58f057d882a7`. Проверь новый HEAD самостоятельно; он изменится от записи handoff.
- Проект **строго независим от NEW RAG** (`UkWood/LLM-RAG-chat-bot`); не менять там файлы, ветки, PR или решения.
- `UkWood/Saturn-Main-Site` — **READ-ONLY**. Не писать в репозиторий сайта.
- Merge, production, DS-02 coding, Pilot, Corpus Freeze — **только по отдельному явному GO владельца**, которого нет.
- Существующий direct DeepSeek API: `https://api.deepseek.com`, `deepseek-flash`, ADR-0004; AI Tunnel ADR-0003 superseded. Модель по факту является alias, не придумывать закреплённый model version.
- Владелец выполняет одну полученную от Architecture Session A команду в Ubuntu WSL и возвращает вывод; после каждого содержательного шага сохрани evidence, Acceptance, state и history **в существующей ветке и PR #1**.
- Владелец **запретил лишние `Enter P...-APPROVED`** в новых скриптах. Не спрашивай их; сохрани `getpass` для ключа, checksum, одноразовые markers, no retries, redacted JSON, контроль бюджета, TTY. Решение `docs/decisions/DS-LV-02-OPERATOR-INPUT-POLICY.md`.
- Не спрашивать/публиковать секреты и API key. Не загружать реальные PDF «Сатурна», закрытые Core/GT, персональные/конфиденциальные данные без отдельного согласия. Не изменять принятую историю.

## 2. Архитектурная идея и исследовательский статус

Исследуем прямой DeepSeek API с нативными веб-инструментами, Files PDF Text/Rich и OCR как основу будущего **Entity-Centric Conversational RAG с иерархическими досье технических сущностей**. **Локальное дообучение LLM не используем**. Сейчас валидация возможностей, а не внедрение.

- DS-01 benchmark: W/A/B/C0 и B-text/B-entity; 12 Pilot, 60 Core (5 на категорию), 8 диалогов, 24 document tasks; 17 fact candidates.
- `0 экспертно утверждённых Ground Truth`; текущие технические отношения/графы ещё требуют экспертной верификации. DS-CORPUS-1.0 НЕ frozen.
- Site snapshot candidate `UkWood/Saturn-Main-Site` commit `084d759487bfab6e111549c9b5469711ac5fc13e`, tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`, только чтение.
- Из 12 настоящих PDF 3 локально SHA-pinned по Linux-отчёту, остальные 9 ещё не закреплены; 6 PNG-страниц просмотрены в Linux; архитектура не делала независимого побайтового аудита всех оригиналов.
- Главные долгосрочные ограничения: private Core/GT не публиковать в публичный репозиторий, source custody/GT и billing не подтверждены.

## 3. Последняя матрица DS-LV-02

| Фаза | Результат к переходу | Замечания |
|---|---|---|
| P1 Thinking | PASS | завершён, платный GO израсходован |
| P2 standalone Search | PASS | завершён, GO израсходован |
| P3 native URL read | PASS WITH REVIEW NOTES | fixture/language, GO израсходован |
| P4 native Web Search | PASS WITH REVIEW NOTES | GO израсходован |
| P5 Thinking + Search | PASS WITH REVIEW NOTES **по tool-capability** | 1259-символьный полный ответ не подвергнут claim-level проверке: `factual_answer_gate=NEEDS_SOURCE_REVIEW`; не считать фактическое качество полностью принятым |
| P6 Text vs Rich Files | PASS WITH REVIEW NOTES | **9/9 HTTP израсходованы**, не повторять |
| P7 direct OCR | PASS WITH REVIEW NOTES | **1/1 HTTP израсходован**, не повторять |
| P8 4-turn chat | **OFFLINE PREFLIGHT PASS; TURN-1 следующий** | нет live-JSON в чате; если пользователь уже запускал, повтор запрещён |
| P9 финальный аудит | NOT STARTED | **только offline, 0 HTTP/$0**, после P8 |

**P6:** один синтетический одностраничный PDF (1031 bytes, SHA256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286`). TEXT правильно вернул FENIX-17 12.4 L TX-731 и ORBIT-5 6.8 L RB-204; цвета/число фигур недоступны. RICH правильно вернул оба устройства **и 2 квадрата: красный и синий**. DELETE обоих файлов HTTP200/`deleted:true`; для TEXT старое требование GET404 ошибочно: per-file GET показал 400, но отдельный read-only `GET /files` дал пустой полный список **до TTL expiry**, что закрыло CR-P6-01. Оригинальный P6-TEXT JSON **НЕ переписывать**. RICH DELETE подтверждён полным списком сразу. Суммарно **9/9 HTTP**, peak pricing estimate **$0.0008733**, фактический счёт не подтверждён. Acceptance `docs/acceptance/DS-LV-02-P6-FINAL-ARCHITECTURE-ACCEPTANCE.md`.

**P7:** отдельный `POST /v1/tools/ocr` без Files API и без Chat. Один HTTP200; `ocr.result`, 1 страница, индекс0, finish `stop`, все 6/6 синтетических маркеров, 226 OCR chars, 2708 ms; usage 401+84=485 OCR tokens **справочно (не биллинг chat)**. Расчётная стоимость страницы **$0.000225**, фактическая неизвестна. Графика не распознана в text_recognition. **1/1 HTTP**, GO израсходован. Acceptance `docs/acceptance/DS-LV-02-P7-ARCHITECTURE-ACCEPTANCE.md`.

## 4. Бюджеты, принятые владельцем

Владелец дал **общее разрешение P6–P9 с осмотрительными лимитами**. Никаких повторных магических подтверждений и отдельного GO на каждый запрос в согласованном scope. Организационный бюджет **$0.05 USD (НЕ server hard cap)**.

| Фаза | USD организационный | HTTP ceiling | Известные использованные |
|---|---:|---:|---:|
| P6 | $0.02 | 9 | 9 |
| P7 | $0.01 | 1 | 1 |
| P8 | $0.02 | 4 | 0 **по переданным в чат данным** |
| P9 | $0 | 0 | 0 |
| Итого | $0.05 | 14 | 10 **наблюдаемых** |

P6+P7 peak estimates суммарно **$0.0010983** (не фактический debit). Новое превышение, повтор, несинтетические данные, другие модели/инструменты или расширение HTTP плана потребуют отдельного решения владельца.

## 5. Точная точка возобновления: P8 TURN-1

- Рабочая машина владельца: **Ubuntu WSL**, каталог `~/ds-consult-validation`.
- P8 скрипт `scripts/validation/ds_lv_02_p8_dialogue.py` закреплён в SOURCE COMMIT `49dba55308e83dcd136c5620c43322b4e186ba3e`, Git blob `28c22cad5b27a6a0e7063b7a3608dbd3aac0075a`, **owner-reported local SHA256**:
  `6ca43fe2031a542700e46c8bd4f931115100934d9d0cbde0e5be47e76af19b3e`.
- `python3 -m py_compile` PASS и `--self-test` PASS: 4 turns, `deepseek-flash`, `thinking.disabled`, no tools; **0 requests/$0**. Evidence `docs/evidence/DS-LV-02-P8-OFFLINE-PREFLIGHT.md`.
- На момент P8 offline отчёта **не было** файла `logs/ds-lv-02-p8-dialogue-private.json` и markers/reports всех четырёх turns; **но** владелец мог уже выполнить ранее выданную TURN-1 команду без публикации JSON. **Не повторять, если существуют state/marker/report.**
- Последняя команда, переданная владельцу для P8-TURN-1:
```bash
set -euo pipefail
cd "$HOME/ds-consult-validation"
echo "6ca43fe2031a542700e46c8bd4f931115100934d9d0cbde0e5be47e76af19b3e  scripts/validation/ds_lv_02_p8_dialogue.py" | sha256sum -c -
if [ -e logs/ds-lv-02-p8-dialogue-private.json ] || \
   [ -e logs/ds-lv-02-p8-turn-1-attempted.marker ] || \
   [ -e logs/ds-lv-02-p8-turn-1-redacted.json ]; then
    echo "STOP: P8-TURN-1 уже запускался или обнаружено состояние диалога."
else
    python3 scripts/validation/ds_lv_02_p8_dialogue.py --turn-1
fi
```
- **В новом чате первым делом уточнить наличие существующего TURN-1 redacted JSON или предоставить одну защищённую команду.** Нельзя автоматически инициировать платный вызов от имени пользователя.
- TURN-1: два учебных устройства, ответ о `ЛИРА-17: 12 В, RS-485`. TURN-2: «А у второй?» → `ОРБИТА-5: 24 В, Ethernet`. TURN-3: исправление интерфейса ЛИРА-17 на Ethernet, 12 В прежние. TURN-4: у обеих Ethernet, но рабочая температура ОРБИТА-5 не указана, **не выдумывать**.
- Каждый TURN: отдельный client-side POST `/chat/completions`, `max_tokens=192`, without Thinking/tools, marker `O_EXCL` before POST, сохраняется private conversation history с хэшами и безопасный redacted JSON. После каждого TURN Architecture **проверяет correctness, http200, model, finish stop, отсутствие tool calls и reasoning, ответ SHA, usage, estimated expense**, записывает evidence/Acceptance в существующем PR и даёт только **одну** следующую команду.
- `status=TURN_COMPLETE_REVIEW_NEEDED` у скрипта не равен независимой архитектурной приёмке. Если сбой, тайм-аут, ошибка или marker уже существует — STOP, не повторять автоматически.

## 6. Основные источники и порядок работы

- PR #1: https://github.com/UkWood/ds-cosult/pull/1
- State: `docs/status/PROJECT_STATE.md` — **хронологический файл с устаревшими ранними текстами, приоритет у последних дополнений/acceptance**.
- History: `docs/history/ARCHITECTURE_LOG.md`.
- Blanket GO: `docs/tasks/DS-LV-02-P6-P9-OWNER-BLANKET-GO.md`.
- P8 source & plan: `scripts/validation/ds_lv_02_p8_dialogue.py`, `docs/tasks/DS-LV-02-P8-FOUR-TURN-DIALOGUE-PROTOCOL.md`.
- P8 accepted preflight: `docs/evidence/DS-LV-02-P8-OFFLINE-PREFLIGHT.md`.
- P5 open factual claim review: `docs/acceptance/DS-LV-02-P5-ARCHITECTURE-ACCEPTANCE.md`.
- P6/P7 final reviews: `docs/acceptance/DS-LV-02-P6-FINAL-ARCHITECTURE-ACCEPTANCE.md`, `docs/acceptance/DS-LV-02-P7-ARCHITECTURE-ACCEPTANCE.md`.
- Operator UX: `docs/decisions/DS-LV-02-OPERATOR-INPUT-POLICY.md`.

**Задача новой сессии** — продолжить строго с P8 TURN-1 evidence/запуска, по одной команде и независимому review каждого TURN, закончить P9 офлайн-аудитом, после чего вынести отдельные архитектурные рекомендации по GT/реальному корпусу, не открывая DS-02 и не объединяя PR без владельца.

**Статус на момент handoff:** никаких новых DeepSeek API вызовов, никакого Merge, production или изменения NEW RAG в ходе этой передачи.
