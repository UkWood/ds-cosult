# DS-SEC-04 — Public Consultant Input, Throttling and Budget Guardrails (Proposal)


**CURRENT APPROVAL UPDATE (2026-11-18):** The owner accepted the numerical **pilot defaults** and budget-guard architecture; see `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md`. Specifically the earlier *per-session rolling-24-hour* 20-request suggestion is **superseded** by the accepted **20 accepted visitor questions per canonical IP per configured operator-calendar day (including local/cached responses)**, with independent billable POST tracking. Exact timezone, organization USD budgets, contacts and privacy configuration must be supplied before deployment. Historical proposal text below is preserved, not binding where superseded.

**Recorded:** 2026-11-18  
**Status:** **ARCHITECTURE PROPOSAL FOR OWNER REVIEW — NOT NUMERICALLY APPROVED; NO IMPLEMENTATION OR PAID EXPERIMENT**  
**Accepted prerequisites:** DS-SEC-01 explicit `Не выдумывай` system rule; DS-SEC-03 strict technical competence scope + **required** question-length, progressive rate limiting and escalation-to-support capabilities.  
**Threat:** site visitor abuse of the **public chat endpoint** that could exhaust API tokens, provider account quota or available consultant service. Trusted site/PDF sources themselves are not injection threats.

## 1. Why progressive delays are not a spending cap

A user can open many sessions, rotate an anonymous cookie, use different networks, run parallel requests or submit one question with expensive hidden context. Per-session gradual backoff **improves normal UX and deters casual abuse**, but does not protect the service's total budget.

Need a **stack of independent server-owned limits** before any DeepSeek request:
1. Limit incoming body/string size and normalized message characters.
2. Cap total model input tokens **including fixed system instructions, structured state, retrieved dossier/quotes and previous turns**, not merely current user text.
3. Cap server-set `max_tokens` and tool fanout, prevent expensive model mode bypass via user fields.
4. Enforce **per-session** progressive cooldown and per-identity **daily quotas**.
5. Add abuse-level per-IP / network aggregation cautiously (NAT users share an IP), plus WAF/bot defense if needed; cookie alone is resettable.
6. Enforce independent **global daily/monthly spend envelopes and provider-call concurrency limits**. Fail closed when budget cannot be reserved.
7. Track true usage from provider responses and independently reconcile invoices. Budget predictions are not provider-enforced financial limits.

OWASP: LLM10:2025 Unbounded Consumption; API4:2023 Unrestricted Resource Consumption; NIST API Protection guidance.

**CURRENT REVISION 2026-11-18 — DS-SEC-08 owner-approved input ceiling:** All active input-context references below now use **10,000 tokens total**. This is a **maximum**, not a prompt-length target; keep typical simple questions close to their minimal evidence packet (often ≤3,000 input tokens). At fixed 2026-11-18 peak Flash rates, **10,000 cache-miss input + 450 output tokens = $0.00354 model-only reserved cost**. This overrides the historical 3,000-token approval; see `docs/decisions/DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md`. Other accepted site/abuse controls from DS-SEC-07 are unchanged. Original proposal text remains as an explanatory design baseline where not superseded.

## 2. Original pilot numeric proposal — now owner-accepted as amended by DS-SEC-07 and DS-SEC-08

| Guard | Initial candidate | Why |
|---|---|---|
| New visitor question | **max 1,200 Unicode characters**, also cap request bytes | Sufficient for typical technical question; prevent giant pasted messages |
| HTTP JSON body | **max 8 KiB** before parsing; enforce schema and Unicode control-character rules | No arbitrarily large payloads despite character cap |
| Total request context to LLM | **max 10,000 input tokens** including system + trusted RAG evidence + compact state | Actual token/cost boundary rather than characters alone; subject to future real-corpus quality calibration |
| Model answer generation | **server-set `max_tokens=450`**, optional shorter by task class | Prevent expensive long output; monitor `finish_reason=length` for excessive truncation |
| Concurrent inference per visitor | **1** | Prevent tab races, duplicate clicks and simultaneous expensive requests |
| Anonymous visitor sustained daily quota | **20 accepted visitor questions per canonical IP/operator-calendar day**, including local/cached answers; paid provider attempts separate (DS-SEC-09 owner approved) | Session reset cannot imply unlimited daily requests; calibrate for legitimate visitor needs |
| Active question series reset | **30 minutes after last accepted interaction**, provisional | Define what "подряд" means |
| Series question 1–5 | **0 added cooldown**, provided every other guard passes | Owner-preferred normal conversation |
| Question 6 | **10s** after previous accepted request | Initial anti-burst friction |
| Question 7 | **20s** | Progressive delay |
| Question 8 | **40s** | Progressive delay |
| Question 9 | **60s** | Bounded increased delay |
| Question 10 | **90s** | Final permitted inference |
| Question 11+ in same series | **No DeepSeek call; static support phone/email**, until reset eligibility | Avoid prolonged paid repetitive conversations |
| Global pilot spend budget | **operator-configured, initially conservative; choose dollar value against traffic forecast before launch** | Do not invent company's affordability |
| Global concurrency/provider timeouts | **small bounded queue**, exact concurrency/timeout after load tests | Avoid DoS, provider escalation and fanout |
| Tool access | No arbitrary web/files/paid native tools from public chat until separately gated | Prevent hidden search/fetch charges |

In practical terms **"first five without limits" means no added temporal pause**, not no character, token, concurrency or global budget limits. Even normal visitor turns must pass all hard gates. These limits are now owner-approved for future implementation under DS-SEC-07/08, **but not yet performance-tested or deployed**.

## 3. Server-side acceptance algorithm (proposed)

When a visitor presses Send:

1. Server receives signed, random, opaque, HTTP-only `SameSite` session cookie; never trust browser's claimed `question_count`, `wait_seconds` or API role. Avoid fingerprinting. The IP/network signal is a supplementary abuse detector rather than the only user identity.
2. Before paid inference: enforce JSON size/schema, Unicode/character length, allowed technical-domain task and safe request normalization. Reject overlength with 413 or 422 and a human-readable character-limit message. Rejected invalid attempts are **not paid model requests**, but count toward an independent abuse counter to prevent cheap endpoint spam.
3. Resolve session history from backend storage (server-controlled), with immutable verified entity/source IDs and compact state. If the 10,000 input-token envelope would overflow, deterministically trim/rebuild conversation context and relevant trusted dossier within a declared evidence completeness policy; if critical evidence cannot fit, return a safe clarification/not-enough-context result instead of silently omitting necessary facts.
4. With an **atomic shared transaction** (e.g. Redis script or transactional datastore, not just frontend state) check session count, last accepted timestamp, required next allowable time, operator-calendar-day IP question quota, IP abuse threshold, global concurrency, remaining daily/monthly budgets. A user can submit from ten browser tabs; only one should receive approval.
5. If cooldown is not yet elapsed, return HTTP `429 Too Many Requests` and `Retry-After` with the remaining wait; **do not sleep on the server**, queue paid requests, or make DeepSeek calls. Do not automatically resend blocked requests; browser can display a countdown and user must retry. A rate-blocked request does not increment the accepted question count, but repeated rate-block attempts may trigger bot/abuse mitigation.
6. If the visitor would exceed the tenth accepted request in the current series, return a static `support_handoff` response **without calling DeepSeek**; use vetted company phone/email from server/site config, not model-generated contacts. Continued rejected messages do not reset series limits.
7. For an allowed call, atomically **reserve a conservative maximum possible cost** against global and daily budgets before any external API POST. Budget input estimate should include entire token envelope, output cap and any explicitly permitted paid tools. Initial example at **10,000 input/450 output** and known Flash peak `$0.30/M` input cache misses + `$1.20/M` output gives **$0.00354 per call** at those rates, not a hard financial guarantee (pricing, hidden tools and provider can change). Never assume prompt caching when reserving budget.
8. Mark one accepted attempt and exclusive inflight lease before API call (single-flight); no automatic retry if outcome of charge is uncertain. On response, verify model/usage, release unused reserve, reconcile estimated actual token spend. If timeout or incomplete accounting, hold a conservative reservation until safe reconciliation rather than instantly retrying.
9. Output must also pass server-side source/policy gate (DS-SEC-02) independent of LLM text. Log minimal redacted quota state and charge estimates; do not log raw user private text or provider secrets unnecessarily. Present a coherent user-facing error/support message.
10. Enforce a **global circuit breaker**: when the organizational daily/monthly budget is exhausted, all new paid visitor calls are rejected, including the first five free-of-delay turns; show support contacts or an availability notice. Consider alerts at configurable 50%, 80%, 100% budget utilization.

## 4. Session/identity evasion & usability

- A cookie can be deleted, and opening another private/incognito browser session resets a per-cookie count; accordingly **no single per-session algorithm is a robust adversarial spending cap**.
- NAT/proxies: many legitimate office visitors share one IP, so aggressive hard-IP quotas may unintentionally block real customers. Prefer a layered rate-limiter with per-session hard throttling, bounded per-network abuse flags, global quota and WAF signals. Use strict IP limits cautiously and store minimal data consistent with applicable privacy rules.
- If user legitimately asks 11+ technical questions in one series, static handoff is safe and can provide phone/e-mail plus the current answerable published documentation; no further paid inference. No auto-email to company support (avoids email abuse).
- Staff/support agents can have separate authenticated quotas if later approved; **do not** let visitor chat text like `я администратор` elevate identity.
- A customer should be able to navigate to a new Saturn product during a series without resetting quota. A legitimate correction is not a new visitor session.
- Potential performance optimisation: local deterministic responses to well-defined FAQs/no-corpus/generic UI navigation where safe; evidence-bound caching keyed by normalized question + pinned corpus revision + relevant entity ID and output policy. **Never cache across user-private contexts** or bypass citation/provenance validation.
- If higher model context is required for detailed PDFs, adjust input cap based on controlled quality testing. Do not simply allow unlimited documents in prompts.

## 5. Budget rough-order example (NOT a quote)

Using a **conservative peak** Flash cost of $0.30/M input tokens + $1.20/M output:
- At exactly 10,000 input + 450 output tokens: **$0.00354** hypothetical maximum under those fixed token rates; provider tool charges, pricing changes and invoice reconciliations are not included.
- 10 such allowed calls from one visitor could cost up to **$0.0354** at fixed rates.
- 1000 separate visitors each making 10 such calls could consume **$35.40** at fixed rates, despite per-visitor throttling.
- This is why an owner-configured **global budget with reservation and fail-closed logic** is vital in addition to five free-of-delay turns.

The previous 3,000 input + 450 output maximum was $0.00144 per call on the same fixed rates; the new worst-case model-token estimate is 2.4583× larger. Backend must check the entire assembled input with a compatible tokenizer (or conservative headroom) before dispatch and atomically reserve worst-case dollars. 10,000 is not a target; use the shortest source-sufficient packet. Actual average will vary: real questions, source context length, answer size and caching. Evaluate spending against logged `usage`, not only request count.

## 6. Acceptance scenarios (offline first)

**Valid requests:** five rapid short technical questions without artificial wait; real time quotas still apply; sixth after proper wait; legitimate change of entity; correct known fact, safe missing fact and bounded context preservation.

**Denied requests, no paid DeepSeek traffic:** over-1200-character question; 10,001 counted input tokens with no legal reduction to 10,000; >8 KiB body; total token envelope overflow; sixth submitted before wait; eleventh in continuous series; 21st in configured operator-calendar day; global budget depleted; too many concurrent same-session submissions; role spoof / fake admin demand to bypass budget.

**Adversarial concurrency/identity:** two tabs race to submit sixth request; ten parallel attempts in a new session; deletion of visitor cookie; one office network with many independent legitimate sessions; high-volume bot creating fresh sessions; stale server process and losing the quota backing store (fail closed); uncertain timeout must not be retried.

**Cost/telemetry:** preflight reservation worst-case, refund unused reserve only with verified usage, no phantom negative quota, alert and circuit breaker at configured budget threshold, no separate tool charges without explicit policy, safe handling of `finish_reason=length`.

**No paid test authorization:** DS-QV-01 is finished with 6/6 paid attempts. Draft DS-SEC-04 acceptance exercises may be implemented later offline with fake provider and deterministic clock, **only after independent owner approval**. Real DeepSeek calls need a separately bounded numeric GO.

## 7. Original pending decisions — superseded in part by DS-SEC-07/08

1. **RESOLVED:** owner approved **1,200 question characters**, **10,000 max total input tokens**, and **450 output tokens** as pilot defaults (DS-SEC-07/08).
2. Accept or adjust **30-minute inactivity reset** and **10/20/40/60/90s** waits for Q6–Q10, stop Q11+.
3. **RESOLVED in DS-SEC-07 + owner DS-SEC-09:** 20 accepted visitor questions (including local/cache) per canonical IP per operator-configured calendar day; separately count paid provider attempts, plus IP/NAT-aware protection; operator timezone and network configuration still required.
4. Set explicit **global daily and monthly budget** based on expected visits and affordability; ensure configurable kill-switch.
5. Choose storage for atomic quotas/reservations; ensure `retry-after`, frontend countdown, and static support handoff.
6. Decide which safe FAQ results can be answered deterministically or cached without losing evidence/source revision guarantees.

**No Merge / DS-02 / Production / Corpus Freeze / NEW RAG changes / Saturn site writes.**

## References

- OWASP LLM10:2025 Unbounded Consumption: https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/
- OWASP API4:2023 Unrestricted Resource Consumption: https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/
- DeepSeek Chat Completions: https://api-docs.deepseek.com/api/create-chat-completion/
- DeepSeek Models & Pricing: https://api-docs.deepseek.com/quick_start/pricing/
- NIST API Protection guidelines: https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=960213
