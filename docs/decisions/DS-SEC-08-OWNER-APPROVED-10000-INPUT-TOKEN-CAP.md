# DS-SEC-08 — Owner Amendment: Full LLM Input Context Ceiling 10,000 Tokens

**Recorded:** 2026-11-18
**Later owner decision:** DS-SEC-09 takes precedence ONLY for 15-minute active-memory interpretation and **20 accepted visitor questions/IP/operator calendar day including zero-model local answers**. The original 20 billable-provider wording below is marked historical rather than silently rewritten; the 10,000-token input cap and all other approved boundaries remain effective.  
**Status:** **OWNER ACCEPTED — AMENDS DS-SEC-07 (SINGLE PARAMETER)**  
**Owner instruction (verbatim):** «Считаю необходимо расширить лимит входных токенов до 10000. Внимательно скорректируй советующие документы в связи с этим изменением.»

## Decision, scope and precedence

The owner **replaces the approved maximum full input context of 3,000 tokens with 10,000 tokens** for the public DS-консультант's direct `deepseek-flash` API request. This applies to the **entire input**: system message, active visitor question, typed compact dialogue state, source-backed Entity/Fact/Relation material, citation/evidence excerpts, response schema instructions, message formatting overhead and any other input the provider counts. This **is not** a per-user-question, per-document or per-evidence allowance.

**Current rule (effective for future implementation): `MAX_LLM_INPUT_TOKENS = 10000`.** A request may be considerably shorter. Local retrieval must prioritize a minimal sufficient evidence packet; 10k is a hard safety/expense ceiling, **not** a required target or default to fill.

This newer owner directive **supersedes only** the `3000` input-token value in `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md`, its DS-SEC-04 proposal origins, and DS-EC-01/03 architectural drafts and checks. The old value was correctly approved earlier, and is retained as **historical context** in append-only project history and acceptance logs; it must not be presented as a current runtime requirement.

**Unchanged owner-accepted requirements**: visitor message <= 1,200 Unicode characters; HTTP JSON body <= 8 KiB; LLM output <= 450 tokens; zero-or-one API request per accepted visitor turn; Saturn-only technical scope; explicit system `Не выдумывай недостающие технические характеристики.`; trusted site/PDF sources; deterministic source-bound answer gate; one anonymous active session/IP and one in-flight; 15-minute idle IP lease; 30-minute idle series reset; no added cooldown Q1–5, 10/20/40/60/90s for Q6–10, Q11+ support handoff; 20 billable provider POST attempts/IP/organization calendar day **[HISTORICAL 2026-11-18 VALUE — SUPERSEDED BY DS-SEC-09: CURRENT HARD QUOTA IS 20 ACCEPTED VISITOR QUESTIONS/IP/OPERATOR CALENDAR DAY INCLUDING LOCAL P0; paid provider attempts and USD recorded separately]**; private 30-day visitor IP/question/answer audit; global daily/monthly spend breaker.

## Required backend behavior

1. Build context locally by progressive dossier levels and exact evidence needs, **avoid sending whole PDF or surplus history** merely because there is room.
2. Require **actual complete assembled provider input** to be measured by the model-compatible tokenizer before dispatch. An approximate character count or static sub-budget is not sufficient for a claimed 10k hard gate. If exact usage prediction is unavailable, apply a conservative local allowance/margin and stop below 10k until measurement can be validated against observed provider usage. Never knowingly exceed the cap.
3. Keep first-pass routine contexts as small as necessary. **Soft operating target at or below ~3,000 input tokens for ordinary/simple questions** is a cost optimization only; it is **not** a second blocking rule. Multi-entity comparisons, conflict citations or justified long PDF extracts may consume more, up to 10k.
4. When required evidence, qualifier or contradictory source does not fit 10k, return a safe partial/clarification/needs-support/error state rather than discard relevant technical conditions or exceed budget.
5. Recompute worst-case per-call reserved cost for the new 10k input maximum, **before** the paid API POST; budget check is server-owned, atomic, and fail-closed. Do not rely on cache-hit discounts, off-peak price, assumed provider refund, or model compliance.
6. Update tests: 10,000 counted input tokens at the boundary (if the request is otherwise valid) should pass token-limit admission; **10,001** must be blocked pre-provider. Both input cap and output cap 450 are independently checked; also test that a 1,200-character question can still exceed the **total** context limit due to source evidence.
7. Exhausted DS-QV-01 paid GO **6/6** stays exhausted; this documentation decision does not authorize a new DeepSeek test, production deployment, implementation DS-02, Merge, Corpus Freeze or source changes.

## Conservative peak-rate expense recalculation (model-only, illustrative)

**DeepSeek official model prices checked 2026-11-18:** `deepseek-flash` peak **$0.30 per 1M input cache-miss tokens**, **$0.006 per 1M cache-hit tokens**, **$1.20 per 1M output tokens**. Verify rates again before real deployment; official page: https://api-docs.deepseek.com/quick_start/pricing/.

| Envelope (all input assumed cache MISS, full output) | Input USD | Output USD | Total USD |
|---|---:|---:|---:|
| Previous 3,000 input + 450 output | 0.000900 | 0.000540 | **0.001440** |
| **New 10,000 input + 450 output** | **0.003000** | **0.000540** | **0.003540** |

- **10 such fully budgeted calls**: `$0.03540`.
- **1,000 such calls**: `$3.54`; 1,000 visitors each doing 10 such calls: `$35.40`.
- At these fixed rates and caps, the conservative **per-call budget reservation increases 2.4583×** relative to the earlier 3k cap. This is a **model-token reservation example**, not an enforceable provider charge ceiling; prices/usage and extra tools, if separately authorized, could change.
- Model API paid native tools/web/files remain disabled in the initial public runtime; if later enabled, their charges require a distinct approved budget contract.
- The global *daily/monthly USD* thresholds are still **owner/operator-configured and unset**. Do not invent values. Provider actual billing remains unverified; maintain usage reconciliation.

## Documents affected and traceability

- `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md` — authoritative table, reservation and acceptance test.
- `docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md` — adjusted numeric proposal and cost examples (historical draft annotations maintained).
- `docs/security/DS-SEC-06-IP-LEASE-DAILY-LOCKOUT-AUDIT-PROPOSAL.md` — one-line cap summary amended.
- `docs/architecture/DS-EC-01-ENTITY-CENTRIC-VERIFIABLE-RAG-REFERENCE.md` — answer pipeline and source-packet cost.
- `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md` — entire-input token admission, illustrative allocation, cost and over-limit tests.
- `docs/architecture/DS-EC-02-03-DESIGN-CONSISTENCY-REVIEW.md` — current contract review updated, history noted.
- `docs/status/PROJECT_STATE.md` and `docs/history/ARCHITECTURE_LOG.md` — **append-only** supersession status, leaving old event records truthful.
- `docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md` — **no change needed** (data contracts do not prescribe an input token limit).

**Project separation:** `UkWood/ds-cosult` only, existing OPEN/DRAFT PR #1; `UkWood/Saturn-Main-Site` READ-ONLY; NEW RAG `UkWood/LLM-RAG-chat-bot` untouched.
