# DS-DC-01 · Передача Architecture Session A

**Статус артефактов** · READY FOR INDEPENDENT ARCHITECTURE ACCEPTANCE REVIEW.

Поставка содержит изолированный Document-Centric RAG v0.2 и решения DS-PDF-01-R1. Реальный путь DeepSeek, платная валидация DC-02, публикация ответов и deployment требуют отдельных решений.

## База и связи между PR

- Репозиторий `UkWood/ds-cosult`, ветка `feat/ds-dc-01-document-centric-pilot`.
- Фактический исходный коммит `f138888d75214f627d1df212a47efc44195ebe70`, актуальный удалённый ref `codex/ds-pilot-01`, голова [PR #2](https://github.com/UkWood/ds-cosult/pull/2). Это прямая база поставки и целевая ветка сравнения для Draft PR.
- На момент проверки `main` указывает на `9eccfecd732da4a489ad625f0214865d29504249`. Сравнение с `main` включило бы изменения PR #2. [PR #3](https://github.com/UkWood/ds-cosult/pull/3) с головой `e102ab4425100a5806cff5b5df1383c17f5bf09c` — исторический контекст без зависимости сборки.
- Источники сайта закреплены на `084d759487bfab6e111549c9b5469711ac5fc13e`.

## Материалы приёмки

- Архитектура и приоритет решений: [v0.2](../architecture/DS-DC-ARCHITECTURE-V0.2.md), [тематическое разрешение](../architecture/A-DS-DC-02-TOPIC-DOSSIER-RESOLUTION.md), [облачная среда](../architecture/DS-DC-INFRA-01-CLOUD.md), [поправка к runtime](../architecture/DS-DC-01-RUNTIME-AMENDMENT.md), [решения DS-PDF-01-R1](../architecture/DS-PDF-01-R1.md).
- [Исходный отчёт DC-01](../reports/DS-DC-01-CLOUD-REPORT.md) фиксирует предыдущую политику обязательной полноты. [Отчёт R1](../reports/DS-PDF-01-R1-REPORT.md) фиксирует действующую политику и итог аудита.
- [Построчный аудит документации](../reports/DS-PDF-01-R1-INVENTORY.md), [список битых ссылок](../reports/DS-PDF-01-R1-BROKEN-LINKS.md).
- Машиночитаемые результаты: [тематический каталог](../reports/ds-dc-01/catalogue.json), [статистика каталога](../reports/ds-dc-01/inventory.json), [реестр досье](../reports/ds-dc-01/dossiers.json), [исходные сценарии](../reports/DS-DC-01-RESOLVER-CASES.json), [результаты resolver](../reports/ds-dc-01/resolver.json), [обезличенная форма mock-запроса](../reports/ds-dc-01/mock-wire-redacted.json).
- [Финальный локальный прогон и статус CI](../reports/DS-DC-01-FINAL-TESTS.md).

## Воспроизведение

Для локального прогона нужны Python 3.12, Git, curl, Poppler и `prlimit`. Выполнить из корня checkout. `SATURN_SOURCE` указывает на отдельный read-only checkout сайта, `DS_DC_CACHE` — на каталог вне рабочего дерева. Оригиналы файлов остаются в кэше.

```sh
python -m pip install -r requirements-dev.txt
git -C "$SATURN_SOURCE" rev-parse HEAD
python -m ds_dc.pdf_audit --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE"
python -m ds_dc.pdf_tables --cache "$DS_DC_CACHE"
export SATURN_BKD_PDF="$DS_DC_CACHE/030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a.pdf"
export SATURN_SLD_PDF="$DS_DC_CACHE/f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f.pdf"
python -m pytest -q
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" --evaluate output
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" --reference-only \
  --question 'Что такое СЛДКС-1?'
```

Перед `pytest` переменные `SATURN_SOURCE` и `DS_DC_CACHE` должны быть экспортированы. Команды аудита обращаются к издателю. Локальный API-адаптер пилота — mock. Для повторного прогона `pytest` и CLI можно использовать готовый кэш. Для проверки записей каталога без технических утверждений есть режим `--p0`.

## Ограничения для независимой приёмки

- Доступные полные материалы БКД-ПК-RF.2 проходят mock D1. Полная область СЛДКС-1 и сравнение превышают прежнюю mock-оценку контекста. Основная карточка и РЭ СЛДКС-1 проходят mock D1 в явно выбранном режиме `--reference-only`.
- Подтверждённый ответ на основе РЭ продемонстрирован для границы массы БКД-ПК-RF.2. Семантическая проверка произвольных модельных ответов и надёжность real API остаются открытыми. Сетевой live-адаптер отсутствует.
- Аудит обнаруженных ссылок охватывает активные исходники сайта. Один PDF требует проверки целостности. Разметка OCR и выборочная проверка таблиц указывают места для дополнительной сверки. OCR и Docling отдельно не запускались. Внешний реестр деклараций отмечен без проверки доступности.
- Один holdout по неподтверждённому кириллическому написанию ПО возвращает уточнение. Пилотные досье собраны для двух сущностей. Техническая память и бюджет mock работают в процессе локального CLI.
