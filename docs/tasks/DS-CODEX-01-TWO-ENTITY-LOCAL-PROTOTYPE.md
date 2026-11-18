# DS-CODEX-01 — Local Working Prototype: Two-Entity Entity-Centric Verifiable RAG

**Date:** 2026-11-18  
**Project:** DS-консультант (NOT NEW RAG)  
**Owner approval:** coding on a **restricted local prototype** after architecture PR #1 is merged into main  
**Status:** **APPROVED FOR SEPARATE CODEX IMPLEMENTATION SESSION — DO NOT START PAID API EXECUTION**  
**Repository:** `UkWood/ds-cosult`  
**Coding branch:** create a **NEW** `feat/ds-pilot-01-two-entity-chat` (or unique equivalent if already present) from **verified final main merge commit of PR #1**; create ONE new **Draft PR** (PR number cannot be presumed); do not commit directly to main or merge the coding PR.  
**Immutable architecture:** `docs/decisions/DS-ARCH-BASELINE-01-OWNER-ACCEPTED-CODING.md`, DS-EC-02–05, DS-SEC-07/08/09/10. **R4-CR01** at the owner-decision baseline is mandatory, not optional.  
**Corpus:** exactly two source objects as pinned in `docs/corpus/DS-PILOT-01-TWO-ENTITY-SOURCE-SCOPE.md`: **device БКД-ПК-RF.2** and **system СЛДКС-1**.  
**Purpose:** a REAL runnable and inspectable LOCAL chat to test source-grounded answers, multi-need completeness, typed dialog context and safe unknown behavior. **Not production, not public internet service, not full platform rewrite**.

## 1. Deliverable to owner — working software, not another plan

Provide an actual working prototype the owner can run under Linux/WSL2 on their computer (32 GiB RAM is available; do not require a local LLM or GPU). It must run **offline after one-time read-only source import** and provide:

1. **Local web chat UI** on `http://127.0.0.1:8765`: ask questions in Russian, see human-readable answer, **source citation links/field paths** and explicit status `answered/partial/clarification/needs_support/error`. Show current focused entity, ability to clear current session, distinguish original question vs follow-up and show a small optional **developer diagnostics drawer** with frozen needs, per-need reasons and evidence provenance. Clean simple layout (desktop and phone widths). Do not expose public raw audit/IP/keys.
2. **CLI equivalent** (`ds-consult ask` or `python -m ds_consultant ask`) for scripted questions and status/need/citation output, no HTTP client prerequisite.
3. **Two reproducible dossiers** from the immutable Saturn source repository, with real structured facts, qualified system prose, document navigation links and no invented cross-entity technical relation.
4. **Deterministic source-backed local route P0** that answers basic technical/site-source questions and safely declines or qualifies unproven/scope-incomplete questions. This is **the initial fully testable acceptance path**: NO paid DeepSeek required.
5. **Mock P1/P2 provider adapters and testable one-call guards**, plus an **optional direct DeepSeek adapter** whose live network dispatch is **DISABLED by default**, even when a key is present. Do not make any live/paid API request during Codex implementation or acceptance work; a future independent owner GO must set exact max count and USD cap.
6. **Offline automated tests** for corpus ingestion/proof, two-entity identity, R4-CR01 frozen QuestionNeeds, 12 designed mixed-need cases (when achievable at contract level), valid P1 unsupported, malformed/omitting P1/P2, one-call budget/idempotency, and representative Russian dialogue samples. Tests must show actual PASS/FAIL outputs.
7. **One-command reproducible local start** documented step-by-step: `python -m venv .venv`, pip install, read-only corpus bootstrap with verified git SHA, test command, local launch. Provide `README`/ `docs/runs/DS-PILOT-01-LOCAL-RUNBOOK.md` with Windows+WSL2 instructions and troubleshooting.
8. A small **real verification report** in `docs/implementation/DS-CODEX-01-IMPLEMENTATION-REPORT.md`, with feature inventory, exact source and code commit SHAs, recorded unit/integration test counts, known restrictions, and explicit statement live DeepSeek calls **0**.

**No substitute deliverables**: sketches, isolated functions or merely a static mock chat page are not sufficient. A user must be able to start the server and ask real questions about these two actual site-source entities.

## 2. Narrow technology choices (prefer fewer moving parts)

Use **Python 3.11+**, `FastAPI` + `uvicorn` for localhost HTTP, `PyYAML` for Astro content front matter, `sqlite3` from standard library for local catalog/session/idempotency/private test audit, `httpx` ONLY for optional disabled DeepSeek provider adapter, `pytest` for tests. A minimal vanilla HTML/CSS/JavaScript page is preferred; **do not require React/Node, Docker, Qdrant, vector database, Redis, Ollama, paid embeddings or NVIDIA GPU**.

Suggested structure, adjust to match repo conventions:
```
src/ds_consultant/
  app.py                 # FastAPI loopback routes/static UI
  config.py              # explicit experimental mode, policy limits
  sources/               # pinned Saturn Git-reader & YAML/Markdown adapter
  evidence/              # entity/fact/relation/source bundle, local FTS/lookup, eligibility
  dialogue/              # session context, referents, request/QuestionNeeds freeze
  answer/                # deterministic final status/reason and citation renderer
  providers/             # P0, mock P1/P2, disabled live DeepSeek adapter
  security/              # input/domain/session/quota, tokens/cost/idempotency
  storage.py             # local SQLite and privacy retention
web/                     # minimal UI
tests/                   # synthetic + two-real-site-source regression fixtures
docs/runs/               # local runbook
docs/implementation/     # real implementation evidence
```

Use normal `pyproject.toml`, locked or bounded dependencies with a documented install method, `.gitignore` for `.env`, SQLite, raw logs, API secrets, downloaded PDF bytes, local site clone, private benchmark/GT, generated caches and backups. No dependency that requires a paid cloud service.

## 3. Corpus integrity and exact two roots

**Source Git repository is READ-ONLY:** `https://github.com/UkWood/Saturn-Main-Site`. Pin `084d759487bfab6e111549c9b5469711ac5fc13e`; read only these **two** source root paths and check exact blobs:
- `src/content/products/bkd-pk-rf-2.md`, blob SHA `86afcfe8be3be4e5022f0baf43143f64a2a9f7a0`, site route `/products/bkd-pk-rf-2/`;
- `src/content/systems/sistema-liftovogo-dispetcherskogo-kontrolya-sldks-1.md`, blob SHA `42ed9f4a12a78dc4e91db91123c5ae20f9b3dca1`, site route `/systems/sistema-liftovogo-dispetcherskogo-kontrolya-sldks-1/`.

Derive a deterministic `SourceBundle` and provenance manifest with commit, Git blob ID, SHA-256 actual source bytes, parser revision, exact field path and Markdown section/line span, source-associated entity/variant and canonical source URL from approved site routes. **Refuse if pinned bytes/blob differ**. Do not guess missing site routes or PDF origins.

Extract representative **structured site fields** for БКД-ПК-RF.2 (interfaces, operating temperature, DC vs AC power, mass, dimensions, documented features) and exactly qualified **system prose** for СЛДКС-1 (purpose, relevant M2 generation/components, documentation metadata). Extract facts as typed field values with units/conditions rather than letting model invent canonical values. Preserve whether a `specs` item had an empty `name`; do not arbitrarily assign semantic attribute.

Allowed navigation: render metadata-only original document links read from the source front matter; **never treat the link as proof of PDF content**. There is **no guaranteed approved pinned PDF content** in this scope. No PDF-based electrical connection, terminal wiring or system compatibility claims until a separately approved byte-pinned physical-page/locator import. Do not download/upload PDFs automatically, do not browse live Internet at runtime.

**Relation safety test:** no source proves that БКД-ПК-RF.2 is a component of, or interoperates with, СЛДКС-1; never add synthetic cross-entity `part_of` or `compatible_with`. In SLDKS system text, M2 component descriptions are only attributed to that generation/configuration.

**L0/L1/L2/L3 bounded evidence:** local entity aliases (L0), concise summaries (L1), structured Fact/Relation records (L2), exact source field/section snippets on demand (L3). For this two-root scope a deterministic Python dictionary + SQLite/FTS suffices; vector search and external embeddings are **not required**. Use a versioned attribute/qualifier dictionary and source-specific `EvidenceEligibilityDecision`; missing source not a negated technical fact.

## 4. HARD REQUIREMENT R4-CR01 — original question never silently shortened

**Authoritative owner decision (copy exactly in code comments/test names):**
> «При ADMITTED фиксируется исходный вопрос и его контекст. После P1 сервер окончательно формирует и проверяет полный набор QuestionNeeds. Затем набор фиксируется до итоговой проверки и формирования ответа. Зависимости устанавливаются по проверенным источникам до вычисления FinalStatus. Ни P1, ни P2 не могут самостоятельно исключить обязательную часть исходного вопроса.»

Implement **two distinct freezes**, without weakening already accepted admission:
1. `ADMITTED`: persist exactly `original_question_exact`, request idempotency identity, canonical parsed question spans/clauses, immutable active `DialogState`/referents and SourceBundle/policy/revision IDs. This snapshot is authoritative; P1 never rewrites it.
2. `SERVER_FINALIZE_NEEDS`: server reconciles the required technical clauses of original text and existing dialogue context with P1 suggestions (if invoked); **all** required original question parts become distinct atomic `QuestionNeed` or a visible unresolved coverage diagnostic. Never accept a `P1` response with omitted conjunction/need as exhaustive. For unsupported/ambiguous complex parse, return scoped clarification instead of a false complete answer.
3. `FREEZE_QUESTION_NEEDS`: store canonical ordered `QuestionNeeds`, source-span coverage mapping, exact `question_needs_hash` (binding original question hash, pinned context, policy/bundle, need IDs/variants/attributes). **No additional P1 or P2 changes permitted**. Hash never changes during the remaining admitted turn.
4. `EVIDENCE_DERIVED_DEPENDENCIES`: only source-validated rules/relations/qualifiers can establish prerequisite need edges **before** DS-EC-05 §13.1.1 final status computation. If prerequisite unavailable, prune dependent unproven technical claims; retained independent claims can produce explicitly qualified `partial`.
5. `P2` selects from existing evidence for the frozen needs; even if P2 omits a required need or proposes `answered`, server final gate compares against immutable original/clause coverage and returns only verified `partial/clarification/needs_support/error`, never a silent answer of only the easiest half.
6. Session follow-up is a **new** admitted turn; use typed anaphora if context unexpired; 15m expiry clears technical referents, not the already persisted original request and audit.

**Mandatory fake P1/P2 negative tests:**
- “Укажи питание БКД-ПК-RF.2 **и** назначение СЛДКС-1”: P1 returns only BKD need → server detects uncovered mandatory SLDKS clause, does **not** emit full answered; if server can independently parse both, it must recover both and answer both with distinct citations. No second paid call.
- P2 omits one of two already frozen needs → full answered prohibited; per-need unresolved status or independently validated existing fact, frozen hash unchanged.
- Comparison needs multiple entity/attribute scopes → each required comparator need retained; unknown system property => partial/needs_support, never synthetic value.
- “А ещё…” follow-up plus old pronoun referent → both current explicit and prior referenced entity scopes maintained or safely clarified, not merged.
- Proven source-dependent fact with missing prerequisite → fail closed on dependency, no unsupported partial.
- Any duplicated/mismatched need_id/question_needs_hash or model-invented source id → reject model output deterministically.

Use this exact design as controlled implementation requirement R4-CR01, **not** a request for further independent architecture review.

## 5. Canonical final answer and source proof

Use DS-EC-05 §13.1.1 status/reason reducer, **after server-complete needs freeze and source-verified dependencies**. Required behavior:
- All required needs safely satisfied → `answered`. Only metadata navigation needs → `ReasonCode=document_reference_only`; with technical facts → `fully_supported`.
- At least one independent satisfied need and another unresolved → `partial` with **specific highest-priority** error > ambiguity > support reason; all remaining need-ID reasons retained in diagnostics, never silently dropped.
- None satisfied → `error` for source/internal errors, else `clarification` for unresolved entity/variant/intent, else `needs_support`; no ungrounded claim.
- Source-proven conflict positions are citeable as **attributed-only** and never established Fact; a metadata document link cannot satisfy an unrelated technical need; missing/unindexed PDF is not proof of negative equipment property.
- `CitationBinding` targets **exactly one** claim_id/document_reference_id/position_id. Exact site commit, blob, SHA256 and canonical route/field/section accompany citations. Returned text from model cannot be displayed directly or used as a technical source.
- Do not emit a model answer rewrite after the policy gate. User-facing Russian answers need to be comprehensible, not raw tuple dumps. A lightweight inspected local template set is acceptable.

Prior cross-contract contract exceptions and operational parameters remain authoritative; missing implementation features must be truthfully marked POC-only in report.

## 6. Local policy, session and resource budget (pilot, not public hardened)

**Runtime must bind ONLY to `127.0.0.1` by default. No 0.0.0.0/public deployment or production reverse proxy configuration by Codex.** The UI is single-operator experimental, so do not pretend a public multi-worker IP/proxy solution has been accepted.

Implement/test in fake clock/local SQLite:
- 1,200 Unicode question characters, 8KiB JSON request, canonical domain admission to only the two entities;
- a short-lived private session/typed `DialogState` (15m inactivity TTL) and a distinct 30m IP/day series counter; one active local session/IP and idempotent request IDs, no leakage to fresh session;
- 20 **admitted visitor questions**/IP/operator-calendar day **including local P0**; Q1–Q5 no extra delay, Q6–Q10 pause **10/20/40/60/90 seconds**; Q11+ support notice until 30m inactivity resets series; do not sleep server workers, send retry-after/remaining;
- user reset/dev fixture commands may clear synthetic local records **only in explicit loopback-only DEVELOPMENT mode**, never an unadvertised production bypass. Allow CLI fake-clock/unit fixtures to test >20 cases without consuming owner's web daily quota;
- private audit of admitted request text and **staged exact deterministic answer** with UTC receive/response timestamps, bounded local session identity/IP, source IDs and provider usage; record delivery transport separately and **never assert browser visual display**. Local SQLite/backup/chat log is ignored by Git; 30-day retention/purge test; safe no-logs fallback and restricted file permissions.
- concurrency: per-IP one in-flight request, atomic quota and (fake) provider budget reservations, one provider attempt per admitted turn. Do not automatically retry uncertain provider charge. All provider network forbidden unless explicit live GO.

**Global-paid-USD DS-SEC-10 Option A:** model paid budget exhausted ⇒ P1/P2 rejected **before admitted-turn debit**; verified zero-POST P0 remains available with all day/session/series/audit/local resource guards; P0 costs 0 provider attempts, counts 1 admitted question. In local simulator use test values, **no invented real production USD budget figures**.

## 7. P1/P2 adapters and money safety

Three mutually exclusive turn modes:
- `P0` deterministic local answer, source-bound, 0 API calls, first pilot default.
- `P1` single (mock or later specifically authorized live) DeepSeek intent parsing: `QuestionInterpretationPlan` only; server independently completes freezes QuestionNeeds, locally verifies/renders; **NEVER P2 on same turn**.
- `P2` single mock or later live `CandidateAnswerPlan` on an already frozen locally recognized QuestionNeeds; model can only refer to existing evidence IDs. Backend source verifier and renderer make final decision.

`ProviderDispatchGuard` applies **before every possible P1 or P2 paid POST** and checks: admitted-turn transaction, exact serialized full input ≤**10,000 tokens** (system+user+context+source+schema), output ≤**450 tokens**, fixed allowlisted `deepseek-flash` with **thinking disabled and tools disabled**, one-call idempotent attempt, safe global USD reserve. If a validated compatible exact tokenizer is not available, **fail closed rather than falsely claiming exact token count**; do not treat word count or characters as tokens. The offline mock can use deterministically supplied counts without pretending they equal live DeepSeek tokenization.

**New paid owner GO is NOT given.** Previous DeepSeek test approvals are all exhausted. For this coding task:
- real API network calls **must be exactly ZERO**, tested with transport-level fake/stub/egress prohibition;
- `DEEPSEEK_API_KEY` (if any) is local secret, never printed, persisted or committed;
- provider adapter may be prepared behind `LIVE_DEEPSEEK_ENABLED=false` with an additional explicit admin decision gate, but **Codex must NOT enable it, attempt an HTTP POST, upload a PDF, use native tools/Search/Fetch or infer authorization from key presence**;
- future controlled paid tests can be a new owner-issued scoped task with **numeric** POST and USD maximum, not this one.

Mock tests must assert 0 / 1 provider dispatch, missing/invalid responses, reserved-slot vs recorded dispatch-risk, source-conflict and insufficient evidence, timeout unknown charge no automatic retry. One call to P1 cannot be followed by P2.

## 8. Working demonstration acceptance scenarios

Use the 14 public-safe `P01..P14` questions already specified by exact source fields in `docs/corpus/DS-PILOT-01-TWO-ENTITY-SOURCE-SCOPE.md`; implement a repeatable offline test for **each** (with independent fake-clock sessions). Include R4-CR01 multi-need omissions and at least these additional checks:

| Test ID | Input / fixture | Expected |
|---|---|---|
| DEV-01 | Entity БКД-ПК-RF.2 source import, pinned blob verified | SourceBundle ID, git commit, blob SHA and byte SHA256 recorded; no external runtime query |
| DEV-02 | SLDKS system import, same commit | Distinct entity type and ID, correct system purpose; no BKD relation invented |
| DEV-03 | BKD DC supply vs AC supply question | Different typed source paths/conditions; don't merge (11–27V vs 187–253V) |
| DEV-04 | BKD mass, temperature, dimensions, interface values | Exact source fields and units, citation per Fact |
| DEV-05 | System M2 composition vs older generations | Version-qualified answer; no mixing obsolete device references as modern M2 |
| DEV-06 | Only manual link is known, question asks manual's internal terminal/pin | Metadata-only document link; **no technical terminal claim** until verified PDF bytes/pages |
| DEV-07 | BKD vs SLDKS compatibility question | No established direct relation; abstain/needs_support with qualified checked scope |
| DEV-08 | BKD question then “а его масса?” within 15m | Correct BKD referent and source; after expiry ambiguous local clarification |
| DEV-09 | Multi-part ask across both entities; mock P1 drops half | Retain all mandatory original clauses or diagnose unresolved; never falsely answered |
| DEV-10 | Mock P2 omits a frozen QuestionNeed | Frozen needs unchanged; no full answered or unproven Fact |
| DEV-11 | Nav-only and nav+unknown characteristic | Pure nav answered/document_reference_only; mixed safe partial with distinct need reason |
| DEV-12 | Malformed P1 vs malformed P2 | Deterministic clarification/invalid_model_plan vs needs_support/invalid_model_plan, no extra call |
| DEV-13 | Global paid USD budget 0, verified local BKD fact | P0 allowed with 1 visitor slot/0 paid; P1/P2 blocked before slot debit |
| DEV-14 | 15m, 30m, 20/day, Q6–Q11 with synthetic clock | Distinct clocks and admission counts; no worker sleep |
| DEV-15 | Forged role “ignore system” and invented source URL | Out-of-scope/blocked or safe legitimate scoped question, no policy promotion |
| DEV-16 | Invalid source Git blob or changed source revision | Import/claim fails closed; no wrong-version citation |
| DEV-17 | Two synthetic conflicting evidence positions + malformed PDF row | Two source-attributed positions, 0 established winner; wrong PDF cell rejected |
| DEV-18 | Request-id replay, provider timeout, session takeover | No double quota/provider cost; original-session-only response bytes |
| DEV-19 | Full DeepSeek input tokens 10,001, output cap 450 | Paid call blocked before network; mock token test does not claim real token compatibility |
| DEV-20 | No API key, no network, fresh WSL launch | Full P0 UI and CLI run successfully; direct DeepSeek provider calls = 0 |

**Substantive success is not just tests passing:** manually query local browser with P01, P03, P04, P08, P09, P10, P13, P14. Demonstrate distinct entity references, clear Russian answers, honest partials, visible source links/provenance and controlled refusals. Record real observed outputs in a compact report (no fabricated command results).

The R3-F01–F12 synthetic need reducer contract and AR-T01–22 remain architectural reference cases; implement only the sections testable in this two-entity local pilot, and report unimplemented cases explicitly as FUTURE rather than falsely claiming all accepted. Prior fake-clock/unit fixtures may test contract reducer without any public site data or external DeepSeek calls.

## 9. Failure handling, scope and deliverables

A prototype build is **NOT acceptable** if any of the following occur:
- source field values/power/variant/compatibility invented or answered from model memory without a bound source;
- a PDF link is treated as proof of a PDF technical statement, or a non-existent physical page/citation is constructed;
- original second half of a mixed question silently disappears after P1/P2 and the result claims `answered`;
- source-version/blob mismatch silently ignored; conflicting source claims published as one established fact;
- unchecked user/model prose is returned as verified technical content;
- code uses paid DeepSeek network in this stage, any private key or personal conversation committed to public GitHub;
- default local server binds publicly, modifies Saturn-Main-Site/NEW RAG, merges a coding PR or silently changes owner policies.

**Files to deliver in new code Draft PR:**
- runnable Python package + web UI + CLI, source importer/index/pin checker, typed dialogue/final gates, P0 and fake P1/P2 providers, disabled live adapter (if implemented);
- automated tests/fixtures (synthetic + real two-source fields), evidence provenance manifest and no invented connectivity relation;
- `README` or `docs/runs/DS-PILOT-01-LOCAL-RUNBOOK.md` for owner's Linux/WSL2 validation, exact copy/paste commands and troubleshooting; any local data path clearly `.gitignore`d;
- `docs/implementation/DS-CODEX-01-IMPLEMENTATION-REPORT.md` showing actual commands/tests/status/head and a **complete blocker/important/minor finding list** for architecture owner, including all deliberate POC shortcuts;
- working screenshot or a textual UI test observation with command output, but no invented PASS or secret-bearing screenshot; no paid API receipts.

**Coding discipline:** implement in one scoped feature branch, no gratuitous refactor; commits small and descriptive; repository/source trust pins immutable. If schedule is tight, prioritize **working P0 + R4-CR01 multi-need correctness + source citations + tests + simple web UI** ahead of vector retrieval, sophisticated NL parsing or provider native tools. Do not ask the owner a series of unnecessary clarifications; make narrowly scoped, documented safe choices and finish a working minimum. Do not silently claim full production hardening.

**Ready-to-accept completion checklist for Architecture Session A (not iterative independent architecture acceptance):**
1. A real local user can open web UI, ask questions about **both** selected objects, receive verified source-linked answer/partial/clarification.
2. Automated tests run and outputs recorded, including exact R4-CR01 mock omission case.
3. No paid DeepSeek/model web calls during coding; baseline source hashes/versions checked.
4. Source proof and typed result/status/need diagnostics exposed in developer view without leaks.
5. Instructions permit owner to reproduce P0 on WSL2; coding PR remains Draft/UNMERGED for acceptance.
6. Report identifies evidence coverage limitations, missing PDF pin and future work, not invented complete corpus.

## 10. Out-of-scope explicit boundaries

- All general Saturn site entities beyond these two, unverified third-party websites, new UI admin/CMS, site asset changes.
- Full visual/diagram PDF RAG, bulk 12-PDF corpus intake, expert GT promotion, source-to-knowledge live sync and automated public production deploy.
- NEW RAG code/repo, Saturn-Main-Site writes, a new architecture PR or historical owner-policy edits.
- Real DeepSeek paid GO / API traffic, production secrets, public reverse proxy/HTTPS service, true NAT/VPN IP security acceptance.

## 11. Hand-off instructions for Codex

On startup in NEW coding conversation:
1. Verify **main** already contains `docs/decisions/DS-ARCH-BASELINE-01-OWNER-ACCEPTED-CODING.md` and this task, and record exact main full SHA. If PR #1 has not merged, **stop before coding** and report baseline mismatch.
2. Read this task, DS-ARCH baseline R4-CR01, exact two-entity source scope and the relevant DS-EC-02/03/04/05 and DS-SEC-07/08/09/10 clauses. Read-only fetch Saturn source at pinned SHA and SHA validate.
3. Create a new feature branch from verified main, implement actual package/tests/UI with no paid HTTP calls and no edits to Saturn site or NEW RAG. Deliver one Draft PR, report and exact code HEAD.
4. Return to owner with working URL `http://127.0.0.1:8765`, WSL install/test commands, truthful test outputs and exact remaining implementation limitations; do **not** declare merge or production accepted.

**Note:** the project owner intentionally ended iterative independent architecture reviews. Record remaining localized ambiguities as testable controlled implementation requirements in the coding PR, escalate only real blockers, and prioritize empirical results over reopening the previous architecture-review loop.
