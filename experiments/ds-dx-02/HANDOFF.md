# HANDOFF Architecture Session A — DS-DX-02 CONSULT-02

Ветка `experiment/ds-dx-02-d-unified-knowledge-compiler` · реализация `88e61096296729fe217c92889210f0ddb8f7df3d` · runtime SHA-256 `fba558071a8980cd9421f9341e2c8066f57305503daa7734b6373fe7be7ca2ed`.

База CONSULT-01 — `e2c6ff9379dd76cebd382e042f70151581bc0d03`. CONSULT-02 читает исходную KnowledgeBase R4-B. Исторические ответы, планы, checkpoints и ledger остаются на месте. [HANDOFF CONSULT-01](https://github.com/UkWood/ds-cosult/blob/f52e7bfa8721452c87195eabf08a900bbaeaefb5/experiments/ds-dx-02/HANDOFF.md)

## Selector, безопасность и ссылки

- Selector `selector-v2.1` использует подготовленные записи, IDF, нормализацию длины, бонусы точных обозначений и покрытие частей вопроса. Технические смешанные кириллические и латинские обозначения, дефисы и русские окончания нормализуются только при поиске. Исходные тексты, числовые значения, условия и редакции передаются без переписывания. Точные дубли объединяют ссылки. Предыдущий вопрос диалога участвует в поиске с меньшим весом. Ответ модели используется только как ограниченная история диалога.
- Safety policy сохраняет применимые предупреждения, включает связанные неопределённости и локально блокирует практический ответ при несовместимых указаниях о силовом и сигнальном назначении одного разъёма. Подтверждение запрашивается у изготовителя. Локальное ограничение помечается отдельно от ответа модели и не расходует резерв. Для предела измеряемого тока требуется подтверждённое значение. Напряжение, сопротивление или потребляемый ток сами по себе его не устанавливают.
- В запрос передаются метки и метаданные только выбранных источников. Отчёт раскрывает метки в названия, доступные исходные URL, физические страницы PDF или строки Astro. Неизвестная метка отмечается как неподтверждённая. Контрольная карта находится в `test_fixtures/`, читается независимым проверяющим CLI и не входит в selector, промпт, историю или запрос. 12 прежних вопросов сохранены побайтно. Thinking Disabled, SSE с usage, максимум ответа 4096, stderr heartbeat и явный итоговый статус сохраняются.
- Локальный предохранитель — **9000 байт полного компактного JSON** с запасом до лимита провайдера. Это приближение без совместимого подтверждённого токенизатора. Если обязательные сведения не помещаются, отправка блокируется. LIVE проверяет фактический usage. При входе свыше 10 000 токенов стоимость учитывается, следующие запросы прекращаются. Производственный потолок ответа 450 в этом эксперименте не проверяется.

## Бесплатная приёмка

**50 PASS, 0 FAIL, 0 SKIP** на трёх прежних SourceArchive с seccomp socket EPERM. Сохранены 43 теста CONSULT-01. Добавлены синтетические регрессии для обозначений, нескольких частей запроса, scoped safety, ссылок, длинной истории, недостатка свидетельств, подмены плана, финансового основания и остановки после превышения usage. Платные вызовы в Codex — **0**.

Исходная KnowledgeBase владельца и фактический ZIP CONSULT-01 доступны на UK-PC. Поэтому исторические 42/54, целевые **54/54**, проверка Q02/Q08 и Q12 на оригинале и локальный размер всех 12 запросов требуют независимого прогона. Успех синтетических тестов этих измерений не заменяет. При FAIL ZIP содержит пропущенные группы и причины; файл допуска LIVE создаётся только при PASS.

| ZIP preflight | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `0c45358a89fd7843b732c26e963b97deb3da8b56a85f2ee1d1ba76d392336df4` |

## Один бесплатный блок WSL для UK-PC

Используются прежний venv, три SourceArchive и неизменные `knowledge-r4-b-v1`, `compile-r4-b-v1/knowledge.zip`, `reports-consult-01/DS-DX-02B-results.zip` и приватные ledger. Блок выгружает отчёт даже при измеренном FAIL, когда сформирован ZIP.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach 88e61096296729fe217c92889210f0ddb8f7df3d
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = 88e61096296729fe217c92889210f0ddb8f7df3d
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-consult02"
  (cd "$UTKC_HOME/preflight-consult02" && sha256sum -c ./*.zip.sha256)
  result=0
  "$DX02_PYTHON" consult02_check.py --workspace "$UTKC_HOME" \
    --preflight "$UTKC_HOME/preflight-consult02/preflight.json" || result=$?
  src="$UTKC_HOME/consult02-offline"
  test -f "$src/consult02-dryrun.zip" || exit "$result"
  (cd "$src" && sha256sum -c consult02-dryrun.zip.sha256)
  target=/mnt/c/DS-Validation/Reports/DS-DX-02-CONSULT-02
  mkdir -p "$target"
  cp -n "$src"/consult02-dryrun.zip{,.sha256} "$target/"
  (cd "$target" && sha256sum -c "$src/consult02-dryrun.zip.sha256")
  exit "$result"
)
```

В `consult02-dryrun.zip` находятся сводка, сравнение фактических выборок CONSULT-01 и локальных v1/v2, группы карты, отдельный Q11 с исторической репликой Q10, метаданные выборок, финансовый пин и лог preflight. Историческая реплика применяется только в этой проверке. Нет новых model-generated ответов, измеренных latency или usage для v2. При PASS SHA локального `consult02-offline/plan.json` выводится отдельно для согласования.

## LIVE после отдельного Owner GO

Ожидаемая экспозиция по прежним журналам — $1.492266972, остаток первоначального потолка — $3.507733028. Более строгий контрольный остаток по решению CONSULT-01 — $3.496914560. Launcher вычисляет их заново и сохраняет UNKNOWN R3/R4-A в учёте. Резерв одного запроса — **$0.3049152**. Сумма резервов 12 запросов — **$3.6589824**. При установленных лимитах завершение серии зависит от последовательных списаний и локальных ограничений. Журналы CONSULT-02 и ответы записываются только в новые каталоги.

Заполните переменные из отдельного решения владельца. Ключ вводится в интерактивном WSL2 через скрытый запрос. Повтор запуска на занятом состоянии запрещён.

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
"$DX02_PYTHON" consult02.py --workspace "$UTKC_HOME" \
  --preflight "$UTKC_HOME/preflight-consult02/preflight.json" \
  --plan-sha256 "${CONSULT02_PLAN_SHA:?}" --owner-go "${CONSULT02_OWNER_GO:?}" \
  --owner-go-usd "${CONSULT02_GO_USD:?}" --total-go-usd "${CONSULT02_TOTAL_USD:?}" \
  --allow-partial --confirm-provider-contract
```

Проверка и локальный экспорт ZIP после LIVE, включая частичный отчёт при наличии:

```bash
(
  set -euo pipefail
  src="$UTKC_HOME/reports-consult-02"
  target=/mnt/c/DS-Validation/Reports/DS-DX-02-CONSULT-02
  (cd "$src" && sha256sum -c consult02-results.zip.sha256)
  mkdir -p "$target"
  cp -n "$src"/consult02-results.zip{,.sha256} "$target/"
  (cd "$target" && sha256sum -c "$src/consult02-results.zip.sha256")
)
```

Инженерная оценка отвечает отдельно за точность модели, безопасность, релевантность, критические условия и корректность ссылок. 54/54 измеряет нахождение записей по карте. Показатели локальных остановок остаются отдельными от модельных ответов.
