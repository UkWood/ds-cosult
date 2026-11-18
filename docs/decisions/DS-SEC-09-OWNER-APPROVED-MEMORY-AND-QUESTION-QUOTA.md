# DS-SEC-09 — Owner-Approved Dialogue Memory Expiry and Daily Question Accounting

**Date:** 2026-11-18  
**Status:** **OWNER ACCEPTED — TWO PREVIOUSLY OPEN DECISIONS RESOLVED / NO CODE GO**  
**Owner statement:** «Вопросы 1,2 согласовано. Делай следующий этап.»  
**Supersedes:** the two unresolved questions in `DS-EC-04` review (`MEM-REVIEW-01` and `MEM-REVIEW-02`), and the **billable-request-only** interpretation of the visitor-facing daily quota in `DS-SEC-07`. The earlier record remains valid history; this decision is authoritative for implementation.

**Later binding owner amendment DS-SEC-10 (2026-11-18):** The reference below to `global budget unavailable` as a blocked request applies to **paid P1/P2 only**. When global DeepSeek-paid USD budget is exhausted, verified **zero-provider P0** remains eligible for admission, counting exactly one of 20 visitor questions/day and obeying all IP/session/series/CPU/audit limits. No model POST or paid-tool call is permitted in that P0 route. See `docs/decisions/DS-SEC-10-OWNER-APPROVED-PAID-BUDGET-BREAKER-LOCAL-P0.md`. Historical decision text below is preserved.

## Decision A — 15-minute active technical memory expiry

After **15 minutes of genuine visitor inactivity**, the anonymous IP session lease expires and its **active technical DialogState is invalidated**. A later visit from the same cookie begins a **new empty technical context** after successful IP-lease admission; former entity focus, `first/second` comparison anchors, pending clarifications and fact handles are **not silently restored**. This protects different physical people using the same shared IP.

The following **do not expire at 15 minutes** merely because technical memory was cleared:
- IP-based **30-minute inactivity** progressive question series and its ordinal/cooldown;
- IP-based **20 accepted visitor questions per operator-calendar day** quota;
- independent provider-attempt and monetary budget accounting;
- restricted, staff-only **30-day** audit records of questions, actual final replies, IP and UTC timestamps.

An active provider POST that began before 15 minutes must remain exclusively fenced through response/timeout reconciliation; do not release the IP slot or expose its reply to a later anonymous session during an unresolved in-flight attempt. Exact idle-clock/lease fencing details require offline tests.

## Decision B — every accepted visitor question consumes the daily 20-question allowance

The visitor-facing limit is now **20 accepted questions per canonical IP per operator-configured calendar day**, whether the answer is generated locally, from an approved source-bound cache, by template, or with **one** DeepSeek paid Chat Completion.

**Separate accounting dimensions (no double spending):**

1. `visitor_turns_accepted_ip_day` — counts **each admitted in-domain visitor question once** before substantive processing regardless of zero/one provider call, with a unique idempotency key. A real accepted turn may end answered, partial, clarification, needs_support or processing_error: it still consumes a user question slot once admitted.
2. `provider_post_attempts_ip_day` — counts **each attempted billable model POST**, separately, before dispatch. Requests with unknown charge outcome stay counted; **no automatic retries**. The initial runtime permits **0 or 1** model POST per accepted visitor turn, so this count cannot exceed the admitted-turn count during normal single-call operation. If an exceptional infrastructure path could attempt a second POST, it is forbidden under the one-call contract.
3. `cost_reservations_and_reconciled_usage` — independent operator-global daily/monthly USD budget (amount remains operator-configurable), reserved conservatively before API dispatch; unused reservation released only when reliable provider usage is known.

**A blocked/invalid request** (overlong, quota-full, cooldown, same-IP other session, out-of-domain/policy-blocked, **global paid budget unavailable for a required P1/P2 route; DS-SEC-10 permits verified P0**) does **not** count as an accepted visitor question and cannot initiate a model POST. It may generate a bounded security log event and a separate anti-abuse counter. Define a request as **admitted** only after server-side IP ownership, question body and scope, daily/series quota and atomic request admission checks pass; this prevents counting user clicks that cannot proceed.

**For quota exhaustion:** Question 20 may be admitted when 19 prior accepted questions are recorded. Subsequent question 21 is rejected before any model call, with a static notice and verified support contacts; chatbot input is unavailable **until configured operator-calendar-day reset**, regardless of session-cookie rotation or 30-minute series reset. No registration required. Multiple tabs or client retries sharing the same idempotency key cannot consume two user slots or cause repeated charged model POSTs.

**Known limitation:** visitors can change IP/VPN/IPv6, multiple humans may share a corporate NAT; global USD budget guard and abuse controls remain essential. Neither IP nor cookie proves person identity.

## Updated implementation acceptance conditions

- 20 accepted turns with all local zero-cost replies => 21st blocked at daily quota, **provider calls remain 0**.
- 9 local + 11 model-backed accepted turns => exactly **20 visitor slots**, **11 provider attempts** (if each model call dispatched), and 21st blocked.
- A repeated request idempotency key or overlapping tabs must not consume extra accepted turns or extra charged POSTs.
- A rejected overlength question, cooldown violation, out-of-scope goal-hijack request and busy IP lease do not consume a visitor slot.
- Crash/timeout after admission: accepted turn remains counted once even if no final answer is delivered; provider attempt separately retained if dispatch occurred; report a clear technical error and avoid automatic replay.
- 15-minute idle session expiry clears current technical memory while preserving 30-minute IP series and daily count, with no cross-session transcript access.
- Calendar reset uses an explicitly configured IANA timezone, not automatically UTC or visitor browser timezone. The actual operator timezone is **not yet provided**.

## Documents to reconcile

- `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md` — authoritative daily-quota line and accounting invariants.
- `docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md`, `docs/security/DS-SEC-06-IP-LEASE-DAILY-LOCKOUT-AUDIT-PROPOSAL.md` — refresh earlier proposal interpretations.
- `docs/architecture/DS-EC-01-ENTITY-CENTRIC-VERIFIABLE-RAG-REFERENCE.md`, `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md`, `docs/architecture/DS-EC-04-TYPED-DIALOGUE-MEMORY-ANAPHORA-CORRECTIONS.md` and respective internal reviews — resolved pending decisions and acceptance tests.
- Project state/history — append-only owner decision and later contract scope, never rewrite historical trial results.

**All other owner-approved policies remain:** strict Saturn domain, explicit `Не выдумывай недостающие технические характеристики.`, trusted injection-free operator site/PDF, complete provider input <=10,000 tokens, output <=450, max 1,200 Unicode chars per user question/8KiB body, 0/1 paid provider call per turn, one active anonymous session per IP, 15m IP lease, 30m progressive-series reset, Q1-5 without artificial wait, Q6-10 cooldowns, Q11+ support, private full IP/Q&A audit with 30-day retention, global daily/monthly spend circuit breaker, no arbitrary visitor paid tools.

**Governance:** this owner approval authorizes documenting architecture decisions only, NOT implementation DS-02, new DeepSeek API attempts (DS-QV-01 GO exhausted 6/6), production, Merge, Corpus Freeze, changes to NEW RAG or writes to Saturn-Main-Site (READ-ONLY).
