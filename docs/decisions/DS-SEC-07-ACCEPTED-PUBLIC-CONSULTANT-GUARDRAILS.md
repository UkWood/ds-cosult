# DS-SEC-07 — Final Owner Approval of Visitor Security, Quotas and Audit Defaults

**Recorded:** 2026-11-18  
**Status:** **OWNER ACCEPTED — ARCHITECTURAL IMPLEMENTATION REQUIREMENTS / NO CODE OR DEPLOYMENT GO**  
**Owner wording:** «Все твои предложения принимаются. Зафиксируй их, для реализации в рамках проекта. Сейчас возвращаемся к архитектуре Entity-Centric RAG с проверяемыми источниками, уже учитывая её эксплуатационную стоимость и защиту от злоупотреблений.»

## 1. Scope and supersession

This approval accepts the previously proposed controls and numerical **pilot defaults** from:
- `docs/decisions/DS-SEC-01-SYSTEM-NON-FABRICATION-RULE.md` — explicit `Не выдумывай недостающие технические характеристики.`.
- `docs/security/DS-SEC-02-DIRECT-VISITOR-GOAL-HIJACKING-THREAT-MODEL.md` — direct visitor-message attacks only; trusted website/PDF deemed injection-free.
- `docs/decisions/DS-SEC-03-SCOPE-AND-RESOURCE-BOUNDARIES.md` — strict Saturn-only technical competence, no general-chat goal override.
- `docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md` — original numerical pilot proposal.
- `docs/decisions/DS-SEC-05-ANONYMOUS-IP-LOCK-DAILY-LIMIT-LOGGING.md` — owner-required anonymous access, one active session/IP, daily chat lockout, IP/Q&A logging.
- `docs/security/DS-SEC-06-IP-LEASE-DAILY-LOCKOUT-AUDIT-PROPOSAL.md` — technical implementation proposal, including 30-day encrypted private raw logs.

**Owner amendment DS-SEC-10 effective 2026-11-18:** Global **paid-provider USD** exhaustion blocks all new P1/P2 DeepSeek calls, but **allows verified zero-provider P0** within already accepted IP, 20/day, series/cooldown, CPU/concurrency, source-proof and private-audit protections. A paid-route budget preflight denial consumes no accepted visitor question. This resolves R1-CR05; see `docs/decisions/DS-SEC-10-OWNER-APPROVED-PAID-BUDGET-BREAKER-LOCAL-P0.md`. It does **not** override independent non-monetary infrastructure/safety circuit breakers.

**Owner amendment DS-SEC-09 effective 2026-11-18:** The previous 20 *billable provider POSTs per IP/day* definition is superseded by **20 admitted visitor questions per IP/operator-calendar day**; every locally rendered or cached answered question counts as one admitted turn, while paid POST attempts and monetary spending are tracked separately. Active technical dialogue memory is cleared at 15-minute idle IP-lease expiry even for a returning cookie; IP-based 30-minute question series and daily quota survive. Normative decision: `docs/decisions/DS-SEC-09-OWNER-APPROVED-MEMORY-AND-QUESTION-QUOTA.md`.

**Owner amendment effective 2026-11-18:** `docs/decisions/DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md` supersedes the original **3,000 full LLM input-token maximum** with **10,000 total input tokens**. This table and budget-gate rules below have been updated to the current 10,000 cap. The original owner acceptance quoted above is preserved as historical evidence; all unrelated requirements remain unchanged.

**Where proposals conflict**, this decision is authoritative. In particular, **20 questions per canonical IP per operator-configured calendar day**, **not** 20 per cookie/session over a rolling 24-hour period. The owner's latest acceptance supersedes the earlier unapproved status of these numerics; old proposal documents are retained for traceability, not reinterpreted as current rejection.

## 2. Approved pilot configuration

| Policy key | Approved initial value |
|---|---|
| Public visitor login | **NONE**: no registration, password or authorization |
| Consultant competence | **Strict Saturn technical domain only**; out-of-scope requests receive a brief fixed, polite redirect |
| System non-fabrication | Explicit Russian rule `Не выдумывай недостающие технические характеристики.` |
| Question text cap | **1,200 Unicode characters** per visitor question, server-validated |
| HTTP JSON body cap | **8 KiB** before JSON parsing |
| Full LLM input/context cap | **10,000 tokens total (hard maximum, not typical prompt size)** INCLUDING system policy, current user question, compact dialogue state and retrieved trusted source evidence |
| Output cap | **450 generated tokens** server-set `max_tokens` |
| Concurrency | **One in-flight LLM request per canonical IP/anonymous session** |
| Session ownership | **One active anonymous session per canonical external IP** |
| Anonymous session lease idle expiry | **15 minutes** inactivity; old session's chat private, not transferred to later session |
| Series reset | **30 minutes** idle since last accepted question; series counter stored server-side and attached to IP, not bypassed by new cookie |
| Questions 1–5 per series | **No added artificial delay**, normal other guards remain |
| Question 6–10 cooldown after previous accepted request | **10 / 20 / 40 / 60 / 90 seconds** respectively, backend timer |
| Question 11+ same continuous series | **No DeepSeek call**, static support handoff; series cannot be reset by visitor role instruction |
| Daily quota | **20 accepted visitor questions per canonical IP per operator-calendar day**, including locally rendered/cached replies; actual billable provider POST attempts counted independently and limited to at most one per accepted turn (not per browser cookie) |
| Daily exhaustion | **Chat submit disabled until configured next day-reset timestamp**; no paid model request; static notice and verified support contact |
| Daily reset | **Fixed calendar day** in **site-operator-configured time zone**, exact IANA zone **must be configured before deployment** |
| Monetary safety | **Global operator-configured daily and monthly DeepSeek-paid USD budgets**; fail-closed P1/P2 provider POST admission and cost reservation on insufficient funds; **source-verified P0 stays available** under full IP/day/series/CPU/security/audit guards, unless a separate non-monetary safety breaker denies it (DS-SEC-10) |
| Source access | Trusted operator-approved Saturn site/PDF only, no arbitrary visitor URLs, uploads, native paid web search/file tools or tool side effects in public chatbot mode unless separately approved |
| Logs | **Every accepted visitor question + actual final user-visible answer**, server UTC timestamps, canonical client IP, session/request pseudonymous correlator, reason, source snapshot, token counts/estimated cost; denied requests produce bounded events |
| Raw private log retention | **30 days**, automatic expiry/deletion incl. retention controls for backups where applicable, subject to legal review and operator needs |
| Security of logs | Strict staff-only access, encryption at rest/in transit, no public GitHub transcripts/IP, no API keys/cookies/reasoning/system secrets |
| Visitor-facing notice | Applicable privacy notice, data use purposes/basis, access/retention and support contacts reviewed before public deployment |

## 3. Invariants and guard implementation

1. Visitor IP must be determined from direct connection or a **trusted configured reverse proxy chain**, never a forged public `X-Forwarded-For` header. Canonicalize IPv4/IPv6; protect IP-based storage keys using keyed digest and keep actual IP in encrypted audit store.
2. Anonymous server-owned `HttpOnly Secure SameSite` cookie identifies a session, but the **daily count and continuous series bind to canonical IP**, not to the cookie. Multiple tabs with same cookie may view **only their own session**; different cookie at same IP must be blocked while lease active and must not see another visitor's chat. One request at a time.
3. Session lease expiry or explicit end-session does **not** reset daily quota or continuous-series timer. Accepted local/template/cached replies **do** consume one visitor-question slot; a blocked/invalid request consumes no accepted-question slot but may increment independent abuse counters. Provider attempts have a **separate** counter; an attempted POST counts even on uncertain timeout. One accepted turn must never cause two paid provider POSTs.
4. Every quota, lease, concurrency and budget check is **atomic in shared backend state** before external API dispatch; fail closed if accounting/lock store unavailable.
5. For cooldown return server-generated `429` and `Retry-After` without sleeping in the backend or calling DeepSeek; for quota exhaustion show exact configured reset time and verified contact links; do not auto-email company support.
6. Reserve conservative per-request maximum cost for **full input 10,000 / output 450 token envelope** and any separately approved tools. Release unused reserve only on validated provider usage. At the 2026-11-18 peak Flash rates used for model-only conservative reservation, 10,000 input cache-miss tokens plus 450 output tokens are **$0.00354 per call** (previous 3,000-input case $0.00144); reserve before POST, with margin for tokenizer/pricing uncertainty as required. Cost estimate is not a provider-enforced dollar cap; reconcile billing externally.
7. System role, source scope, retrieval, policy gate, claim verification and final citations are **backend-owned**. Visitors cannot promote instructions or proposed technical facts into trusted corpus or user-independent system role.
8. IP locking prevents simultaneous sessions from a *network address*, **not** unique humans. NAT/shared office IPs and VPN/IPv6 rotation are known limitations. A global budget, mild network abuse controls and IP-aware analytics remain required. Do not claim prevention of all sybil attacks.
9. Logging full IP and Q/A can involve personal data; maintain approved purpose/legal basis, visitor notice, access control, deletion rights/handling and data-transfer analysis as applicable. **30 days is a product retention default, not legal permission to collect indiscriminately**. Privacy/security review remains a launch gate.
10. Each accepted visitor question (including local/template/cache) consumes exactly one daily question slot; independent provider POST attempts and cost reservations are counted separately. Per-request idempotency prevents replay/double counting; source-version binding applies also to cached answers.

## 4. Deployment-only administrative configuration remains unset

The owner accepted the **requirement to configure**, not guessed values, for:
- IANA organization timezone controlling calendar-day reset;
- company support phone/email sourced from official, trusted config;
- global USD budget per day and month, alarm delivery and incident response contacts;
- trusted proxy/CND addresses and the real hosting topology;
- privacy notice and legally reviewed purpose/basis/recipient details, approved staff roles;
- encryption keys, logs DB location, deletion/backups.

**No hardcoded invented organizational phone/email, dollar allowance, timezone, source revision or production connection string.** These inputs must be supplied/approved before launch.

## 5. Implementation and acceptance boundaries

Architectural acceptance here is **not authorization for coding DS-02, hosting, production, new PR, or new paid DeepSeek calls**. Scope remains current open Draft PR #1 documentation only.

A future coding assignment must carry these accepted requirements, with offline tests first for IP concurrency/races, daily reset, series Q6–Q11, log retention, budget reservations, bad proxy headers, malicious role text, session visibility, known vs missing source facts and 10,001-token overflow (10,000 boundary accepted when otherwise valid). Private IP/Q&A and hidden benchmark Core/GT must **never** be copied to this public repo.

**DS-QV-01: 6/6 authorized requests used, 0 remain**. NEW RAG remains independent and `Saturn-Main-Site` read-only.

**Next now:** Architecture Session returns to **Entity-Centric RAG with verifiable sources**, incorporating these costs and controls into design discussions; separate owner GO before implementation.
