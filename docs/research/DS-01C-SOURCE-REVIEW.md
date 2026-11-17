# DS-01C — Source Review / Preliminary Evidence v0.1

Дата: 2026-11-17. Статус: CANDIDATE, NOT EXPERT APPROVED.
Источник: `UkWood/Saturn-Main-Site`, commit `084d759487bfab6e111549c9b5469711ac5fc13e` (READ-ONLY).

## Проверенная структура
- `src/content/products/` — 292 записей; `src/content/systems/` — 25 систем и категорий.
- `src/content/groups/` — 23 группы; `src/content/articles/` — 36; `src/content/pages/` — 40; `src/content/news/` — 22.
- Реальная content schema: `src/content.config.ts`; часть полей `related`, `software`, `articles` автоматически сформирована по упоминаниям (см. `docs/content-model.md` источника), поэтому не доказывает совместимости.

## Кандидаты первичных источников
| Источник | Файл в `src/content/` | Git blob SHA |
|---|---|---|
| СЛДКС-1 | `systems/sistema-liftovogo-dispetcherskogo-kontrolya-sldks-1.md` | `42ed9f4a12a78dc4e91db91123c5ae20f9b3dca1` |
| ЕАСДКиУ | `systems/informatsionno-izmeritelnaya-sistema-easdkiu.md` | `59693f83fb8387468d3dfe6f9642f8e143b3f3b7` |
| СОС-95 | `systems/sistema-okhrannoy-signalizatsii-sos-95.md` | `84ade947e6f252fbbc5c289b333705c9faa52288` |
| БДК-3 | `products/bdk-3.md` | `9fee594bb700c1740f25f63856338a3f60518e4c` |
| БДК-4 | `products/bdk-4.md` | `0e86044db1c220432edc2cbeb2639fbd2c8e1d23` |
| БДК-3М | `products/bdk-3m.md` | `334ca39a523e8be47ca6bf1f175d37d875c34606` |
| БКД-М | `products/bkd-m.md` | `88c33ac32c850325305b8d3e5dca8cdb5deae54b` |
| БКД-МЕ | `products/bkd-me.md` | `3f77e13537945a2ae76fe604dd0ba2ccf9d78619` |
| БКД-UPS | `products/bkd-ups.md` | `86c126df822c54f69325b22e65e6c0e5520f1d54` |
| Saturn-PLC | `products/saturn-plc.md` | `a313902a3308bb34f0465ed10a638af184df2a04` |
| SatPlcStudio | `products/satplcstudio.md` | `a5e62a811de597289d5065c61eb9eb2346024d14` |
| АРМ LanMon | `products/arm-lanmon.md` | `860c97a1704af08aa8cd9c9a68722c25051ad763` |
| Сервер LanMon | `products/server-lanmon.md` | `516971ba9fc0f4a71f151ba90e1d16c88a306251` |
| ДВВ | `products/dvv.md` | `1f5178b5440dbc00147182e0a214030a48f54310` |
| МР-БУС | `products/mr-bus.md` | `c8cd1659bdaa24e971d639af39961c1d0467f0b0` |
| УСД-GSM | `products/usd-gsm.md` | `beacd985c08c254e241241a0c6acce77bec9aa94` |
| Паскаль-Д | `products/paskal-d.md` | `a2300077a58dcf6e9056287e96443c11b97699e0` |
| Паскаль-И | `products/paskal-i.md` | `19fc937fac24d30a7b77702e42ae9da45e5a6bcb` |
| МР AI4-AO2-DI2-DO2-D | `products/mr-ai4-ao2-di2-do2-d.md` | `36d8e176e413b501d26ff8a602c143980dc1ab66` |

## Верифицированные по исходной карточке примеры (НЕ экспертный Ground Truth)
- СЛДКС-1: назначение в разделе «Общие сведения» файла системы.
- ЕАСДКиУ: коммерческий и технологический учёт в тексте системы.
- СОС-95: одна master + до 255 остальных адресных устройств, файл системы, строка 36.
- БДК-3: `status: obsolete`, предупреждение о неприменении в новых проектах СЛДКС-1, `ip: IP54`.
- БДК-4: `status: obsolete`, `ip: IP54`, текст о встроенном переговорном устройстве.
- БДК-3М: три переговорных устройства согласно `specs`.
- БКД-М: источник заявляет номинальное выходное напряжение ИПЛ 24 В.
- ДВВ: `interfaces: RS-485`, `protocols: Modbus RTU`.
- БКД-ПК-RF.2: `interfaces: Ethernet, RS-485, RS-232, GSM/GPRS`.
- УПГС: в категории «Продукция, снятая с производства», но `status: active` — **неразрешённая неоднозначность метаданных**, а не доказанный технический конфликт.

## Нерешённое
Полные bytes SHA-256, PDF-страницы, URL маршруты, документы разных редакций, права передачи данных API, значения реального корпуса и утверждение специалистов отсутствуют. Ни одна запись не получила `expert_approved`.
