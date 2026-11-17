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

**Where proposals conflict**, this decision is authoritative. In particular, **20 questions per canonical IP per operator-configured calendar day**, **not** 20 per cookie/session over a rolling 24-hour period. The owner's latest acceptance supersedes the earlier unapproved status of these numerics; old proposal documents are retained for traceability, not reinterpreted as current rejection.

## 2. Approved pilot configuration

| Policy key | Approved initial value |
|---|---|
| Public visitor login | **NONE**: no registration, password or authorization |
| Consultant competence | **Strict Saturn technical domain only**; out-of-scope requests receive a brief fixed, polite redirect |
| System non-fabrication | Explicit Russian rule `Не выдумывай недостающие технические характеристики.` |
| Question text cap | **1,200 Unicode characters** per visitor question, server-validated |
| HTTP JSON body cap | **8 KiB** before JSON parsing |
| Full LLM input/context cap | **3,000 tokens total** INCLUDING system policy, current user question, compact dialogue state and retrieved trusted source evidence |
| Output cap | **450 generated tokens** server-set `max_tokens` |
| Concurrency | **One in-flight LLM request per canonical IP/anonymous session** |
| Session ownership | **One active anonymous session per canonical external IP** |
| Anonymous session lease idle expiry | **15 minutes** inactivity; old session's chat private, not transferred to later session |
| Series reset | **30 minutes** idle since last accepted question; series counter stored server-side and attached to IP, not bypassed by new cookie |
| Questions 1–5 per series | **No added artificial delay**, normal other guards remain |
| Question 6–10 cooldown after previous accepted request | **10 / 20 / 40 / 60 / 90 seconds** respectively, backend timer |
| Question 11+ same continuous series | **No DeepSeek call**, static support handoff; series cannot be reset by visitor role instruction |
| Daily quota | **20 accepted billable model POST attempts per canonical IP per operator-calendar day** (not per browser cookie) |
| Daily exhaustion | **Chat submit disabled until configured next day-reset timestamp**; no paid model request; static notice and verified support contact |
| Daily reset | **Fixed calendar day** in **site-operator-configured time zone**, exact IANA zone **must be configured before deployment** |
| Monetary safety | **Global operator-configured daily and monthly budgets**, conservative cost reservation, concurrency ceiling, alert thresholds, global fail-closed circuit breaker |
| Source access | Trusted operator-approved Saturn site/PDF only, no arbitrary visitor URLs, uploads, native paid web search/file tools or tool side effects in public chatbot mode unless separately approved |
| Logs | **Every accepted visitor question + actual final user-visible answer**, server UTC timestamps, canonical client IP, session/request pseudonymous correlator, reason, source snapshot, token counts/estimated cost; denied requests produce bounded events |
| Raw private log retention | **30 days**, automatic expiry/deletion incl. retention controls for backups where applicable, subject to legal review and operator needs |
| Security of logs | Strict staff-only access, encryption at rest/in transit, no public GitHub transcripts/IP, no API keys/cookies/reasoning/system secrets |
| Visitor-facing notice | Applicable privacy notice, data use purposes/basis, access/retention and support contacts reviewed before public deployment |

## 3. Invariants and guard implementation

1. Visitor IP must be determined from direct connection or a **trusted configured reverse proxy chain**, never a forged public `X-Forwarded-For` header. Canonicalize IPv4/IPv6; protect IP-based storage keys using keyed digest and keep actual IP in encrypted audit store.
2. Anonymous server-owned `HttpOnly Secure SameSite` cookie identifies a session, but the **daily count and continuous series bind to canonical IP**, not to the cookie. Multiple tabs with same cookie may view **only their own session**; different cookie at same IP must be blocked while lease active and must not see another visitor's chat. One request at a time.
3. Session lease expiry or explicit end-session does **not** reset daily quota or continuous-series timer. Requests that never reach paid provider do not increment billable quota but may increment independent abuse counters; timeout after attempted POST counts as a consumed attempt.
4. Every quota, lease, concurrency and budget check is **atomic in shared backend state** before external API dispatch; fail closed if accounting/lock store unavailable.
5. For cooldown return server-generated `429` and `Retry-After` without sleeping in the backend or calling DeepSeek; for quota exhaustion show exact configured reset time and verified contact links; do not auto-email company support.
6. Reserve conservative per-request maximum cost for **full input 3,000 / output 450 token envelope** and any separately approved tools. Release unused reserve only on validated provider usage. Cost estimate is not a provider-enforced dollar cap; reconcile billing externally.
7. System role, source scope, retrieval, policy gate, claim verification and final citations are **backend-owned**. Visitors cannot promote instructions or proposed technical facts into trusted corpus or user-independent system role.
8. IP locking prevents simultaneous sessions from a *network address*, **not** unique humans. NAT/shared office IPs and VPN/IPv6 rotation are known limitations. A global budget, mild network abuse controls and IP-aware analytics remain required. Do not claim prevention of all sybil attacks.
9. Logging full IP and Q/A can involve personal data; maintain approved purpose/legal basis, visitor notice, access control, deletion rights/handling and data-transfer analysis as applicable. **30 days is a product retention default, not legal permission to collect indiscriminately**. Privacy/security review remains a launch gate.
10. Free or cached responses must not corrupt accounting or source-version binding. Exact definition of `accepted billable model POST` versus deterministic local response must be reflected in a consistent UI and counters.

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

A future coding assignment must carry these accepted requirements, with offline tests first for IP concurrency/races, daily reset, series Q6–Q11, log retention, budget reservations, bad proxy headers, malicious role text, session visibility, known vs missing source facts and 3,000-token overflow. Private IP/Q&A and hidden benchmark Core/GT must **never** be copied to this public repo.

**DS-QV-01: 6/6 authorized requests used, 0 remain**. NEW RAG remains independent and `Saturn-Main-Site` read-only.

**Next now:** Architecture Session returns to **Entity-Centric RAG with verifiable sources**, incorporating these costs and controls into design discussions; separate owner GO before implementation.
