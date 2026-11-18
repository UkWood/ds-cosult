# DS-01C / CF-04 — Open Ground Truth Expert Review Packet v0.1

**Дата:** 2026-11-17  
**Статус:** EVIDENCE CANDIDATES PREPARED — **0 EXPERT APPROVED**  
**Назначение:** передать профильному техническому рецензенту **открытые** факты из трёх закреплённых по Linux-отчёту PDF; не включать закрытые Core-тесты или ответы.

## 1. Evidence baseline (Linux-reported, not independently rehashed by Architecture Session A)

| Doc ID | Document | Local PDF bytes SHA-256 | Physical pages | Source identity |
|---|---|---|---:|---|
| PDF-P01 | СОС-95 | `2dce9d7a2b4c2d0cbb222e4233c164523b2605d80ca20eb0abd2b5c1bd39a9ee` | 195 | URL in DS-LV-01 manifest, revision 2002 |
| PDF-P02 | СЛДКС-1 | `f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f` | 83 | URL in DS-LV-01 manifest, 26.05.2011 |
| PDF-P03 | ЕАСДКиУ | `62de0ffad9f6a045c60f666d216385c5ba678ec5733be857aa2f6dea28b00486` | 79 | URL in DS-LV-01 manifest, 2006 |

Original PDF and six rendered PNG are still stored **only in Linux WSL**. Independent checksum rerun in Architecture Session A not performed. To approve GT reviewers must inspect **these exact byte-pinned files**, not a changed live URL.

## 2. Review candidates — atomic technical scope

| Seed ID | PDF page / part | Candidate normalized assertion | Mandatory qualifiers | Initial triage |
|---|---|---|---|---|
| PEV-SOS-01 | P01 p9 table2 #13 | 2 km | length of **one SOS-95 ray without УСЛ**, upper limit | verify |
| PEV-SOS-02 | P01 p9 table2 #14 | 10 km | length of **one SOS-95 ray with УСЛ blocks**, upper limit | verify |
| PEV-SOS-03 | P01 p9 table2 #15 | 24 V DC | nominal ИПЛ voltage in specified SOS-95 manual | verify |
| PEV-SLD-01 | P02 p7 table1 #3 | 255 address blocks | **per one master ray**, upper limit | verify |
| PEV-SLD-02 | P02 p7 table1 #5 | 3 km | **without repeater**, coaxial, SLDKS-1 revision 2011 | verify |
| PEV-SLD-03 | P02 p7 table1 #5 | 1 km | **without repeater**, twisted pair, SLDKS-1 revision 2011 | verify |
| PEV-SLD-04 | P02 p18 table7 + fig1 | master, addressed blocks, repeater, power supply, terminator present | **depicted reference schematic** only, not universal wiring instructions; power budget affects device count | important: visual |
| PEV-EAS-01 | P03 p3 section1 | energy/resource measurement and commercial/technological accounting | refers to EASDKIU as described in 2006 manual | verify |
| PEV-EAS-02 | P03 p4 table1 | KM-5 entry: RS-232 (RS-485) | **row-specific** interface listing, not all meters and not modern universal compatibility | verify |
| PEV-EAS-03 | P03 p12 fig1 | levels 0,1,2,3 and components arranged in diagram | no automatic claim about arrows, bidirectional transfer, protocols or obligatory paths | **BLOCKED interpretation** |
| PEV-EAS-04 | P03 p12 after fig1 | minimum system includes meters + AРM + PostgreSQL; АРМ and DB may be on same computer | 2006 architecture; distinguish Server LanMon | verify |

The reviewer must not infer current production status or suitability of obsolete devices from old documents. `PEV-EAS-03` must be decomposed: the **visible labels/levels** may be accepted independently, while **edge direction/protocol/mandatory routing** stays blocked unless explicitly documented.

## 3. Required 2-person review path

- **Source reviewer:** confirms exact SHA identity; looks at physical PDF page, actual quote/field, printed page versus physical page; checks units, footnotes, section scope and any conditional.
- **Technical reviewer:** confirms technical meaning, applicability, omissions, variant/version restrictions and whether claim is safe for general answering.
- **Adjudicator:** resolves disagreements and marks `expert_approved`, `approved_with_qualification`, `rejected`, or `blocked` with dated rationale.
- Neither model-generated answer nor the original author of a candidate can self-approve its technical meaning. The reviewer signs an ID, not a general blanket acceptance of the file.

## 4. Review record for every seed

```yaml
evidence_id: PEV-SLD-02
source_document_id: PDF-P02
source_sha256: f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f
physical_page_1based: 7
printed_page: 7
section: "Table 1 / item 5"
claim_kind: conditional_numeric_limit
normalized_value: "3 km"
applicability: "SLDKS-1, 2011 revision, single coaxial IPL ray without repeater"
source_reviewer_id: null
technical_reviewer_id: null
source_quote_sha256: null  # capture from exact approved quotation
technical_review_status: needs_review
scope_decision: pending
reviewed_at: null
adjudication_notes: null
expert_approved: false
```

Required: exact statement + units + system + edition + cable/repeater/УCЛ condition + page and optional direct quote SHA; if comparison between systems, pin **both** source documents separately.

## 5. Expert reviewer checklist

- Проверен ли **оригинал с указанным SHA-256**?
- Верно ли название системы, исполнение, revision/дата?
- Сохранены ли «не более», «типовой», «при ...», «без усилителя», «один луч», ограничения питания?
- Есть ли уточняющая сноска, таблица, другой раздел документа, меняющий применимость?
- Может ли инженер по этому факту **безопасно рекомендовать** оборудование в новом проекте, или это лишь описательное историческое свойство?
- Нельзя ли спутать СОС-95 (2 км без УСЛ) с СЛДКС-1 (3 км coax / 1 км twisted pair без усилителя)?
- Можно ли точно доказать стрелку связи на ЕАСДКиУ рис.1? Если нет, это `blocked`, а не `false`.
- Объясните любые расхождения с сайтом/новой документацией, не заменяйте эталон автоматически.

## 6. Quality gates

- 11 evidence seeds have explicit source hash, page and scope: **PREPARED**.
- Same document hash repeated consistently across manifest: **PASS (record consistency only)**.
- Expert sign-offs: **0/11**.
- Current docs pages and schematic semantics: **needs_review**.
- Core benchmark and Gold labels: unchanged, not published, not frozen.
- 9 of 12 PDF still without their own pinned originals: **OPEN**.

## 7. Next steps

After offline expert signatures, create a reviewed facts ledger in a protected workspace. Public repo may hold only agreed public facts/status and anonymized review evidence. Hidden Core and its target answer mappings must never be revealed before Core testing. Do not move to Corpus Freeze based merely on this packet.
