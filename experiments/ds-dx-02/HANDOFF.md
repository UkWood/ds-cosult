# HANDOFF Architecture Session A — DS-DX-02-D-R2

24 ноября 2026 года. Ветка `experiment/ds-dx-02-d-unified-knowledge-compiler`.

| Поставка | Идентификатор |
|---|---|
| Исходный HEAD R2 | `8a027b5f34a2636bac07d83df63da4b2adb4ae03` |
| Коммит реализации | `ae56595183220c8d00405c4ded41026439faea53` |
| Коммит HANDOFF | `git log -1 --format=%H -- experiments/ds-dx-02/HANDOFF.md` из опубликованной ветки |
| Astro commit | `084d759487bfab6e111549c9b5469711ac5fc13e` |
| Astro tree | `a5297822bf3a5e071b10cc1dca553481c1b84d47` |

D-only. Облачная сессия выполнила подготовку источников и изолированную mock-приёмку. Платных операций 0. LIVE-COMPILE и LIVE-CONSULT ожидают раздельных решений владельца. Исходный сайт использован для чтения Git-объектов и скачивания исходных материалов.

## Изменения

- `astro.py` читает закреплённые Git-объекты, коллекции, front matter и маршруты. Обход ограничивает глубину и число узлов, фиксирует прямые и обратные ссылки, упоминания, принадлежность к группе, границы охвата и проверенные URL. Метаданные включают commit, tree, blob, SHA-256, путь и строки.
- `sources.py` принимает конфигурацию сущности, явный список материалов или автоматическое обнаружение. Проверяет сигнатуру, байты, хеши и число страниц. Сохраняет оригиналы, локаторы, метаданные и диагностику источников. Для PDF строит карту текстовых, растровых, табличных и векторных кандидатов, слабых текстовых слоёв, полных рендеров и кропов. При ограничении провайдерского файла сохраняет производные PDF с привязкой к физическим страницам оригинала.
- `planning.py` и `compile_d.py` заменяют фиксированный граф, страницы, иллюстрации, NEWEL и продуктовый промпт группами локаторов и валидируемыми планами. Ранние проходы чередуют карточку, PDF и изображения. Компилятор сохраняет digest запроса и стабильного префикса, usage, расходы, checkpoints и частичные записи. Ограниченные продолжения охватывают план, извлечение, vision и fusion. Fusion объединяет точные дубли с локаторами и сопоставляет записи разных источников по темам.
- `protocol.py` сохраняет прямой транспорт DeepSeek, seccomp и консервативный ledger. Resume сверяет идентичность запроса и checkpoints, а увеличение бюджета требует отдельной записи Owner GO с привязкой к плану. UNKNOWN удерживает резерв и блокирует последующие операции.
- `bundle.py`, `consult_d.py` экспортируют схему 2 с адаптивными темами и содержательным индексом, checksums и разрешёнными иллюстрациями. CONSULT читает только готовый комплект, использует ESSENCE или извлечения и удерживает помеченные критические условия и конфликты при выборе контекста. LIVE-CONSULT требует результат LIVE-COMPILE. Приёмка PARTIAL требует явного разрешения.
- `configs/pilot.json`, `configs/product.json`, `configs/system.json` содержат примеры пакетов. Вопросы пилота перенесены в `configs/pilot-questions.json`. `requirements.txt` закрепляет PyYAML. `preflight.py`, `test_d.py`, `test_universal.py` поддерживают бесплатное воспроизведение и проверку трёх пакетов. `HANDOFF.md` заменяет предыдущую инструкцию поставки.

Универсальный путь проходит от входной конфигурации через SourceArchive, план и checkpoints к KnowledgeBase. Комплект имеет собственный manifest, версию, покрытие, индекс фактов и ссылки на источники. Оригиналы, provider handles, ledger, секреты и приватные эталоны остаются вне KnowledgeBase. Приватное состояние и выходы CLI задаются отдельными путями.

## Пилот и дополнительные пакеты

Пилотная карточка `src/content/products/bkd-pk-rf-2.md` подтверждена по blob `86afcfe8be3be4e5022f0baf43143f64a2a9f7a0`. Из 438 записей Astro в пилот вошли 7 записей, 7 типизированных отношений и 24 диагностики границ. Подтверждены четыре PDF и две фотографии, обнаружено 196 визуальных кандидатов с учётом кропов. Устаревший URL помечен `EXCLUDED` по конфигурации владельца. Загрузка обзора получила HTTP 503 с первой попытки, повторное скачивание подтвердило исходный SHA-256.

| Пилотный источник | Страниц | Байт | SHA-256 |
|---|---:|---:|---|
| ЕСАН.426469.012РЭ, ред. 203-01 | 65 | 3024578 | `030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a` |
| Руководство по быстрому старту | 2 | 167325 | `bf07da30d1221f61a3ecdde5b40f542b90ca2a646c5dc6019997326a2c570148` |
| Обзор основных изменений | 8 | 392090 | `496ddc2786b8fb2cdfd8970947fadde6b7a045e7d86e20737f2ef694425d5890` |
| Работа с OPC UA | 5 | 230917 | `959f515c588ea8758cae0ccfdd17efaf396b31c84c4315e1b195c745d59db5db` |
| Фото 3112376640116232.jpg | | 73206 | `504f11f654a5b3b7466715e5a30ede6a38c149b7f5a3c909e8164b209481bf73` |
| Фото 3385755126930346.jpg | | 179920 | `b4912d21cea0b83974b5afe04d4067e66ee0392436117466c3daa994e95a017a` |

| Пакет | Структура подготовленного снимка | Mock |
|---|---|---|
| БКД-ПК-RF.2 | 14 источников в реестре, 4 PDF на 80 страниц, 2 фото, 92 группы | `PARTIAL` после инъекций усечения, 167 записей, 4 эмулированных upload |
| ARCHTOOL | Карточка программы, 11 Astro-записей, 6 PDF на 173 страницы с учётом связанных материалов, 13 изображений, 202 группы. Часть PDF разделена на производные диапазоны по настройке пакета | `PARTIAL` из-за `DEFERRED` ZIP с программой, 350 записей, 12 эмулированных upload |
| Контроль затопления | 10 Astro-записей, включая обратные связи от ИУ, Э1, Э2 и ЭРУ-1, PDF на 17 страниц, 19 изображений, 107 групп | `COMPLETE_UNREVIEWED`, 139 записей, 1 эмулированный upload |

Отпечатки SourceArchive для повторного сравнения результатов подготовки в этой сессии

| Пакет | SHA-256 snapshot |
|---|---|
| Пилот | `8d4a7f59a4b115a00d0aa50c93ce320e0ff361cbb756f699724efedc76119887` |
| ARCHTOOL | `8cac12819a89884eb858642e9c3b0375ed5ae8f74853c1fc91319ad1408f5173` |
| Контроль затопления | `0e0eb7d1ce828d81596458d464230ee33aa0996da6cfa152ba48024576f695de` |

Mock проверяет протокол, воспроизводимость и границы данных. Выходы содержат синтетические наблюдения. Статус `COMPLETE_UNREVIEWED` подтверждает выполнение структурного прохода. Экспертная семантическая проверка фактов, графики, полноты и ответов остаётся за LIVE-проверками владельца. Нарезка PDF использует локальные оценки и границы. При отказе провайдера размер его OCR-контекста и фактический cache hit требуют собственной диагностики. Эвристики обнаружения вектора и кропов допускают пропуски и ложных кандидатов.

## Бесплатная приёмка

Чистый checkout, Python 3.12.14, PyYAML 6.0.3, Poppler 26.05.0, Linux с libseccomp2. **21 тест PASS, 0 FAIL, 0 SKIP**, включая 14 адаптированных проверок D. Сокет в preflight и дочернем тесте отклонён с EPERM. Mock-запуски прошли с одинаковым runtime digest `4e13d7e114531279713dada6f22221f2340ac9eab011dcd799febbd214d5eed1`. Контрольная сумма ZIP preflight `f51bc770f1162bd1842b0a4a8146b6fca6bb369a5746ddf0cf37ff2c368c2239`.

| Проверка | Статус и доказательство |
|---|---|
| U01 | PASS · скан общего runtime и промптов |
| U02 | PASS · ARCHTOOL прошёл discovery → plan → compile → ZIP → CONSULT |
| U03 | PASS · та же цепочка для системы «Контроль затопления» |
| U04 | PASS · реальные route/blob и отношения; fixture для вложенного slug, обратной ссылки и цикла |
| U05 | PASS · проверка пинов четырёх PDF пилота, отдельная диагностика отсутствующего, повреждённого и неподходящего по пину материала, сохранение вручную подключённого PDF |
| U06 | PASS · различающиеся графы; проверены отказ при неверном локаторе, цикле, пропуске и превышении лимита |
| U07 | PASS mock · стабильный префикс, отдельный суффикс, учёт usage, запросы к ограниченным группам и 12 раздельных файлов из 6 PDF ARCHTOOL |
| U08 | PASS структурный · локальные кандидаты, inline vision, кропы, происхождение и переносимые изображения |
| U09 | PASS mock · инъекции length для планировщика, извлечения, vision и fusion, сохранение валидных префиксных записей, дочерние задачи, повтор с нулём вызовов |
| U10 | PASS mock · дедупликация с несколькими локаторами, раздельные условия, конфликт unresolved и отклонение невалидного локатора |
| U11 | PASS · PARTIAL у усечённого пилота и ARCHTOOL с видимой причиной, покрытие и UNREVIEWED |
| U12 | PASS · динамические темы, обязательные файлы, проверки ZIP, внешнего SHA, traversal, индекса и фильтра запрещённого содержимого |
| U13 | PASS mock · SourceArchive тестового запуска удалён перед CONSULT, маркер и provider handles отсутствуют в wire payload; при выборе темы критическая запись сохранена |
| U14 | PASS mock · резерв и учёт usage, журнал разрешений, отклонение несанкционированного увеличения и блокировка при UNKNOWN |
| U15 | PASS mock · lock, сверка digest, replay без повторных вызовов, новый выпуск с прежней идентичностью содержимого |
| U16 | PASS облачный preflight · socket EPERM, 0 платных операций, cloud LIVE rejected, чистый checkout и сверка удалённых refs |
| Независимый preflight WSL владельца | NOT RUN в этой сессии |
| LIVE-COMPILE, LIVE-CONSULT и инженерная приёмка | NOT RUN, требуются отдельные решения владельца |

Защищённые refs сверены чтением. `main` сохранил `9eccfecd732da4a489ad625f0214865d29504249`, DS-DX-01 сохранила `a6770b60c95caece619bc0f3c4d9c75e6e7c8103`. PR № 4 сохранил статус draft и HEAD `846dc9572bb11975a1f77453e0a8faa0f3100ded`. Изменения ограничены `experiments/ds-dx-02/`. Обновлена существующая ветка R2. PR, merge и deploy отсутствуют.

## Независимый бесплатный preflight WSL

В WSL2 владельца нужны Git, Poppler, libseccomp2 и uv. На UK-PC ожидаются Ubuntu 20.04, Python 3.12.16 и Poppler 0.86.1. Команды используют отдельную среду uv и сохраняют системный Python.

```bash
export UTKC_HOME="$PWD/utkc-r2-acceptance"
mkdir -p "$UTKC_HOME"
git clone --single-branch -b experiment/ds-dx-02-d-unified-knowledge-compiler \
  https://github.com/UkWood/ds-cosult.git "$UTKC_HOME/backend"
git init "$UTKC_HOME/site"
git -C "$UTKC_HOME/site" fetch --depth 1 \
  https://github.com/UkWood/Saturn-Main-Site.git 084d759487bfab6e111549c9b5469711ac5fc13e
git -C "$UTKC_HOME/site" switch --detach FETCH_HEAD
cd "$UTKC_HOME/backend/experiments/ds-dx-02"
uv python install 3.12.16
uv venv --python 3.12.16 "$UTKC_HOME/venv"
uv pip install --python "$UTKC_HOME/venv/bin/python" -r requirements.txt
export DX02_PYTHON="$UTKC_HOME/venv/bin/python" PYTHONDONTWRITEBYTECODE=1
"$DX02_PYTHON" --version
pdftoppm -v

# Онлайн разрешён исключительно для подготовки источников.
for package in pilot product system; do
  bash prepare.sh --config "$PWD/configs/$package.json" --site "$UTKC_HOME/site" \
    --sources "$UTKC_HOME/source-$package" --online
done

# Дальнейшая приёмка запрещает создание сокетов.
bash preflight.sh --sources "$UTKC_HOME/source-pilot" \
  --additional-source "$UTKC_HOME/source-product" --additional-source "$UTKC_HOME/source-system" \
  --site "$UTKC_HOME/site" --reports "$UTKC_HOME/preflight"
(cd "$UTKC_HOME/preflight" && sha256sum -c DS-DX-02-D-preflight.zip.sha256)
git status --porcelain
```

`source-manifest.json` показывает состояние каждого материала и подтверждённые байты. Сверьте четыре PDF и две фотографии пилота с таблицей. Успешный тест моков совместим с частичной доступностью материалов. При временном сбое подготовьте новый каталог из тех же пинов. Вход `materials[].file` принимает локальную копию с теми же SHA-256 и числом страниц. При изменении байтов согласуется новый пин. Рендеры и отпечатки WSL проверяются на месте, так как версия Poppler отличается.

## Provider, резерв и решения LIVE

Проверены публичные спецификации `deepseek-flash` (V4.1-Flash-1017), прямой endpoint `api.deepseek.com`, контекст 1M, максимум выхода 384K, Files multipart и ссылки `file_id`, inline vision и метрики usage. Компилятор использует Files purpose `text_recognition` и подаёт инженерную графику отдельными inline изображениями. Владелец может удалить файл штатным DELETE или дождаться выбранного TTL 604800 секунд. CLI повторно сверяет TTL перед использованием, загрузку после истечения не повторяет. Перед LIVE владелец подтверждает текущий контракт и цены флагом `--confirm-provider-contract`. [Модель и тарифы](https://api-docs.deepseek.com/quick_start/pricing/) · [Files API](https://api-docs.deepseek.com/guides/files_api/) · [Парсинг](https://api-docs.deepseek.com/guides/document_parsing/) · [Vision](https://api-docs.deepseek.com/guides/vision/) · [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)

| Величина | Расчёт |
|---|---:|
| Резерв одного чата | `$0.3000000 + max_tokens × $0.0000012` |
| Планировщик / извлечение с максимумом 8192 | $0.3098304 |
| Разбор четырёх пилотных PDF | `80 × $0.000225 = $0.018` |
| Верхняя граница графа COMPILE при потолке 2048 чатов | `2048 × $0.3098304 + $0.018 = $634.5506592` |
| Резерв одного вопроса CONSULT с максимумом 4096 | $0.3049152 |
| Верхняя граница серии из 18 вопросов | `18 × $0.3049152 = $5.4884736` |
| Платные расходы этой сессии | $0 |

Графовая граница учитывает максимум, заданный в runtime, при полном cache miss. В ledger фактическое списание использует $0.006 за 1M cache hit, $0.30 за 1M miss и $1.20 за 1M output. Reasoning учитывается внутри completion. Перед каждым POST применяются одновременно лимит этапа и общий лимит. При неопределённом исходе резерв удерживается до независимого выяснения. При остановке по лимиту CLI сохраняет PARTIAL и диагностику; новый выпуск получает отдельный каталог. Ориентиры из R2 ($2 COMPILE и до $3 CONSULT) требуют отдельного решения. При таких суммах полный проход по верхней оценке не гарантирован.

### LIVE-COMPILE после GO владельца

```bash
bash compile-live.sh --sources "$UTKC_HOME/source-pilot" --preflight "$UTKC_HOME/preflight/preflight.json" \
  --state "$UTKC_HOME/private-state" --knowledge "$UTKC_HOME/knowledge-v1" \
  --reports "$UTKC_HOME/compile-v1" --owner-go-usd "${COMPILE_GO_USD:?}" \
  --total-go-usd "${TOTAL_GO_USD:?}" --confirm-provider-contract
```

Ключ вводится скрыто в интерактивном WSL2. Установите числовые лимиты только из решения владельца. При возобновлении с прежними лимитами используйте `--resume`, тот же state и свежие пути KnowledgeBase и отчёта.

### Возобновление после дополнительного Owner GO

Сохраните согласование отдельно от Git. `identity` берётся из вывода `Compile plan identity`. `old_cap`, `new_cap`, `old_total` и `new_total` задаются целыми нанодолларами (1 USD = 1 000 000 000 nd). `owner_go` должен однозначно указывать на решение владельца. Следующая команда использует согласованные значения из окружения.

```bash
"$DX02_PYTHON" - "$UTKC_HOME/compile-amendment.json" <<'PY'
import json, os, sys
from pathlib import Path
fields = {name: int(os.environ[name.upper()])
          for name in ("old_cap", "new_cap", "old_total", "new_total")}
record = dict(fields, stage="compile", identity=os.environ["COMPILE_PLAN_ID"],
              owner_go=os.environ["OWNER_APPROVAL_ID"])
with Path(sys.argv[1]).open("x") as stream:
    json.dump(record, stream)
PY
bash compile-live.sh --sources "$UTKC_HOME/source-pilot" --preflight "$UTKC_HOME/preflight/preflight.json" \
  --state "$UTKC_HOME/private-state" --knowledge "$UTKC_HOME/knowledge-v2" \
  --reports "$UTKC_HOME/compile-v2" --owner-go-usd "${NEW_COMPILE_GO_USD:?}" \
  --total-go-usd "${NEW_TOTAL_GO_USD:?}" --confirm-provider-contract \
  --resume --budget-approval "$UTKC_HOME/compile-amendment.json"
```

### Экспорт и проверка KnowledgeBase

```bash
bash export.sh --zip "$UTKC_HOME/compile-v2/knowledge.zip"
(cd "$UTKC_HOME/compile-v2" && sha256sum -c knowledge.zip.sha256 DS-DX-02A-results.zip.sha256)
bash export.sh --knowledge "$UTKC_HOME/knowledge-v2" --zip "$UTKC_HOME/portable-knowledge.zip"
```

### LIVE-CONSULT после просмотра COMPILE и отдельного GO

До запуска зафиксируйте приватный эталон отдельно от модели и разберите покрытие и нерешённые конфликты. Используйте выбранный выпуск KnowledgeBase и тот же приватный state для общего финансового лимита.

```bash
bash consult-live.sh --knowledge "$UTKC_HOME/knowledge-v2" --state "$UTKC_HOME/private-state" \
  --reports "$UTKC_HOME/consult-v1" --questions "$PWD/configs/pilot-questions.json" \
  --owner-go-usd "${CONSULT_GO_USD:?}" --total-go-usd "${NEW_TOTAL_GO_USD:?}" \
  --confirm-provider-contract
(cd "$UTKC_HOME/consult-v1" && sha256sum -c DS-DX-02B-results.zip.sha256)
```

В ходе оценки сравниваются существенные факты, применимость, ограничения, противоречия, схемы и ответы с оригиналами и подготовленной базой. Отдельно фиксируются критические ошибки, неизвестные сведения, размер рабочего контекста и фактические usage/cache/cost. Перед следующим LIVE владелец изучает результат предыдущего. ZIP реальных результатов и эталоны остаются в приватной среде владельца.
