# HANDOFF Architecture Session A — DS-DX-02-R4-B-QA / CONSULT-01

Ветка `experiment/ds-dx-02-d-unified-knowledge-compiler` · реализация QA `e2c6ff9379dd76cebd382e042f70151581bc0d03` · runtime SHA-256 `1a9f9a2b2b6072dc15ed47c9967e5abab52128e5a7beeb477b6a35e1d93227df`.

База R4-B — `86acd589f99276f192eb06a80e5bf2f308697bc3`. Исходный снимок и результаты владельца читаются из прежних каталогов. [HANDOFF R4-B-INT](https://github.com/UkWood/ds-cosult/blob/b2d04355b946d5f13b4eb885112e098b7ec40857/experiments/ds-dx-02/HANDOFF.md)

## Что поставлено

- **QA-01.** Бесплатный replay под seccomp проверяет пины двух ZIP, плана, ledger, SourceArchive и 98 завершённых checkpoints. Восстанавливает порядок, request/prefix hashes и фактические области задач, включая основания Fusion. Для исторического file handle используется окно от времени завершения upload до сохранённого expiry, сверенное с исходным UTC начала каждого запроса. Сегодняшний TTL не влияет на replay. Реконструкция во временном каталоге сравнивает содержимое обоих ZIP с исходными и удаляется при выходе. Публикуется только отдельный review ZIP. Любое расхождение останавливает проверку.
- **Диагностика.** Review ZIP содержит безопасные исходные поля, порядковый номер, исходный первый код, дополнительные выявленные причины, допустимые локаторы, изображения и отдельное предложение только для однозначных преобразований. Сводка включает примеры, распределения и сравнение с переданными 327 первыми причинами, а также списки `unconfirmed_images`, `truncated` и `invalid_json`. Только фактический replay заполнит эти результаты. Предложения не меняют факты или исходную KnowledgeBase.
- **CONSULT-01.** Приложенные 12 вопросов сохранены побайтно, SHA-256 `aa083f7d102e583a3f49d347001dde2d4b3d0322696b01a9758876d3d8ec2c08`. Q10–Q11 образуют один диалог `serial`. Первый эксперимент отправляет текст из подготовленной базы и метаданные источников без inline-изображений, эталонных ответов, tools и raw fallback. Прежний selector остаётся с `CONTEXT_BYTES=240000`, `LIMIT=4096`. В системный текст для PARTIAL добавлено одно указание о статусе, инженерной непроверенности и существенных пробелах. SSE отправляет естественный текст с Thinking Disabled и итоговым usage. Q12 оценивается по источникам после ответа.
- **Прогресс.** COMPILE, CONSULT и QA replay пишут в stderr время UTC, текущую задачу, завершённые и известные задачи, учтённые нанодоллары и heartbeat примерно каждые 15 секунд. Heartbeat показывает работу процесса, а не получение данных. Терминальный статус содержит путь отчёта. Причина прежнего Ctrl+C не установлена.

**Бесплатная приёмка в Codex — 43 PASS, 0 FAIL, 0 SKIP.** Три прежних SourceArchive, socket EPERM, 0 платных операций. Тест replay с истёкшей арендой выполнен на синтетических checkpoints. Приватные артефакты владельца и фактические причины отклонений проверяются на UK-PC.

| ZIP preflight | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `171709d27cfb97be6d8626921dedd937195566d5203a0060448fcded53f7f750` |

## Один бесплатный WSL-блок

Запустите на UK-PC в прежней WSL-среде. Укажите фактическую папку `UTKC_HOME`, если она отличается от приведённой. QA ZIP содержит тексты для внутренней инженерной проверки. Храните экспорт в согласованном локальном каталоге. Новый пакет KnowledgeBase здесь не экспортируется.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach e2c6ff9379dd76cebd382e042f70151581bc0d03
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = e2c6ff9379dd76cebd382e042f70151581bc0d03
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-r4-b-qa"
  (cd "$UTKC_HOME/preflight-r4-b-qa" && sha256sum -c ./*.zip.sha256)
  "$DX02_PYTHON" qa_replay.py --workspace "$UTKC_HOME" \
    --output "$UTKC_HOME/qa-r4-b/qa-review.zip"
  "$DX02_PYTHON" consult_qa.py prepare --workspace "$UTKC_HOME" \
    --preflight "$UTKC_HOME/preflight-r4-b-qa/preflight.json"
  (cd "$UTKC_HOME/qa-r4-b" && sha256sum -c qa-review.zip.sha256 consult-dryrun.zip.sha256)
  output=/mnt/c/DS-Validation/Reports/DS-DX-02-R4-B-QA
  mkdir -p "$output"
  cp -n "$UTKC_HOME/preflight-r4-b-qa"/DS-DX-02-D-preflight.zip{,.sha256} \
    "$UTKC_HOME/qa-r4-b"/qa-review.zip{,.sha256} \
    "$UTKC_HOME/qa-r4-b"/consult-dryrun.zip{,.sha256} "$output/"
  (cd "$output" && sha256sum -c "$UTKC_HOME/preflight-r4-b-qa/DS-DX-02-D-preflight.zip.sha256" \
    "$UTKC_HOME/qa-r4-b/qa-review.zip.sha256" "$UTKC_HOME/qa-r4-b/consult-dryrun.zip.sha256")
)
```

В dry-run Q11 использует явно синтетический ответ Q10. ZIP содержит байты контекстного блока и запроса, виды и число выбранных записей, наличие критических записей и локаторов. Это проверка selector. Фактические usage и качество ответа измеряются в LIVE. Если критические записи не помещаются или не передаются, подготовка останавливается. Исходные счета R2, R3, R4-A, R4-C и R4-B проверяются и фиксируются в SHA плана. Удержанные резервы остаются в расчёте. Пиковый резерв первого вопроса **$0.3049152**, сумма резервов 12 вопросов **$3.6589824**. Это верхние оценки, а не утверждённый бюджет.

## Будущий LIVE-CONSULT после отдельного Owner GO

После просмотра QA ZIP и dry-run установите `CONSULT_PLAN_SHA`, `CONSULT_OWNER_GO`, `CONSULT_GO_USD` и `CONSULT_TOTAL_USD` из отдельного решения владельца. Launcher повторно сверяет план, исторические счета, архив, вопросы и runtime перед запросом ключа. При UNKNOWN матрица останавливается. Автоматических повторов нет.

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
bash consult-live.sh live --workspace "$UTKC_HOME" \
  --preflight "$UTKC_HOME/preflight-r4-b-qa/preflight.json" \
  --plan-sha256 "${CONSULT_PLAN_SHA:?}" --owner-go "${CONSULT_OWNER_GO:?}" \
  --owner-go-usd "${CONSULT_GO_USD:?}" --total-go-usd "${CONSULT_TOTAL_USD:?}" \
  --allow-partial --confirm-provider-contract
(cd "$UTKC_HOME/reports-consult-01" && sha256sum -c DS-DX-02B-results.zip.sha256)
```

Ответы UNREVIEWED. Сопоставьте их с `R4-A-ENGINEERING-01` и исходными материалами отдельно от измерений selector. Особое внимание уделите критическим условиям, исходным противоречиям, распиновке и реакции Q12 на неподтверждённый диапазон.
