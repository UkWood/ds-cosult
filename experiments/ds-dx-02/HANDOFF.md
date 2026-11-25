# HANDOFF Architecture Session A — DS-DX-02-D-R4

25 ноября 2026 года · `UkWood/ds-cosult` · `experiment/ds-dx-02-d-unified-knowledge-compiler`

| Пин | Значение |
|---|---|
| R3, база реализации | `445ea6aba2dfc3ef1b2d6d1334f3b450aeaceb0f` |
| R3, родитель ветки R4 | `27e27559197fa17a6630e2585f13f986d08cfeae` |
| R4, коммит реализации | `a1dd50de04bad2ab412d3e9acf253e4b5371b912` |
| R4, runtime SHA-256 | `f9fc4759cd4ee37c9b8b8059e278452153bc73474c5d4cc752477427f735af93` |
| Astro commit / tree | `084d759487bfab6e111549c9b5469711ac5fc13e` / `a5297822bf3a5e071b10cc1dca553481c1b84d47` |

## Что проверяет R4

На реальном R3 15 из 17 генераций закончились `length`. Reasoning занял 103 176 из 115 604 completion tokens (89,25%). В первых текстовых запросах он занял все 8192 токена, в первом визуальном — все 4096. При этом часть других ответов с `length` дала пригодные записи. Отдельный UNKNOWN `g0002-visual-002` остался без checkpoint, HTTP-статуса и исключения. Причина этого UNKNOWN остаётся неизвестной. Агрегированный CSV подтверждает учтённые объёмы, но не устанавливает исход отдельного запроса.

R4 сохраняет детерминированный граф D и ноль planner. JSON output включается независимо от Thinking. Disabled, Low и явно выбранный High пинятся в запросе и журнале. В R4-A используются только Disabled и Low. Если подтверждённый usage показывает полный exhaustion на reasoning с пустым content, результат остаётся PARTIAL, без дочерних запросов. Для смешанного усечения сохраняются валидные факты и допустимо ограниченное разбиение полного графа. Неизвестные reasoning tokens представлены как `null`. Некорректный необязательный topic заменяется рубрикой задания с диагностикой. Область локальной неопределённости сохраняется, точные дубли объединяются с основаниями, разные условия остаются отдельными. Независимо подтверждённую связь можно зарегистрировать в отчёте сверки.

Транспорт записывает PENDING до POST, сохраняет приватные UTC, размеры, хеши, идентификаторы при наличии, стадию, тип ошибки, HTTP-статус и ограниченную классификацию provider error. Отдельный durable marker удерживает блокировку, если запись итогового ledger не удалась. Сырой response и проверенный result сохраняются приватно, когда это возможно. Безопасный ZIP содержит сводные метаданные. UNKNOWN/PENDING сохраняют резерв и блокируют новые операции. CONSULT по-прежнему работает с переносимой KnowledgeBase schema 2. SourceArchive R2/R3 совместим, нового снимка для R4 не требуется.

## Бесплатная приёмка

**32 PASS, 0 FAIL, 0 SKIP.** Старые 23 теста сохранены под прежними именами. Mock усечения уточнён до валидного префикса фактов, чтобы проверять обоснованное разбиение. Дополнительные 9 проверок закрывают R4-01–12.

| Критерии | Доказательство |
|---|---|
| R4-01–04 | Режимы и JSON, 8192/8192 и 4096/4096 без дочерних POST, mixed length, optional usage, нормализация topic, отклонение чужих локаторов и изображений, регрессия R2/R3 |
| R4-05–06 | HTTP 429, тайм-аут при чтении, ошибка JSON оболочки, usage mismatch, сбой result и ledger, read-only сверка и удержание резерва |
| R4-07–09 | 6 chats + 1 upload, равенство payload внутри пар кроме режима, остановка при UNKNOWN на каждом из семи шагов и отказ до POST по бюджету |
| R4-10–12 | Scoped unresolved, независимая аттестация связи, три прежних пакета, seccomp EPERM, replay с нулём новых вызовов, контрольные суммы ZIP |

В облачной проверке прошли БКД-ПК-RF.2 (PARTIAL, инъекции трёх смешанных усечений), ARCHTOOL (PARTIAL, неподдерживаемый ZIP) и «Контроль затопления» (COMPLETE_UNREVIEWED). Дополнительный CLI smoke проверил `prepare`, `freeze`, read-only `reconcile` на синтетических финансовых данных и отказ облачного LIVE до создания state.

| ZIP | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `5356f714b67ee6ca0a6006d5d04eafad76cec9f20f25d68a9a8a7b741b69b284` |
| `mock-package-1.zip` | `4ebda7d43e04705896f01ec2a909fb6c6021b18e30faf7a8140c7a3ac8c57259` |
| `mock-package-2.zip` | `0ca05228f4f74cb9bcec05ddefd8cc00ae999109438087a2d9e7d2d5aa04c62f` |
| `mock-package-3.zip` | `06ba56240668190b509a87a7b797ea10b294d68bfee5814e5cb75245dc3bd6de` |
| `r4-a-mock.zip` | `38646e1f59b32647bed863631cdca757ce194db84998a1c8539e4a8973ee3f5c` |

Mock проверяет структуру и поведение. В Codex платных операций и расходов **0**. Инженерная оценка Disabled и Low, подтверждение контракта DeepSeek и независимый WSL-прогон выполняются владельцем. Изменения ограничены `experiments/ds-dx-02/`. Сайт использован только для проверки закреплённого Git-дерева. [Точный diff реализации от R3](https://github.com/UkWood/ds-cosult/compare/27e27559197fa17a6630e2585f13f986d08cfeae...a1dd50de04bad2ab412d3e9acf253e4b5371b912)

## Матрица и потолки R4-A

| Порядок | Материал | Токены / пиковый резерв за операцию |
|---|---|---|
| A-D → A-L | 71 строка карточки Astro `A-c5c7146d49ed3f59` | 8192 / $0.3098304 каждый |
| upload → P-D → P-L | 8 страниц обзора `P-42f2fcb6f7dfdfa3`, один новый `file_id` | $0.0018 upload, 8192 / $0.3098304 каждый чат |
| V-D → V-L | Рисунок 3, физическая стр. 11 основного руководства `P-6f65a717b55eec7c`, inline PNG | 4096 / $0.3049152 каждый |

Визуальный выбор проверен локальным просмотром. Верхний и нижний кропы содержат читаемые разъёмы и цепи. Их SHA-256, размеры и координаты зафиксированы в `r4-a-plan.json`. Рендеры UK-PC могут отличаться побайтно от Linux-рендеров Codex. Перед GO проверяются локальные файлы и запечатываются их пины. V использует другой набор, поэтому сравнение с High R3 только историческое. A/P сопоставимы по исходному материалу и имеют отличия в промпте и runtime. Одинаковая вторая подача может получить больше cache hit. Сравнивайте usage и тарификацию отдельно от режима. Один ответ на режим даёт разведочный результат.

Сумма резервов $1.850952, первый резерв $0.3098304. Продолжение проверяет доступный остаток перед каждой операцией. В финансовом основании удерживаются R2 $0.005267700, R3 SETTLED $0.156373932 и R3 reserve $0.304915200, всего минимум **$0.466556832**. Исходные потолки дают остатки не выше $1.533443168 COMPILE и $4.533443168 всего. Предложение для отдельного Owner GO — $0.50 на R4-A и общий остаточный потолок $4.53. При таком лимите возможен PARTIAL/DEFERRED_BUDGET до шестой генерации. Сверьте биллинг и все прошлые расходы, не списывая удержанный резерв по часовому CSV.

## UK-PC · бесплатная независимая проверка и подготовка

Запустите в WSL. Команды используют прежние `site`, `venv` и `source-*` без скачивания материалов. `UTKC_HOME` можно заменить абсолютным путём к вашей среде. Существующие журналы и отчёты остаются на месте.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach a1dd50de04bad2ab412d3e9acf253e4b5371b912
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = a1dd50de04bad2ab412d3e9acf253e4b5371b912
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-r4"
  (cd "$UTKC_HOME/preflight-r4" && sha256sum -c DS-DX-02-D-preflight.zip.sha256 \
    mock-package-{1,2,3}.zip.sha256 r4-a-mock.zip.sha256)
  "$DX02_PYTHON" r4_a.py prepare --workspace "$UTKC_HOME"
)
```

В `r4-a-plan/manifest-draft.json` проверьте snapshot и шесть задач. Скопируйте `draft-card.json` в `reviewed-card.json` рядом. Сверьте текстовые выдержки с точными строками и страницами, уточните ожидаемые утверждения, категории и критерии. Просмотрите два PNG в `source-pilot/raw-illustrations`. Для V заполните `expected`, сужайте `region` до читаемого участка и разделяйте независимые утверждения по уникальным `id`. Задайте новую `revision` без префикса `draft`. Оценочная карта остаётся локальной и не подставляется в запросы.

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
"$DX02_PYTHON" r4_a.py freeze --workspace "$UTKC_HOME" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" --reviewer "${R4_REVIEWER:?}"
```

Заморозка сверяет preflight, исходный снимок, runtime, матрицу, карту и старые ledger по путям `private-state/ledger.json` и `private-r3/ledger.json`. Если на машине журналы расположены иначе, укажите утверждённое рабочее дерево с этими путями к оригиналам до запуска и проверьте напечатанные хеши. Сохраните напечатанный SHA frozen manifest в решении владельца. Новый state эксперимента — `private-r4-a`.

## Отдельный LIVE R4-A после Owner GO

Проверьте текущий DeepSeek Files/Vision, модель и тарифы перед подтверждением контракта. Установите утверждённые значения `R4_OWNER_GO`, `R4_COMPILE_USD` и `R4_TOTAL_USD`. Ключ вводится только через скрытое приглашение в интерактивной WSL2.

```bash
"$DX02_PYTHON" r4_a.py live --workspace "$UTKC_HOME" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" --owner-go "${R4_OWNER_GO:?}" \
  --owner-go-usd "${R4_COMPILE_USD:?}" --total-go-usd "${R4_TOTAL_USD:?}" \
  --confirm-provider-contract
```

При PARTIAL CLI возвращает ненулевой код и оставляет `reports-r4-a/r4-a-summary.zip`. Повторная отправка, разбиения, fusion и CONSULT в R4-A отсутствуют. Проверьте контрольную сумму ZIP. В `private-r4-a/engineering/r4-a-engineering.zip` находятся Markdown, принятые факты и шаблон оценки. Скопируйте `review-template.json` в `reviewed-results.json`. Для каждой полученной генерации заполните совпавшие обязательные ID, неподтверждённые утверждения, критические пропуски, сохранение условий и единиц. Для V укажите ложные визуальные срабатывания. Индивидуальные billing amounts указывайте только при независимом подтверждении, иначе оставьте `null`. Сопоставьте итог с usage, reasoning, latency, cache hit и пиковым ledger.

```bash
(cd "$UTKC_HOME/reports-r4-a" && sha256sum -c r4-a-summary.zip.sha256)
"$DX02_PYTHON" r4_a.py score --workspace "$UTKC_HOME" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" \
  --review "$UTKC_HOME/private-r4-a/engineering/reviewed-results.json"
```

Инженерная команда выбирает политику R4-B отдельным решением. Полный COMPILE требует `private-r4-b`, штатный свежий preflight, утверждение с `owner_go`, SHA файла `private-r4-a/engineering/score.json` и allowlist `modes` для `extract`, `vision_photo`, `vision_document`, `fusion`. Выбор блокируется без отчёта R4-A. Остатки для полного прохода рассчитываются с учётом R4-A. Критические ошибки и пропуски оцениваются до сравнения цен. Если обе альтернативы неудовлетворительны, передайте результаты Architecture Session A для решения.

## Read-only сверка и границы восстановления

```bash
"$DX02_PYTHON" reconcile.py --ledger "$UTKC_HOME/private-r3/ledger.json" \
  --knowledge-zip "$UTKC_HOME/compile-r3-v1/knowledge.zip" \
  --output "$UTKC_HOME/reconcile-r3.json"
"$DX02_PYTHON" reconcile.py --ledger "$UTKC_HOME/private-r4-a/ledger.json" \
  --output "$UTKC_HOME/reconcile-r4-a.json"
```

Для сравнения часовых агрегатов добавьте `--csv` с локально нормализованными колонками `time,model,usage_type,quantity,cost_usd`. Используйте ISO 8601 с часовым поясом, типы `prompt_hit,prompt_miss,completion,reasoning,ocr,request` и исходные суммы без двойного учёта reasoning. Сверка проверяет доступные checkpoints и контрольные суммы. Агрегаты CSV оставляют UNKNOWN и резерв в силе.

Аудируемая приватная реконструкция поддерживает `--approval` и `--independent-evidence`. В approval задаются `operation`, `stage`, `owner_go`, `disposition` и `evidence_sha256`. Независимое доказательство должно связывать точный `request_sha256` с хешем сохранённого ответа для `verified_response` или с подтверждённым провайдером исходом `provider_confirmed_no_charge`. Для upload также нужны исходные размер и страницы. Выход содержит отдельную запись решения или восстановленный result и стоимость. Исходный ledger и его блокировка сохраняются. Для R3 достоверная индивидуальная сверка пока недоступна.

Подтверждённое инженером разрешение локальной неопределённости можно связать с утверждением через `--verified-links` при проверке KnowledgeBase. JSON содержит `knowledge_identity`, `reviewer`, `links` с `unresolved`, `assertion`, `applicability_verified: true` и `evidence`. Отчёт фиксирует связь и SHA аттестации. Исходная запись остаётся в KnowledgeBase.
