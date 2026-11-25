# HANDOFF Architecture Session A — DS-DX-02 CONSULT-02-R1

Ветка `experiment/ds-dx-02-d-unified-knowledge-compiler` · реализация `78fc12ba49d03a276eabf297b9c28d0b42fcde48` · runtime SHA-256 `c8c72f64fe98c07e8d86c3992a62ef4bce522108bedee30a992365cb872fa48d`.

База R1 — `88e61096296729fe217c92889210f0ddb8f7df3d`. Исходная KnowledgeBase R4-B, вопросы, контрольная карта, история запросов, планы и ledger сохранены. Ранжирование selector не менялось. [HANDOFF CONSULT-02](https://github.com/UkWood/ds-cosult/blob/a70cd7c3580f35ffe959cd5fb3e1bbe981014e96/experiments/ds-dx-02/HANDOFF.md)

## Нормативы и размер запроса

CONSULT-02-R1 отправляет `max_tokens=5000`, Thinking Disabled и Streaming SSE с usage. В системный промпт добавлено дословное указание отвечать по существу, выбирая объём по сложности вопроса и сохраняя технически значимые условия, ограничения, меры безопасности и ссылки. Инструкция «Не выдумывай недостающие технические характеристики» сохранена. Исторический CONSULT-01 остаётся отдельной базой сравнения.

Локальный предел — размер компактного JSON в UTF-8. Ни один из профилей не даёт гарантии 50 000 входных токенов до отправки. Совместимый подтверждённый токенизатор в этом этапе не внедрён. LIVE проверяет фактический `prompt_tokens` после получения usage. При превышении 50 000 стоимость учитывается и дальнейшая серия прекращается. Output свыше 5 000 нарушает проверку usage и удерживает резерв.

Резерв по штатной консервативной формуле — **$0.306 за запрос**, до **$3.672** для 12 запросов. Профиль JSON и норматив входа не снижают расчётный резерв. Исторические расходы и удержанные UNKNOWN учитываются по ledger. Новый бюджет требует отдельного Owner GO. Один платный POST на вопрос максимум, автоматических повторов нет. Heartbeat WSL примерно каждые 15 секунд.

## Бесплатный Selector Context Sweep

| Профиль | Предел компактного JSON |
|---|---:|
| A | 9 000 байт |
| B | 32 000 байт |
| C | 64 000 байт |
| D | 96 000 байт |
| E | 128 000 байт |

В каждом профиле проверяются 12 вопросов. `cases.json` содержит покрытие и конкретные пропуски групп, выбранные ID, число неопределённостей и критических записей, размеры запроса, локальные остановки и сохранность применимых мер безопасности. Q11 отдельно проверяется с фактическим ответом Q10 из CONSULT-01, который используется только как ограниченный контекст диалога. Контрольная карта читается только проверяющим CLI.

В `summary.json` указан первый достаточный профиль из испытанных для каждого вопроса и отдельно для всей серии. Для серии проверяются все 54 группы, обе истории Q11, локальные пределы, сохранность обязательных сведений и специальные проверки Q02, Q08 и Q12. Профили могут давать разные выборки. План LIVE записывается только при прохождении всей серии и закрепляет прошедший минимальный профиль. При FAIL ZIP сохраняет измеренные пропуски без плана LIVE.

**52 PASS, 0 FAIL, 0 SKIP** в Codex на трёх прежних SourceArchive, seccomp socket EPERM. 0 платных операций. Приватные данные UK-PC в Codex недоступны, поэтому фактическое покрытие 54/54 и минимальный достаточный профиль ещё не измерены. Фактического usage v2 в бесплатной приёмке нет.

| ZIP preflight | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `e5b03465fa10ae91d3f2d5d5636cf9dc7746e54de42f1c6da329f6bb3df4a9ec` |

## Один бесплатный блок WSL для UK-PC

Блок использует старые venv, три SourceArchive, KnowledgeBase, архив CONSULT-01 и исторические ledger. Он экспортирует измеренный ZIP при PASS и при FAIL, если проверка смогла собрать отчёт. Каталоги R1 отдельные.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach 78fc12ba49d03a276eabf297b9c28d0b42fcde48
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = 78fc12ba49d03a276eabf297b9c28d0b42fcde48
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-consult02-r1"
  (cd "$UTKC_HOME/preflight-consult02-r1" && sha256sum -c ./*.zip.sha256)
  result=0
  "$DX02_PYTHON" consult02_check.py --workspace "$UTKC_HOME" \
    --preflight "$UTKC_HOME/preflight-consult02-r1/preflight.json" || result=$?
  src="$UTKC_HOME/consult02-r1-offline"
  test -f "$src/consult02-context-sweep.zip" || exit 1
  (cd "$src" && sha256sum -c consult02-context-sweep.zip.sha256)
  target=/mnt/c/DS-Validation/Reports/DS-DX-02-CONSULT-02-R1
  mkdir -p "$target"
  cp -n "$src"/consult02-context-sweep.zip{,.sha256} "$target/"
  (cd "$target" && sha256sum -c "$src/consult02-context-sweep.zip.sha256")
  exit "$result"
)
```

## LIVE только после отдельного Owner GO

Используйте SHA `consult02-r1-offline/plan.json`, напечатанный при PASS. Launcher сверяет выбранный профиль по ZIP, SHA плана и исторические ledger до ввода ключа. Если обнаружен ledger предыдущего CONSULT-02, требуется отдельная финансовая сверка его экспозиции. Все новые операции пишутся в `private-consult-02-r1`, отчёты — в `reports-consult-02-r1`.

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
"$DX02_PYTHON" consult02.py --workspace "$UTKC_HOME" \
  --preflight "$UTKC_HOME/preflight-consult02-r1/preflight.json" \
  --plan-sha256 "${CONSULT02_R1_PLAN_SHA:?}" --owner-go "${CONSULT02_R1_OWNER_GO:?}" \
  --owner-go-usd "${CONSULT02_R1_GO_USD:?}" --total-go-usd "${CONSULT02_R1_TOTAL_USD:?}" \
  --allow-partial --confirm-provider-contract
```
