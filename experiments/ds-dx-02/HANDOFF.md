# HANDOFF Architecture Session A — DS-DX-02-D-R4-B-INT

25 ноября 2026 года · `UkWood/ds-cosult` · `experiment/ds-dx-02-d-unified-knowledge-compiler`

- Базовая реализация R4-C: `19e70a72d18b932e9119357749290d8bfa897016`
- Коммит реализации INT: `86acd589f99276f192eb06a80e5bf2f308697bc3`
- Runtime SHA-256: `da8e7bdf27c3fde1816b368d6d3035497166e9a545123f4e2372db5b0bf0d247`
- Saturn-Main-Site commit/tree: `084d759487bfab6e111549c9b5469711ac5fc13e` / `a5297822bf3a5e071b10cc1dca553481c1b84d47`

## Интеграция и основания

Полный COMPILE использует `thinking.type=disabled` для extract, vision_photo, vision_document и fusion. Каждый Chat Completions проходит через SSE с `stream=true` и `stream_options.include_usage=true`. Files API остаётся отдельным вызовом. Граф, SourceArchive, промпты, Fusion, формат KnowledgeBase и тракт CONSULT сохранены. При обрыве, отсутствии DONE либо ошибке usage операция остаётся UNKNOWN с удержанием резерва. Матрицы R4-A/R4-C и закрытые исходные материалы используются для проверки допуска.

Architecture Session A зафиксировала Disabled 68/72 и 0 критических пропусков, Low 18/72 и 7 критических пропусков, SSE 4/4 без новых UNKNOWN. Disabled для vision_photo и fusion остаётся предварительной инженерной политикой. Их качество проверяется на полной KnowledgeBase владельцем.

Бесплатная подготовка сверяет оба `score.json` с замороженной картой `R4-A-ENGINEERING-01`, идентичностью Owner GO, сводками экспериментов, завершёнными checkpoints и режимами запросов. Штатный оценщик пересчитывает оценки. Для R4-C дополнительно проверяется прежний замороженный план продолжения. SHA плана связывает Thinking, SSE, SHA обоих оценочных отчётов, карту, исходный снимок, runtime, preflight и финансовое основание. LIVE пересчитывает эти пины под финансовой блокировкой до запроса ключа. Замена файла после утверждения плана требует нового бесплатного расчёта и отдельного решения владельца.

## Бесплатная приёмка

**38 PASS, 0 FAIL, 0 SKIP.** Сохранены все 36 прежних тестов. Трёхпакетный mock пропустил результаты через SSE-ассемблер, проверил параметризацию всех четырёх семейств, повтор по checkpoints и совместимость готовой базы с CONSULT. Добавлены проверки остановки полного COMPILE при EOF и плохом usage, отсутствия и изменения каждого score, смены режима и изменения финансового пина. Использованы Linux и прежние три SourceArchive с seccomp `socket EPERM`. Проверки разрешения использовали синтетические локальные отчёты соответствующего формата. Фактические приватные артефакты владельца проверяются на UK-PC. Платные операции в Codex — **0**.

| Артефакт | SHA-256 |
|---|---|
| `DS-DX-02-D-preflight.zip` | `bdc658ae8ea25c91305f7cc06a39b9a03960d4d1d64d48bf3af511f039fcf54e` |
| `mock-package-1.zip` | `f9bd04f74fe746e2d6593eb88cfe329df29ca316ecdc3ec60cdaad129989cf32` |
| `mock-package-2.zip` | `d015250d25a8df30086c6b4355c909d49ed7d213e05adc080303a616485ddad9` |
| `mock-package-3.zip` | `3a0ea943d6c04b25917effe02da57109ce49b46a2df62801ad90c6591ddec08a` |
| `r4-a-mock.zip` | `61d46cfeb9b4c2832e91e9b5f5ebc1914010ef32e12e44476e6789ce23f98b4d` |

## Независимый бесплатный WSL-preflight и подготовка допуска

Команды используют прежний checkout, venv и SourceArchive. Приватные пути соответствуют предыдущим HANDOFF. Сохраните выведенный SHA плана в отдельном Owner GO.

```bash
export UTKC_HOME="$HOME/utkc-r2-acceptance"
(
  set -euo pipefail
  test -z "$(git -C "$UTKC_HOME/backend" status --porcelain)"
  git -C "$UTKC_HOME/backend" fetch origin experiment/ds-dx-02-d-unified-knowledge-compiler
  git -C "$UTKC_HOME/backend" switch --detach 86acd589f99276f192eb06a80e5bf2f308697bc3
  test "$(git -C "$UTKC_HOME/backend" rev-parse HEAD)" = 86acd589f99276f192eb06a80e5bf2f308697bc3
  test "$(git -C "$UTKC_HOME/site" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
  cd "$UTKC_HOME/backend/experiments/ds-dx-02"
  export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
  bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
    --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
    --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight-r4-b-int"
  (cd "$UTKC_HOME/preflight-r4-b-int" && sha256sum -c ./*.zip.sha256)
  "$DX02_PYTHON" compile_release.py --workspace "$UTKC_HOME" \
    --sources "$UTKC_HOME/source-pilot" --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" \
    --preflight "$UTKC_HOME/preflight-r4-b-int/preflight.json" \
    --output "$UTKC_HOME/r4-b-int-plan.json"
)
```

Финансовый пин вычисляется по локальным ledger и проверенным завершённым checkpoints. Контроль Architecture Session A — $0.212773848 расходов плюс $0.614745600 удержанных резервов. Контрольные остатки — $1.172480552 COMPILE и $4.172480552 всего. При расхождении представьте локальное основание владельцу до GO. Старые UNKNOWN сохраняются в прежних сессиях и учитываются в лимитах нового R4-B.

## Полный COMPILE пилота после отдельного Owner GO

Из утверждённого решения задайте `R4B_PLAN_SHA`, `R4B_OWNER_GO`, `R4B_COMPILE_USD` и `R4B_TOTAL_USD`. Ключ вводится скрыто в интерактивной WSL2. Перед запуском подтвердите действующий контракт провайдера.

```bash
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
bash compile-live.sh --sources "$UTKC_HOME/source-pilot" \
  --preflight "$UTKC_HOME/preflight-r4-b-int/preflight.json" \
  --card "$UTKC_HOME/r4-a-plan/reviewed-card.json" \
  --policy "$UTKC_HOME/r4-b-int-plan.json" --plan-sha256 "${R4B_PLAN_SHA:?}" \
  --state "$UTKC_HOME/private-r4-b" --knowledge "$UTKC_HOME/knowledge-r4-b-v1" \
  --reports "$UTKC_HOME/compile-r4-b-v1" --owner-go "${R4B_OWNER_GO:?}" \
  --owner-go-usd "${R4B_COMPILE_USD:?}" --total-go-usd "${R4B_TOTAL_USD:?}" \
  --confirm-provider-contract
```

При остановке по бюджету доступный результат остаётся частичным. Явный `--resume` с тем же SHA, Owner GO и state использует завершённые checkpoints. Выберите новые пути KnowledgeBase и отчётов. Увеличение требует действующей процедуры `--budget-approval` и соблюдения итоговых потолков из плана. UNKNOWN блокирует возобновление. Пиковые резервы последовательны, и имеющийся остаток не гарантирует прохождение всего графа.

## Экспорт и проверка

```bash
(cd "$UTKC_HOME/compile-r4-b-v1" && sha256sum -c knowledge.zip.sha256 DS-DX-02A-results.zip.sha256)
bash export.sh --zip "$UTKC_HOME/compile-r4-b-v1/knowledge.zip"
bash export.sh --knowledge "$UTKC_HOME/knowledge-r4-b-v1" --zip "$UTKC_HOME/portable-knowledge-r4-b-v1.zip"
"$DX02_PYTHON" reconcile.py --ledger "$UTKC_HOME/private-r4-b/ledger.json" \
  --knowledge-zip "$UTKC_HOME/compile-r4-b-v1/knowledge.zip" \
  --output "$UTKC_HOME/reconcile-r4-b-v1.json"
```

Инженерная приёмка проверяет полноту, происхождение, условия применимости, критические пробелы и качество vision_photo и fusion. Результаты mock подтверждают протокол. Реальные показатели полного COMPILE и пригодность KnowledgeBase подтверждаются после отдельного запуска владельца. [Предыдущий HANDOFF R4-C](https://github.com/UkWood/ds-cosult/blob/f19ffa9e8a8ca0b5de4a473b3e9cb64f4801e789/experiments/ds-dx-02/HANDOFF.md)
