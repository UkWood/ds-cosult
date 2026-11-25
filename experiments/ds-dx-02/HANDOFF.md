# HANDOFF Architecture Session A — DS-DX-02-D-R3

25 ноября 2026 года · `UkWood/ds-cosult` · `experiment/ds-dx-02-d-unified-knowledge-compiler`

- Родительский HEAD R2: `d62b7fcefeacc945e0ef2fbd47190bdfa4ccdefe`
- Коммит реализации R3: `445ea6aba2dfc3ef1b2d6d1334f3b450aeaceb0f`
- Runtime digest: `9662d09cb62242798b1923e39504e8273a8d357e5b145ed3209dc08f1306dc98`
- Astro commit: `084d759487bfab6e111549c9b5469711ac5fc13e` · tree: `a5297822bf3a5e071b10cc1dca553481c1b84d47`

## Причина и исправление

R2 потребовал, чтобы смысловой ответ DeepSeek сразу служил исполняемым графом. В оплаченной операции `g0001.plan` модель указала строку `"1-12"`, внешние ID источников, незарегистрированные пути фотографий, внешние зависимости и gaps. Локальная проверка остановила весь процесс до загрузки PDF. Регрессия воспроизводит эти признаки из отчёта владельца, включая отдельно форму `tasks/gaps` без фактов. Первичный LIVE-checkpoint владельца остаётся местным.

Ядро R3 строит и проверяет граф по инвентаризации до обработки ответов. Небольшая карточка Astro проходит одним заданием. Текст PDF сгруппирован внутри одного провайдерского фрагмента, локаторы указывают на физические страницы оригинала. Соседние изображения идут пачками до трёх с ограничением размера сообщения. ID, область, зависимости и резервы назначает ядро. Порядок чередует Astro, PDF и самостоятельные изображения. Независимые базовые задачи сохраняют места под аварийным потолком при разбиении усечённого ответа.

Запрос разделяет `available_evidence` и `related_source_metadata`. Для PDF совместимые текстовые запросы используют тот же `file_id` и стабильный префикс, а локаторы и задачу передают в суффиксе. Фактический cache hit определяется по usage провайдера. DeepSeek может предложить темы, связи, условия, неопределённости и следующие шаги в извлечении. Рубрики фактов допускают проверенный slug. Некорректная рекомендация изолируется с кодом причины. Отдельных вызовов планировщика и платных исправляющих запросов для структурного отказа — 0.

Извлечение сохраняет принятые строки и отмечает структурный сбой как `PARTIAL`. Сырой текст ответа хранится в приватном checkpoint. В `coverage.json` есть карта задач, ожидаемая и подтверждённая область, пропуски, коды отклонения и хеши лишних ссылок. Независимые задачи продолжаются при доступном бюджете. `length` допускает ограниченное продолжение. Fusion сравнивает проверенные по структуре и локаторам записи нескольких источников даже при несовпадении тем. Возможные конфликты сохраняются как `unresolved`. Метки `UNREVIEWED` требуют инженерной оценки. CONSULT получает только переносимую KnowledgeBase и разрешённые иллюстрации.

Схема SourceArchive совместима с R2. Формат переносимого пакета остаётся schema 2 с дополнительными полями coverage. Старые LIVE-checkpoints R2 относятся к несовместимому runtime и остаются в отдельном каталоге. Для R3 нужен новый бесплатный preflight и новый финансовый state.

## Бесплатная приёмка

Linux · Python 3.12.14 · Poppler 26.05.0 · seccomp проверил `socket → EPERM` в preflight и дочернем процессе. **23 PASS, 0 FAIL, 0 SKIP**. Платные операции и расходы этой сессии — **0**. Mock проверяет протокол и границы данных. WSL-прогон владельца и инженерная проверка LIVE ещё впереди.

| Пакет | Группы / локаторы / изображения | Planner / extract / vision / fusion / upload / CONSULT | Факты | Статус и причина |
|---|---:|---:|---:|---|
| БКД-ПК-RF.2 | 18 / 220 / 196 | 0 / 18 / 70 / 9 / 4 / 1 | 230 | PARTIAL, три тестовых усечения |
| ARCHTOOL | 43 / 570 / 380 | 0 / 30 / 137 / 28 / 12 / 1 | 440 | PARTIAL, ZIP программы отложен как неподдерживаемый материал |
| Контроль затопления | 31 / 842 / 50 | 0 / 12 / 30 / 5 / 1 / 1 | 74 | COMPLETE_UNREVIEWED |

Архивы подготовлены из пинов R2. Для системы использованы сверенные публичные копии файлов из повторных скачиваний после HTTP 503.

| ZIP | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `c395bbc640fe4ade6b21d21792fb655e9000a3887e63562cf4a23739d8ea0079` |
| `mock-package-1.zip` | `413ce23200559e2a217b716bce6ef9fefe7f521ac39df33ec7746b21fce4d94d` |
| `mock-package-2.zip` | `e4c57fba158adf76257cafacaf9e8009423814e1a36c9ae9f63bb24079563756` |
| `mock-package-3.zip` | `6ee8c77057665c9c0338c9ccfb4e378578a6d9d533a56daafd074fe963404b6c` |

`mock-package-{1,2,3}.zip` соответствуют строкам таблицы. Каждый содержит `summary.json`, `coverage.json`, `knowledge.zip`, `compile.zip`, `consult.zip` и контрольные суммы. Повтор mock COMPILE сверил ZIP KnowledgeBase и прошёл с нулём новых вызовов. В mock CONSULT исходный архив удалён перед вопросом. Проверены блокировка UNKNOWN, запрет дубликатов, резервы, отдельный Owner GO для увеличения лимита и сверка checkpoint.

## Бесплатный расчёт пилотного графа

| Величина | Результат |
|---|---:|
| Группы / локаторы / визуальные кандидаты | 18 / 220 / 196 |
| Базовые операции | 0 planner, 16 extract, 68 vision, 4 upload |
| Разбор 80 физических страниц PDF | $0.018000000 |
| Сумма резервов базовых операций | $25.709520000 |
| Резерв первого вызова R3 | $0.309830400 |
| Аварийный предел чатов / верхняя граница резервов | 2048 / $634.550659200 |

Базовая сумма рассчитана на cache miss и максимальный разрешённый вывод, до условных разбиений и fusion. Значение 2048 ограничивает исполнение, а рабочий расход определяется фактическим usage. Ledger проверяет оба утверждённых лимита перед каждым POST и удерживает резерв при UNKNOWN. При предлагаемом лимите COMPILE $1.99 запуск может завершиться частичным пакетом.

## Независимый бесплатный WSL preflight

В уже подготовленной среде R2 выполните этот блок. `UTKC_HOME` — прежний каталог с `backend`, `site`, `venv` и тремя `source-*`. Существующий checkout должен быть чистым. Команда проверяет отдельный SHA реализации и пишет отчёты в новый каталог.

```bash
(
  set -euo pipefail
  : "${UTKC_HOME:?Укажите абсолютный путь к подготовленной среде R2}"
  branch=experiment/ds-dx-02-d-unified-knowledge-compiler
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin "$branch"
  git -C "$UTKC_HOME/backend" switch --detach 445ea6aba2dfc3ef1b2d6d1334f3b450aeaceb0f
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = 445ea6aba2dfc3ef1b2d6d1334f3b450aeaceb0f
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" \
    --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-r3"
  cd "$UTKC_HOME/preflight-r3"
  sha256sum -c DS-DX-02-D-preflight.zip.sha256 mock-package-{1,2,3}.zip.sha256
)
```

## Протокол Owner GO и LIVE

Сверьте приватный ledger R2 с биллингом. Отчёт владельца содержит один `SETTLED` на $0.0052677 (3111 miss, 3612 output, из них 1267 reasoning). Запишите в общей приватной сводке расход R2, утверждённые лимиты R3, фактические расходы R3 и сумму. При подтверждённом единственном списании остаются $1.9947323 COMPILE и $4.9947323 общего потолка. Для отдельного Owner GO предлагаются округлённые вниз пределы $1.99 и $4.99, дающие суммарные потолки $1.9952677 и $4.9952677 вместе с R2. При расхождении пересчитайте остатки по биллингу и согласуйте их с владельцем. Проверьте модель, Files/Vision и тарифы перед подтверждением контракта.

**LIVE-COMPILE после отдельного решения владельца.** Введите утверждённые лимиты через окружение, ключ через интерактивный запрос в WSL2.

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
bash compile-live.sh --sources "$UTKC_HOME/source-pilot" \
  --preflight "$UTKC_HOME/preflight-r3/preflight.json" --state "$UTKC_HOME/private-r3" \
  --knowledge "$UTKC_HOME/knowledge-r3-v1" --reports "$UTKC_HOME/compile-r3-v1" \
  --owner-go-usd "${COMPILE_GO_USD:?}" --total-go-usd "${TOTAL_GO_USD:?}" \
  --confirm-provider-contract
```

При возобновлении R3 используйте `--resume`, прежний `private-r3`, тот же pinned runtime и свежие выходные каталоги. Для утверждённого повышения передайте также `--budget-approval` с полями `stage`, `identity` из вывода CLI, `old_cap`, `new_cap`, `old_total`, `new_total` в целых нанодолларах и `owner_go` со ссылкой на решение владельца. Сверьте `knowledge.zip.sha256` и `DS-DX-02A-results.zip.sha256` в каталоге результата, разберите coverage и конфликты до CONSULT.

**LIVE-CONSULT после просмотра KnowledgeBase и отдельного решения владельца.** Выберите проверенный выпуск. Для PARTIAL требуется явный `--allow-partial` по решению владельца.

```bash
bash consult-live.sh --knowledge "$UTKC_HOME/knowledge-r3-v1" --state "$UTKC_HOME/private-r3" \
  --reports "$UTKC_HOME/consult-r3-v1" --questions "$PWD/configs/pilot-questions.json" \
  --owner-go-usd "${CONSULT_GO_USD:?}" --total-go-usd "${TOTAL_GO_USD:?}" \
  --confirm-provider-contract
(cd "$UTKC_HOME/consult-r3-v1" && sha256sum -c DS-DX-02B-results.zip.sha256)
```
