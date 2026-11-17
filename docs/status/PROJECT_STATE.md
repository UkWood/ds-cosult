# PROJECT STATE — DS-консультант

**Обновлено:** 2026-11-17  
**Текущий статус:** **DS-LV-02/P5 DEEP THINKING + NATIVE WEB SEARCH PASS WITH REVIEW NOTES; DS-01C GROUND TRUTH & CORPUS FREEZE PENDING**

## Решения владельца
- DS-консультант — независимый проект. `UkWood/Saturn-Main-Site` — READ-ONLY; NEW RAG не изменять.
- `UkWood/ds-cosult` — долговременная память, история, решения, требования и код.
- Основной API: **прямой DeepSeek** `https://api.deepseek.com`, `deepseek-flash`; ADR-0004, AI Tunnel ADR-0003 SUPERSEDED.
- DS-01 protocol accepted: W/A/B/C0, B-text/B-entity; Pilot 12, Core 60 (по 5 на категорию), 8 диалогов и 24 document tasks.
- Merge только после явного разрешения владельца; PR #1 остаётся Draft. **P1 и P2 PASS**, индивидуальные платные разрешения исчерпаны. **P3 выполнен и принят по tool-capability, один POST / $0.01; разрешение исчерпано**. P4 выполнен, **PASS WITH REVIEW NOTES**; платный GO 1 POST/$0.01 исчерпан; P5..P9, DS-02 coding, production и Corpus Freeze не разрешены.

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
3. Native DeepSeek **thinking = PASS for one smoke test**; standalone Search **P2 PASS / ACCEPTED**; Files/OCR/standalone Fetch/continuity **UNTESTED**; native URL Reading **P3 PASS** and model-managed Web Search **P4 PASS**, both with review notes.
4. Из 12 запланированных документов лишь 3 byte-pinned по Linux-отчёту, 9 ожидают проверку.
5. Независимый custody/audit локальных исходных PDF/PNG и манифеста не получен; billing не сверён.
6. Технические отношения, версии оборудования и неоднозначные стрелки в ЕАСДКиУ требуют экспертной оценки.

## DS-LV-02/CF-04 readiness update (2026-11-17)
- Официальные контракты нативных Web Tools, Files API, OCR, Search/Fetch и актуальная тарифная страница повторно изучены.
- Подготовлен исполнимый **по стадиям** протокол DS-LV-02 v0.2 с отдельными subgates P0..P9, наблюдаемой проверкой `server_tool_calls`, обработкой ошибок HTTP 200 и учётом billed tool units; **никаких новых API-вызовов не было**.
- Сформирован `docs/research/DS-01C-CF04-GT-EXPERT-PACKET.md`: 11 открытых кандидатов с точными SHA/page/scope, статус подписей специалистов **0/11**.
- Тарифы DeepSeek на дату подготовки: model tokens + отдельные Search/Fetch + PDF/OCR; фиксированный бюджет и hard stop для multi-search не доказаны. Для paid subgate требуется отдельный GO владельца.

## Owner GO — DS-LV-02 P1
- 17.11.2026 владелец ответил «Разрешаю, продолжай» на предложение P1: 1 платный вызов, максимум $0.01. Это разрешение записано в `docs/tasks/DS-LV-02-P1-OWNER-GO.md`; скрипт в `scripts/validation/ds_lv_02_p1_thinking.py`.
- **Статус P1: EXECUTED / PASS / ACCEPTED.** 17.11.2026 18:46:55 UTC: один direct API запрос HTTP 200, правильный ответ 9.8, `reasoning_content_present=true` (184 символа), `reasoning_tokens=65`, total 118 tokens, 1443 мс. Cost estimate $0.0000975, billing unverified. Отчёт: `docs/acceptance/DS-LV-02-P1-ARCHITECTURE-ACCEPTANCE.md`; sanitized evidence: `docs/evidence/DS-LV-02-P1-RESULT.json`. Текст reasoning не сохранялся, ключ не передавался; разрешение на один вызов ИСЧЕРПАНО.

## DS-LV-02/P2 owner authorization
- Владелец согласовал один прямой Search API вызов с бюджетом $0.01; `POST /v1/tools/search`, `count=1`, `need_content=false`. Published charge estimate $0.00075 for successful nonempty result, actual billing unverified.
- Safe test script: `scripts/validation/ds_lv_02_p2_search.py`; scope & GO: `docs/tasks/DS-LV-02-P2-OWNER-GO.md`. **P2 executed and accepted:** 2026-11-17 19:00:23 UTC, HTTP 200, `result_count=1`, valid official DeepSeek documentation URL, 862 ms, estimated $0.00075, actual billing UNKNOWN. Отчёт: `docs/acceptance/DS-LV-02-P2-ARCHITECTURE-ACCEPTANCE.md`, JSON: `docs/evidence/DS-LV-02-P2-RESULT.json`. Разрешение исчерпано, P3 не разрешён.

## P3 preflight preparation (2026-11-17)
- User: «Согласовано продолжай». P3 scope/offline preparation approved; no numeric budget was previously proposed. Paid P3 NOT AUTHORIZED until owner confirms proposed **1 HTTP POST and $0.01 USD** with acknowledged server-side fetch billing risk.
- Verified official docs (Chat Completions + `deepseek_read_url`), JSON `message.server_tool_calls`, true billed `usage.server_tool_use.tool_fetch`, and separate model token charges.
- Read-only one-page fixture `https://example.com/`; safe `scripts/validation/ds_lv_02_p3_url_read.py` with `--self-test` (zero network), one-attempt marker, getpass, redacted report.

## P3 offline preflight result (2026-11-17)
- Linux/WSL user report: `py_compile` clean; `--self-test` PASS; 0 network requests, $0 cost; local script SHA-256 `1de63e655bc84c19fce73076442280946ff099d06d5b3ae8898b4a8cd8fc26e2`.
- Detailed provenance and limits: `docs/evidence/DS-LV-02-P3-OFFLINE-PREFLIGHT.md`. **No paid DeepSeek request executed at this status review; owner P3 GO now documented: 1 request / $0.01**.

## P3 execution & architecture acceptance — 2026-11-17
- **P3 CAPABILITY PASS (ACCEPTED WITH REVIEW NOTES)**: 1 direct Chat Completions, HTTP 200, `read_link` completed on `example.com` with signature present, 419 tokens, 1 tool_fetch, 0 search, 1709 ms.
- Billing estimate $0.0009207, actual billed amount unverified. Owner GO exhausted; no repeat.
- **Important fixture drift:** independently fetched live `example.com` HTML contains `<title>Example Domain</title>` but NO `<h1>`. DeepSeek answer in Chinese **noted absence of H1 and page title correctly for current page**; old expected H1 is stale. The pinned P3 script's substring-only `PASS` is not valid proof of H1 extraction. Source semantics consistency reviewed separately; not byte-pinned to DeepSeek tool payload.
- Language continuity issue: Chinese response to Russian prompt. Evidence: `docs/evidence/DS-LV-02-P3-RESULT.json`, acceptance `docs/acceptance/DS-LV-02-P3-ARCHITECTURE-ACCEPTANCE.md`, quality `docs/quality/DS-LV-02-P3-FIXTURE-DRIFT.md`.
- P4 model-directed `deepseek_web_search` draft at `docs/tasks/DS-LV-02-P4-WEB-SEARCH-PROPOSAL.md`; P4..P9 NOT AUTHORIZED.

## Next stage
- **CF-01/CF-04:** route 11 evidence seeds to two-person expert review using `docs/research/DS-01C-CF04-GT-EXPERT-PACKET.md`; don't publish hidden Core/GT, don't invent signatures; remaining PDF/relations still open.
- **DS-LV-02:** staged conformance v0.2 `docs/tasks/DS-LV-02-EXECUTION-PROTOCOL.md` (P0 offline); **P1 PASS; P2 Search PASS; P3 URL Reading PASS with review notes; P4 Web Search PASS with review notes; P5..P9 NOT AUTHORIZED**. P3: `docs/tasks/DS-LV-02-P3-URL-READING-PROPOSAL.md`.
- **DS-02 Minimal Harness / Pilot:** only after separate Architecture decision and approved gates; no implementation begun.
- **Draft PR #1 remains OPEN, NO MERGE / NO PRODUCTION.**

## DS-LV-02/P3 owner paid GO — 2026-11-17
- Пользователь ответил «Разрешаю» на прямой вопрос: «Подтверждаете GO для одного платного вызова `deepseek_read_url` с лимитом $0,01 USD?». **OWNER GO GRANTED: exactly one Chat Completions HTTP POST, $0.01 organizational limit**.
- Официальный контракт URL-reading повторно сверён; script from SHA `4b6bdf5058946337021aade831d09cf34831ecaa` успешно прошёл WSL offline preflight. **P3 paid request EXECUTED 2026-11-17 19:16:47 UTC**.
- Статическая строка `authorization` внутри ранее закреплённого скрипта всё ещё содержит `P3_BUDGET_OWNER_GO_REQUIRED_BEFORE_EXECUTION`; это метка времени создания скрипта, а не действующее состояние разрешения. **Нормативный источник GO — запись в `docs/tasks/DS-LV-02-P3-OWNER-GO.md`**; при приёмке явно сверить обе записи и не делать повторов.

## P4 preparation (2026-11-17)
- Owner: «Разрешаю» after proposal to proceed to native `deepseek_web_search`, **but no numeric spend limit in that proposal**. Scope and offline work approved; **paid call not yet authorized**.
- Reviewed official DeepSeek Web Tools/Chat Completions docs and pricing. 1 outer HTTP call may create multiple billable `tool_search` and `tool_fetch` operations; these are distinct from HTTP calls. Proposal: one POST, $0.01 organizational limit, risk of not having provider-enforced hard cap.
- WSL offline safety/selftest script: `scripts/validation/ds_lv_02_p4_web_search.py` — `--self-test` costs $0; real mode uses getpass, no retry, atomic marker and redacted diagnostic.
- User-supplied `Example Domain.html` (related P3) examined as a separate file. SHA256 `25ddf2c883e0d1958ea971d279a7e4f0fd446724ee3db7db19dadabd4a62e484`, 577 bytes; contains HTML title `Example Domain` and no H1. **Not a copy of the DeepSeek tool's encrypted snapshot**; no original uploaded HTML bytes published.

## P4 offline preflight acceptance (2026-11-17)
- WSL report: `py_compile` clean, `--self-test` PASS, network requests 0, API cost $0; local script SHA256 `c10bd4a6b22aedb74f059a1d089c089e6686f70c6b247c993b315bd2710ba0bd`.
- Acceptance evidence `docs/evidence/DS-LV-02-P4-OFFLINE-PREFLIGHT.md`. **P4 PAID NOT YET EXECUTED; ONE POST / USD $0.01 remains a proposed, NOT approved numeric budget**. P5..P9 blocked.

## P4 explicit paid GO — 2026-11-17
- Owner reply «Подтверждаю» to a question proposing **one paid P4 Chat Completion** and **$0.01 USD organizational limit** with acknowledged risk of multiple billed server-side Search/Fetch operations. This is NOT a provider-enforced hard cap.
- GO: `docs/tasks/DS-LV-02-P4-OWNER-GO.md`, pinned script `scripts/validation/ds_lv_02_p4_web_search.py` unchanged, WSL preflight accepted. **P4 EXECUTED / ACCEPTED, GO exhausted. P5..P9 NOT AUTHORIZED.**
- Static `authorization=P4_NUMERIC_BUDGET_GO_REQUIRED_BEFORE_PAID_RUN` in the verified script predates the GO and is a historical metadata label; authoritative authorization is the owner GO document. Do not rewrite the tested script only to change this label.

## P4 live execution + acceptance — 2026-11-17 19:40:03 UTC
- Owner-authorized 1 direct POST, HTTP 200, `deepseek_web_search` actually invoked and completed, **3 billable internal searches**, 13 sources reported, 9 citations saved, URL overlap true, 0 fetch. 9393 prompt tokens + 303 completion = 9696 total; 3638 ms, Russian answer preview.
- Primary official release `https://api-docs.deepseek.com/news/news261113/` independently verified (date 2026-11-13, native Search and Fetch features). Only first 480 chars of answer accessible: **factual_answer_gate=NEEDS_SOURCE_REVIEW** remains. Citation trace passed, full claim grounding unmeasured.
- Peak fee estimate $0.0054315; off-peak cache-miss estimate $0.00384075 for 19:40 UTC. Actual billing unknown; $0.01 organizational limit not enforceable by current script. P4 authorization **exhausted**; no re-run.
- Architecture result **PASS WITH REVIEW NOTES**. Evidence `docs/evidence/DS-LV-02-P4-RESULT.json`; acceptance `docs/acceptance/DS-LV-02-P4-ARCHITECTURE-ACCEPTANCE.md`.
- P5 thinking+search **offline preparation approved; paid testing NOT AUTHORIZED**: `docs/tasks/DS-LV-02-P5-THINKING-WEB-SEARCH-PROPOSAL.md`. P5 single paid request executed 2026-11-17 20:07:23 UTC; GO exhausted; P6..P9 not authorized.

## P5 OFFLINE preparation authorized — 2026-11-17
- Owner reply «Разрешаю» interpreted as approval for **free research and offline script**, as the proposal explicitly calls for a separate numerical GO before a paid test.
- Official DeepSeek docs: deep thinking search may perform **about 20 internal tool steps**, single search can bill multiple queries, `max_tool_calls` ignored in Responses API. No verified enforceable per-request USD cap in consulted docs; 1 HTTP POST and `max_tokens` alone do not guarantee charge below $0.01. See `docs/research/DS-LV-02-P5-SERVER-TOOL-BUDGET-REVIEW.md`.
- Safe `scripts/validation/ds_lv_02_p5_thinking_search.py` prepared; run `--self-test` only before budget GO. **No P5 HTTP request executed; no new DeepSeek charges.**

## P5 Offline WSL preflight acceptance — 2026-11-17
- Script from pinned commit `4009ad2d17d71c627deb61b0fca3c941f7a27e3a` compiled successfully and synthetic `--self-test` returned **PASS**. Owner-reported local SHA-256: `4a9dd93517ae09a1e0f1ec61415d1ab65666cdb127a2d0dd2681c43941882608`. `NETWORK REQUESTS: 0 | API COST: $0`.
- Acceptance record: `docs/evidence/DS-LV-02-P5-OFFLINE-PREFLIGHT.md`. **Only offline preflight accepted**. Live Deep Thinking + native Web Search remains UNTESTED and **PAID P5 OWNER GO APPROVED (1 POST / $0.05, not yet executed)**; P6–P9 not authorized.

## P5 explicit paid GO — 2026-11-17
- Owner answered «Да» to explicit **one paid P5 POST / organizational $0.05 USD with risk of exceeding this amount**. Authoritative record: `docs/tasks/DS-LV-02-P5-OWNER-GO.md`.
- **P5 EXECUTED AND ACCEPTED FOR TOOL CAPABILITY; GO exhausted**, pinned WSL script unchanged after offline PASS; one attempt only, no retry. The monetary limit is NOT a hard API cost cap; server-side Search/Fetch and input/output charges may exceed it. P6..P9, Merge, DS-02 and production not authorized.

## P5 live Deep Thinking + native search / Architecture Acceptance — 2026-11-17
- Owner-authorized **1 direct paid POST** completed at 2026-11-17 20:07:23 UTC, HTTP 200, model `deepseek-flash`, thinking enabled, `reasoning_tokens=856`, 3122 reasoning chars reported (**raw reasoning not retained**).
- `deep_search` 2 tool steps; actions 1 search / 4 `open_page` / 0 `find_in_page`, all 5 completed; 4 individual search queries billed, 24 sources reported, 3 structurally valid citations (all spans valid), source overlap.
- 14,645 prompt (5,760 cache hit + 8,885 miss) + 1,418 completion = 16,063 tokens; latency 9,245ms; peak estimate $0.00740166, applicable off-peak estimate $0.00520083; actual billing unknown.
- **4 open_page and 0 billed fetch is consistent with official DeepSeek billing rules** (page content already in search results/cached or page navigation can be free). Exact underlying source per action cannot be reconstructed from redacted JSON.
- Source verification: initial answer preview and official docs consistent; **full 1,259-character answer NOT independently examined**, `factual_answer_gate=NEEDS_SOURCE_REVIEW`. Full answer stored locally only; no reasoning text persisted. This is tool-capability PASS, not verified claim-by-claim correctness.
- Acceptance **P5 PASS WITH REVIEW NOTES**: `docs/acceptance/DS-LV-02-P5-ARCHITECTURE-ACCEPTANCE.md`; evidence `docs/evidence/DS-LV-02-P5-RESULT.json`. **P5 authorization EXHAUSTED; no repeat**. P6 synthetic Files text/rich stage authorized for constrained preflight and sequential execution `docs/tasks/DS-LV-02-P6-FILES-PREPARATION-PROPOSAL.md`; P6..P9 OWNER BLANKET GO (controlled execution only; not yet run).

## DS-LV-02 P6–P9 blanket owner authorization — 2026-11-17
- Owner directly approved: «Даю общее разрешение на выполнение P6–P9 с установкой осмотрительных лимитов». Architecture defined **global organizational $0.05 USD**: P6 $0.02 / ≤8 HTTP calls (2 upload/chat/delete/verify cycles), P7 $0.01 / 1 HTTP, P8 $0.02 / 4 HTTP, P9 $0 / 0 HTTP. **13 external HTTP calls maximum**, no retries, monetary figures not provider hard caps.
- Consent scope limited to **synthetic one-page documents**, no confidential Saturn PDFs/GT, production or training. Every stage/subgate requires offline preflight and independently reviewed output, strict stop after errors, cost uncertainty or failed Files cleanup.
- Official file-contract check: `POST /files` purpose before file; expiry 3600 sec, upload parse on server even after disconnect; `file_id` Chat content block; `DELETE /files/{id}` response `deleted:true` then GET 404. P7 OCR does not store in Files API, billed by successful page.
- Authorization/limits `docs/tasks/DS-LV-02-P6-P9-OWNER-BLANKET-GO.md`. P6 staged test code `scripts/validation/ds_lv_02_p6_files.py`. **No P6–P9 paid calls yet**.

## P6 WSL offline preflight accepted — 2026-11-17
- Owner reported successful `py_compile`, `--self-test` PASS, **0 DeepSeek network requests, $0 cost**. Script local SHA-256 `35c2e9b8ca89b2de75395f8097b3061e1d4417e3b56c1855c99ee48f7808c0a4`, pinned Git blob `3ef0b10108d8133ed4088c0adad4071aaea01ca4`.
- Fixture local SHA-256 `069a6f1192bd80b10315302a85bedb3f1c79f76973d4f504b25645385cc9c286` checked `OK`, 1 page, `pdftotext` matches FENIX-17 12.4L TX-731 and ORBIT-5 6.8L RB-204. Evidence `docs/evidence/DS-LV-02-P6-OFFLINE-PREFLIGHT.md`.
- **P6-TEXT now ready for one controlled upload + chat + delete + GET absence cycle (≤4 HTTP / $0.010 organizational first-variant budget), under general owner GO.** Not yet executed; P6-RICH and P7–P9 remain stage-gated.
