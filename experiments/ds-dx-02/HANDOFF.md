# HANDOFF Architecture Session A — DS-DX-02 CONSULT-02-R2

Ветка `experiment/ds-dx-02-d-unified-knowledge-compiler` · immutable implementation `ecde5b407703122b3ee977d89884b2d26a99e90d` · runtime SHA-256 `b7341deccd4df14167a9d4956a38bd4bdfea03ac594be9be3443c94f8e390e19`.

Базовая реализация — `78fc12ba49d03a276eabf297b9c28d0b42fcde48`. [HANDOFF CONSULT-02-R1](https://github.com/UkWood/ds-cosult/blob/4d3de2e4ec169c9b33fc5c1860c5dc8b3695e620/experiments/ds-dx-02/HANDOFF.md)

## Изменения

- Диапазоны раскрываются для однотипных технических обозначений с совпадающими нормализованными префиксами. Обрабатываются пробелы, ASCII и Unicode-дефисы, кириллические и латинские варианты. Раскрывается не больше 16 позиций. Числовые интервалы, префиксы единиц измерения и несовместимые обозначения не раскрываются. Промежуточные обозначения участвуют в поиске и проверке области конфликта. Отчёт содержит обозначение, ID записей и локаторы силового и сигнального указаний. Это основание для локальной остановки и проверки у изготовителя.
- Для открытых обзоров возможностей selector добавляет до шести кандидатов из прямых деклараций по подходящим категориям. Приоритет задан для подготовленной карточки сущности. Например, защищённые сетевые функции могут попасть в обзор связи без общих лексических токенов. Дополнения подчиняются тому же JSON-пределу и идут после обязательных ограничений безопасности. Узкие процедурные вопросы сохраняют обычный путь поиска.
- Оригинальная KnowledgeBase, контрольная карта, 12 вопросов, исторические результаты и ledger остаются неизменными. Действуют Token Policy v2 **50 000/5 000**, прежний системный промпт, Thinking Disabled, Streaming SSE с usage, отключённые native tools и один POST на вопрос максимум. Консервативный резерв — **306 000 000 nd**. Размер компактного JSON остаётся приближённым ограничителем, проверка токенов выполняется по usage провайдера.

## Бесплатная проверка

**56 PASS, 0 FAIL, 0 SKIP** на трёх прежних SourceArchive с seccomp socket EPERM. Закрытые данные владельца не входили в облачный прогон. Платных вызовов и повторной компиляции — 0. Покрытие R2 будет измерено только на UK-PC.

| Профиль | Предел JSON | R1, по данным UK-PC | R2 |
|---|---:|---:|---|
| A | 9 000 | 23/54 | ожидает замера |
| B | 32 000 | 42/54 | ожидает замера |
| C | 64 000 | 44/54 | ожидает замера |
| D | 96 000 | 48/54 | ожидает замера |
| E | 128 000 | 53/54 | ожидает замера |

R1 завершился FAIL по всем профилям, Q11 с фактической историей достиг 3/3 в D/E. Проверяющий CLI сверяет архив R1 по SHA-256 `672aa6112c73c933867f482b6de871aad3f385dbf397b1f5e652b5adc239ec20`. В `r1-comparison.json` войдут дельты по профилям, восстановленные и новые пропуски, изменения локальных остановок и отдельное сравнение исторического Q11.

PASS R2 требует 54/54, обе истории Q11, Safety Gate Q02 и Q08 по известному конфликту, отсутствие дополнительных блокировок, abstention guard Q12, сохранность обязательных мер безопасности и соблюдение JSON-предела. Отчёт покажет минимальные достаточные профили по каждому вопросу и всей серии. При FAIL отчёт сохраняется, план LIVE не формируется.

| ZIP preflight | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `5d182d3ecbe44d2a0fe6b14f3ab9798e0bd7fae8cf21c60406d08930daa30db0` |

## Один бесплатный блок WSL на UK-PC

Сохраните архив R1 с его sidecar в прежнем `consult02-r1-offline`. Используются прежние venv, SourceArchive, KnowledgeBase и исторические данные. Блок экспортирует единый ZIP R2 при PASS или FAIL, если отчёт сформирован.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach ecde5b407703122b3ee977d89884b2d26a99e90d
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = ecde5b407703122b3ee977d89884b2d26a99e90d
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-consult02-r2"
  (cd "$UTKC_HOME/preflight-consult02-r2" && sha256sum -c ./*.zip.sha256)
  result=0
  "$DX02_PYTHON" consult02_check.py --workspace "$UTKC_HOME" \
    --preflight "$UTKC_HOME/preflight-consult02-r2/preflight.json" || result=$?
  src="$UTKC_HOME/consult02-r2-offline"
  test -f "$src/consult02-context-sweep.zip" || exit 1
  (cd "$src" && sha256sum -c consult02-context-sweep.zip.sha256)
  target=/mnt/c/DS-Validation/Reports/DS-DX-02-CONSULT-02-R2
  mkdir -p "$target"
  cp -n "$src"/consult02-context-sweep.zip{,.sha256} "$target/"
  (cd "$target" && sha256sum -c "$src/consult02-context-sweep.zip.sha256")
  exit "$result"
)
```

Sweep и будущий LIVE показывают heartbeat в stderr примерно каждые 15 секунд. При PASS отдельно выводится SHA `consult02-r2-offline/plan.json`. LIVE запускается владельцем после отдельного Owner GO, с этим SHA и `preflight-consult02-r2/preflight.json`, через `consult02.py` по интерфейсу R1. Для новых записей используются только `private-consult-02-r2` и `reports-consult-02-r2`. Любая ранее запущенная платная сессия CONSULT-02 требует сверки её финансовой экспозиции до подготовки нового плана.
