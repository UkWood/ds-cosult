# PROJECT STATE — DS-консультант

**Обновлено:** 2026-11-17  
**Текущий статус:** **DS-LV-01 ACCEPTED WITH REVIEW NOTES; DS-01C GROUND TRUTH & CORPUS FREEZE PENDING**

## Решения владельца
- DS-консультант — независимый проект. `UkWood/Saturn-Main-Site` — READ-ONLY; NEW RAG не изменять.
- `UkWood/ds-cosult` — долговременная память, история, решения, требования и код.
- Основной API: **прямой DeepSeek** `https://api.deepseek.com`, `deepseek-flash`; ADR-0004, AI Tunnel ADR-0003 SUPERSEDED.
- DS-01 protocol accepted: W/A/B/C0, B-text/B-entity; Pilot 12, Core 60 (по 5 на категорию), 8 диалогов и 24 document tasks.
- Merge только после явного разрешения владельца; PR #1 остаётся Draft. Нет разрешения на DS-02 coding, production, новый платный вызов или Corpus Freeze.

## Доказательный baseline сайта — кандидат
`UkWood/Saturn-Main-Site` commit `084d759487bfab6e111549c9b5469711ac5fc13e`, tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`.

## DS-01C benchmark
- 60 Core candidates, 12 Pilot, 8 dialogue scenarios, 24 document tasks, 17 extracted fact candidates — структурный PASS.
- **0 expert-approved GT**; технические отношения и утверждения по графам требуют отдельной экспертизы.
- Три PDF имеют **Linux-reported locally checked SHA-256**, подробный JSON-manifest `docs/evidence/DS-LV-01-PDF-MANIFEST-REPORTED.json`.
- Шесть физических страниц PNG визуально проверены **в Linux Validation Session**, другие девять PDF ещё не закреплены. ЕАСДКиУ рис.1 — частично неоднозначен.
- Отчёт архитектурной приёмки: `docs/acceptance/DS-LV-01-ARCHITECTURE-ACCEPTANCE.md`.

## DS-LV-01 acceptance
- LV-ENV-01: PASS (Ubuntu WSL2, Poppler).
- LV-PDF-01: PASS **по отчёту с локальными SHA256**.
- LV-PDF-02: PASS WITH REVIEW NOTES (6 PNG).
- LV-API-01: PASS — 1 direct API call (`deepseek-flash`), HTTP 200, 21 tokens, 1064 ms, no tools, no uploads.
- Один платный запрос был **явно одобрен владельцем** с лимитом $0.01 USD. Денежное списание не проверено по billings.
- **Оригинальные PDF/PNG и локальный evidence-manifest в Architecture Session A не поступили**; независимое побайтовое перепроверение не выполнено.

## Remaining blockers
1. `ds-cosult` PUBLIC: нельзя публиковать закрытый Core/GT, секреты и ограниченные источники.
2. Нет expert-approved Ground Truth, DS-CORPUS-1.0 не frozen.
3. Native DeepSeek thinking/web/URL/Files/OCR/Search/Fetch/continuity **UNTESTED**.
4. Из 12 запланированных документов лишь 3 byte-pinned по Linux-отчёту, 9 ожидают проверку.
5. Независимый custody/audit локальных исходных PDF/PNG и манифеста не получен; billing не сверён.
6. Технические отношения, версии оборудования и неоднозначные стрелки в ЕАСДКиУ требуют экспертной оценки.

## Next stage
- **CF-01/CF-04:** independently inspect source evidence and expert-review technical facts, particularly 11 public PDF evidence seeds and relation provenance; remaining PDFs staged separately.
- **DS-LV-02:** Draft native DeepSeek capability conformance in `docs/tasks/DS-LV-02-NATIVE-API-CONFORMANCE.md`; **not authorized**, needs paid-call budget and new GO.
- **DS-02 Minimal Harness / Pilot:** only after separate Architecture decision and approved gates; no implementation begun.
- **Draft PR #1 remains OPEN, NO MERGE / NO PRODUCTION.**
