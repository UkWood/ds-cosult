# DS-PILOT-02 source manifest

The two original dossier roots and all 28 secondary pages use Saturn commit `084d759487bfab6e111549c9b5469711ac5fc13e`. The checkout supplies Git objects during import. Subsequent questions use verified local copies. The 30 Markdown sources total 247,072 bytes.

The importer reads outbound Markdown links in the two dossiers and front matter references in `systems`, `articles` and `solutions`. It resolves each against a real entry and the Astro collection route templates in that revision. Discovery stops after this single hop. A system or component appearing in an article does not establish compatibility with the other dossier.

[Machine inventory with canonical URLs, exact Git blobs, byte hashes, sizes, reason/line, entity IDs, revisions and excluded links](DS-PILOT-02-SOURCE-MANIFEST.json). Local import writes this inventory to the immutable bundle directory. PDF custody receipts are separate and update only after local import.

## Included Markdown

| Source title | Canonical route | Inclusion evidence in root |
|---|---|---|
| Диспетчеризация лифтов СЛДКС-1 | `/articles/dispetcherizatsiya-liftov-sldks-1/` | sld articles[1] |
| Диспетчерский контроль подъемников для инвалидов видео и связь | `/articles/dispetcherskiy-kontrol-podemnikov-dlya-invalidov-video-i/` | sld articles[2], sld L77 |
| Интеллектуальное здание в городе Мурманск | `/articles/intellektualnoe-zdanie-v-gorode-murmansk/` | sld articles[3] |
| Обзор аппаратных средств | `/articles/obzor-apparatnykh-sredstv/` | sld articles[4] |
| Простая система диспетчеризации лифтов | `/articles/prostaya-sistema-dispetcherizatsii-liftov/` | sld L126 |
| СЛДКС-1 выпуск 2001-2004 г. | `/articles/sldks-1-vypusk-2001-2004-g/` | sld L85 |
| СЛДКС-1 выпуск 2005-2006 г. | `/articles/sldks-1-vypusk-2005-2006-g/` | sld articles[0], sld L93 |
| Диспетчеризация лифтов СЛДКС-1 | `/dispetcherizatsiya-liftov-sldks-1/` | sld solutions[0] |
| СЛДКС-1 | `/sldks-1/` | sld L34 |
| БДК-2М | `/products/bdk-2m/` | sld L103 |
| БДК-3М2 | `/products/bdk-3m2/` | sld L103 |
| БДК-4М2 | `/products/bdk-4m2/` | sld L103 |
| БДК-Л-3М2 | `/products/bdk-l-3m2/` | sld L101 |
| БДК-Л-4М2 | `/products/bdk-l-4m2/` | sld L101 |
| БГС-ПМ-В | `/products/bgs-pm-v/` | sld L104 |
| БГС-ПМ | `/products/bgs-pm/` | sld L104 |
| БИУ-Л | `/products/biu-l/` | sld L105 |
| БКД-М | `/products/bkd-m/` | sld L100 |
| БКД-МЕ | `/products/bkd-me/` | sld L100 |
| БКД-ПК-RF.2 | `/products/bkd-pk-rf-2/` | pinned primary dossier |
| БКД-Р | `/products/bkd-r/` | sld L118 |
| БПС | `/products/bps/` | sld L119 |
| ГР-1 | `/products/gr-1/` | sld L107 |
| ГР-1Д | `/products/gr-1d/` | sld L107 |
| КСН-313 | `/products/ksn-313/` | sld L101 |
| ЛИФТ-4 | `/products/lift-4/` | sld L99 |
| ТД | `/products/td/` | sld L109 |
| УКЛ | `/products/ukl/` | sld L102 |
| NEWEL | `/systems/newel/` | bkd systems[0] |
| Система лифтового диспетчерского контроля СЛДКС-1 | `/systems/sistema-liftovogo-dispetcherskogo-kontrolya-sldks-1/` | pinned primary dossier |

## Evidence coverage

The original importer produced 14 facts, 12 configuration-scoped relations and 2 document references. The expanded importer produces 156 typed fact positions, 42 configuration-scoped relations and 52 document references to 38 distinct URLs. Some fact positions conflict and therefore cannot be published as established claims. The candidate index has 1,556 YAML fields, array entries, heading and body lines, including header-associated Markdown table rows. These counts exclude PDFs. Candidate units are searchable excerpts and do not count as verified facts.

Historical composition uses the linked first- and second-generation articles. M2 with a dispatcher workstation and M2 without a computer use separate sections of the system root. Device facts apply to their own product cards. Typed lookup examines the entire applicable attribute ledger. For example, the БГС-ПМ card contains a scalar mass and an upper bound. The resolver presents both sourced positions as a conflict. Free prose and unmodeled fields remain searchable candidates.

The expanded device card supplies the previously unavailable answer to «Какая масса у БКД-МЕ?» (2 кг, `mass_kg`). The legacy two-file import has no БКД-МЕ source. The source contains 52 document listings, including 15 in the primary dossiers. The operating-manual link answer uses the relevant dossier listing. Link titles do not establish technical content.

## Document originals and exclusions

Both primary operating manual downloads returned HTTPS proxy CONNECT 403 and supplied zero bytes in this run. No PDF pages, binary digest or page claims were verified from these attempts. Physical pages and hashes are reported by the local PDF inventory only after verified import. The remaining originals were not downloaded.

- saturn:device:bkd-pk-rf-2 — https://www.mnppsaturn.ru/ftp/public/doc/bkd-pk-rf2/re%20BKD-PK-RF2.pdf
- saturn:system:sldks-1 — https://www.mnppsaturn.ru/ftp/public/doc/sldks/re%20SLDKS-1%20p1(3).pdf

The unresolvable legacy product query, external legacy regulation link and two body images are recorded individually in the JSON exclusions. The corpus also excludes image fields and drawings, video, OCR, external sites, archives, unstated relations, second-hop pages and the rest of the site. The three Markdown tables are candidate text with keyed cells. They do not establish measurements extracted from diagrams or PDF tables.
