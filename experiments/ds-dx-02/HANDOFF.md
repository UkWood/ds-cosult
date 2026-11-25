# HANDOFF Architecture Session A — DS-DX-02-D-R4-C

25 ноября 2026 года · `UkWood/ds-cosult` · `experiment/ds-dx-02-d-unified-knowledge-compiler`

- База R4: `886ebc04708308658aa6e39f16ef7f79d78899cd`
- Коммит реализации R4-C: `19e70a72d18b932e9119357749290d8bfa897016`
- Runtime SHA-256: `59af04bab770d6da7970710633f030f6a8bd5453c1ce9aaefa8def4e87a70df7`
- Astro commit/tree: `084d759487bfab6e111549c9b5469711ac5fc13e` / `a5297822bf3a5e071b10cc1dca553481c1b84d47`

## Результат и границы

Независимый R4 WSL дал 32 PASS. По переданной инженерной оценке Astro Disabled прошёл 25/26 критериев, Astro Low — 15/26. R4-A остановился на P-D с `RemoteDisconnected` до HTTP-заголовков после 44,678 с. DNS, TCP и TLS прошли базовую диагностику. Почасовой CSV согласуется с подтверждёнными операциями. Индивидуальный исход P-D остаётся UNKNOWN.

R4-C отправляет Chat Completions с `stream: true` и `stream_options.include_usage: true`. Декодер принимает keep-alive комментарии, объединяет `delta.content`, считает байты `delta.reasoning_content`, проверяет последовательность `finish_reason`, финальный usage и `[DONE]`. Usage из завершающего чанка проходит прежние проверки затрат и токенов. Результат компиляции и формат KnowledgeBase сохраняются. Потоковый режим включён у матрицы R4-C. [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/) · [Keep-alive](https://api-docs.deepseek.com/quick_start/rate_limit/)

Сводка обрыва содержит стадию, размер, счётчики событий и признаки появления finish, usage и DONE. Сырые байты потока с reasoning остаются в приватном state. EOF без DONE, обрыв, некорректный SSE и ошибки usage удерживают резерв и останавливают матрицу. Потоковый режим позволяет принимать keep-alive после HTTP-заголовков. Его влияние на прежний обрыв до заголовков требует LIVE-проверки.

В Codex: **36 PASS, 0 FAIL, 0 SKIP**, полный seccomp-preflight с тремя прежними SourceArchive. Сценарии покрывают дробление SSE/UTF-8 между чтениями, HTTP headers disconnect, частичное чтение и timeout, некорректный JSON, отсутствующие DONE/usage, неверный usage, финансовую блокировку, повторное использование и замену PDF lease и неизменность исходного состояния R4-A. CLI smoke подтвердил бесплатный `prepare` и отказ облачного LIVE до создания state на синтетическом ledger. Платные операции и расходы — **0**. Изменения ограничены `experiments/ds-dx-02/`. [Точный diff](https://github.com/UkWood/ds-cosult/compare/886ebc04708308658aa6e39f16ef7f79d78899cd...19e70a72d18b932e9119357749290d8bfa897016)

| Артефакт бесплатной приёмки | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `66f173335537b4da5fc5a4479b7df9de3cb56ffbf07b2f1e9d18f8f758a9d94f` |
| `mock-package-1.zip` | `7ee84fca63d21567b761130f545a9a29d4eddaeb3a0d259af9f29768caf96ae2` |
| `mock-package-2.zip` | `2b2f340f4bbda14c2c69a2321ef8a60dee39b04bc66ff7304d8a466f27e3e8d0` |
| `mock-package-3.zip` | `e8386c92bc1faeb06db11aab83c9be3a4a89ec512e8bf66db37dcf99e2891846` |
| `r4-a-mock.zip` | `84e919a649a6b5ac01a3343eb74a8cbc35f35350394d48084ca84f7534deedf1` |

## Матрица продолжения

| Порядок | Вход из R4-A | Режим | Пиковый резерв |
|---|---|---|---:|
| P-D | Все 8 физических страниц обзора, текст + Files API | Disabled | $0.3098304 |
| P-L | Те же страницы и тот же `file_id` | Low | $0.3098304 |
| V-D | Стр. 11 основного руководства, прежние кропы рисунка 3 | Disabled | $0.3049152 |
| V-L | Тот же фрагмент и кропы | Low | $0.3049152 |

A-D и A-L уже оценены. R4-C сверяет старые frozen manifest, оценочную карту, хеши исходных checkpoints, запрос загрузки PDF и оригинальный digest P-D. Владельцу нужно отдельно утвердить новый сетевой вызов P-D в рамках этой матрицы и признать старый UNKNOWN. Старый ledger, checkpoints и score сохраняются. Два варианта PDF: прежний проверенный lease либо один новый upload по отдельному Owner GO. Срок lease проверяется локально. Удалённую доступность файла покажет запрос. Отказ останавливает матрицу без повторной отправки и переключения на другой файл.

Сумма резервов — **$1.2294912** при повторном использовании или **$1.2312912** с новой загрузкой. Первый резерв — **$0.3098304** для reuse или **$0.0018** для upload. Для разрешения upload стартовый лимит должен покрыть также первый чат. Резервы сверяются последовательно. Лимит ниже суммы пиковых резервов может привести к PARTIAL/DEFERRED_BUDGET.

До Owner GO сверяются исходные потолки $2 COMPILE / $5 всего, база R2–R3 не менее $0.466556832 и фактические SETTLED плюс удержанные резервы из R4-A, включая **$0.3098304** старого P-D. Точные остатки выводит `prepare` по локальным ledger. Уже начатый R4-B требует отдельного финансового решения. Последующий R4-B учитывает новый ledger R4-C, включая UNKNOWN.

## UK-PC · бесплатный preflight и план

Запустите в WSL на прежних `site`, `venv` и `source-*`. Укажите SHA исходного frozen manifest из решения R4-A. Код также сверяет его с прежним файлом Owner GO.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach 19e70a72d18b932e9119357749290d8bfa897016
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = 19e70a72d18b932e9119357749290d8bfa897016
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-r4-c"
  (cd "$UTKC_HOME/preflight-r4-c" && sha256sum -c ./*.zip.sha256)
)
```

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
"$DX02_PYTHON" r4_c.py prepare --workspace "$UTKC_HOME" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" \
  --frozen-sha256 "${R4A_FROZEN_SHA:?}" --file reuse
```

Если локальный lease истёк и владелец рассматривает новую загрузку, выполните ту же бесплатную команду с `--file upload`. Проверьте напечатанный план, финансовые остатки и его SHA. Сохраните в новом решении владельца SHA плана, режим PDF, допустимые лимиты и подтверждение удержания старого P-D.

## LIVE · только после нового Owner GO

Для `reuse` установите `R4C_PLAN_SHA`, `R4C_OWNER_GO`, `R4C_COMPILE_USD` и `R4C_TOTAL_USD` по утверждённому решению. Ключ вводится скрыто в интерактивной WSL2.

```bash
"$DX02_PYTHON" r4_c.py live --workspace "$UTKC_HOME" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" \
  --frozen-sha256 "${R4A_FROZEN_SHA:?}" --file reuse \
  --plan-sha256 "${R4C_PLAN_SHA:?}" --owner-go "${R4C_OWNER_GO:?}" \
  --owner-go-usd "${R4C_COMPILE_USD:?}" --total-go-usd "${R4C_TOTAL_USD:?}" \
  --acknowledge-prior-p-d-unknown --confirm-provider-contract
```

Для отдельно утверждённого upload замените `--file reuse` на `--file upload`, укажите SHA именно upload-плана и добавьте `--upload-owner-go "${R4C_UPLOAD_GO:?}"` с отдельным ID решения. Оба варианта используют одно новое одноразовое состояние `private-r4-c` и отдельный каталог `reports-r4-c`.

После запуска проверьте ZIP и при необходимости снимите read-only диагностику. Для инженерного сравнения заполните копию `private-r4-c/engineering/review-template.json` по прежней карте. Команда score пишет отдельную оценку R4-C.

```bash
(cd "$UTKC_HOME/reports-r4-c" && sha256sum -c r4-c-summary.zip.sha256)
"$DX02_PYTHON" reconcile.py --ledger "$UTKC_HOME/private-r4-c/ledger.json" \
  --output "$UTKC_HOME/reconcile-r4-c.json"
"$DX02_PYTHON" r4_c.py score --workspace "$UTKC_HOME" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" \
  --review "$UTKC_HOME/private-r4-c/engineering/reviewed-results.json"
```

Владелец сохраняет старую оценку Astro и сравнивает P/V отдельно по инженерным критериям, cache hit, usage и стоимости. Исторический R4 и процедура независимого доказательства исхода доступны в прежнем HANDOFF. [HANDOFF R4](https://github.com/UkWood/ds-cosult/blob/886ebc04708308658aa6e39f16ef7f79d78899cd/experiments/ds-dx-02/HANDOFF.md)
