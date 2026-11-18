# DS-SEC-06 — Proposed Architecture: One Active Session per IP, Daily Lockout, Private Conversation Audit


**CURRENT APPROVAL UPDATE (2026-11-18):** Owner accepted the design defaults and implementation direction from this proposal: one active anonymous session per IP, 15-minute idle lease, fixed calendar-day 20 accepted visitor questions/IP including zero-call local/cache answers, complete private IP/Q&A audit with 30-day raw retention, and server-side atomic quota/budget controls. Binding record: `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md`. Deployment-specific timezone, organization global USD budget, trusted proxies, contact data and privacy review remain required. Original proposal text below preserved as rationale. No implementation authorized.

**Recorded:** 2026-11-18  
**Status:** **TECHNICAL DESIGN PROPOSAL / OWNER NUMERIC APPROVAL AND IMPLEMENTATION PENDING**  
**Accepted behavior:** `docs/decisions/DS-SEC-05-ANONYMOUS-IP-LOCK-DAILY-LIMIT-LOGGING.md`. Do not reinterpret the accepted IP-lock requirement as authenticated user tracking.

**LATEST OWNER APPROVAL (DS-SEC-08, 2026-11-18):** The complete LLM input cap is now **10,000 tokens**, superseding the original 3,000 figure. All per-IP limits, audit retention, cooldown and anonymous session policies remain unchanged. The budget reservation must be recalculated for 10,000 input + 450 output tokens, up to **$0.00354/call** at fixed current peak Flash token rates before cache discounts; not a provider invoice or hard dollar cap. This is a ceiling, not target prompt size.

## 1. Logical components (choice of technology open)

1. `VisitorIpResolver` — canonical client IP from network peer or verified trusted proxy chain; reject untrusted forwarded headers; normalize IPv4, IPv6 (including IPv4-mapped IPv6).
2. `AnonymousSessionManager` — random opaque HttpOnly Secure SameSite cookie `consult_session`; stores server-side random session ID; no registration/account.
3. `IpLeaseStore` — atomic key keyed by a server-secret HMAC of canonical IP, holding session-owner ID, lease expiry, last activity, and in-flight status. Raw IP must NOT be present in Redis key names. Full canonical IP can be encrypted and retained in **private audit store** for owner-authorized logging.
4. `DailyIpQuota` — fixed per-IP counters unrelated to the cookie and previous session lease. Owner-approved **20 admitted visitor questions / calendar day / canonical IP**, including locally rendered/cached responses; provider POST attempts counted separately (DS-SEC-09). Reset epoch fixed to site-operator timezone; output exact `resets_at` timestamp.
5. `SeriesCooldown` — separate per-IP continuous-series policy of 5 no added cooldown, Q6–Q10 progressive delay, Q11+ static support; idle reset 30m, owner-approved under DS-SEC-07. Avoid treating session cookie rotation as new "series".
6. `BudgetReservation` — independent global daily/monthly monetary envelopes, per-request token/context/output hard bounds and global concurrency. No model dispatch unless reservation is committed.
7. `ConversationAuditStore` — private DB records each accepted visitor's question, final rendered answer, two timestamps, canonical full IP, opaque pseudonymous session correlator, source snapshot ID, token costs, policy status and errors. Only designated staff access; no public website endpoint to retrieve by IP.
8. `StaticNoticeRenderer` — server-owned strings for `ip_busy`, `cooldown`, `day_quota_reached`, `series_limit`, `global_budget_stop`, and verified static phone/email support from operator configuration. None go through DeepSeek.

## 2. Atomic lease state machine

Proposed states:
- `FREE`: no valid IP lease; next anonymous cookie can acquire it.
- `ACTIVE(session_id, expires_at)`: same-cookie requests allowed subject to all other quotas; different token at same IP gets `IP_BUSY` without data leakage.
- `IN_FLIGHT(session_id, request_id)`: only one concurrent model POST for the accepted session; duplicate sends get predictable non-paid `429/409`. The lease must survive for the duration of the provider call and have a bounded recovery mechanism.
- `EXPIRED` / `RELEASED`: explicit End Session or idle lease expiration releases IP ownership. **No reset of daily quota** and no unauthorized transfer of previous transcript.
- `DAY_LIMIT(ip_key, day_key)`: separate hard account state. Overrides `FREE/ACTIVE`: no new model calls until `resets_at`; frontend chat submit disabled and support notice presented. Does not grant a new session to circumvent lockout.

**Atomicity:** acquisition, session ownership check, per-IP Q/day increment/reservation and in-flight flag are a single all-or-nothing shared-store operation. Enforce on **every** request; frontend disabled button is presentation only. Backend failure to read lock/quota must fail closed and log an availability event, not issue an ungated paid POST.

**Lease release:** explicit `Завершить консультацию` can free IP to another visitor, but cannot reset today's question counter, and never exposes prior private chat. Owner-approved idle lease TTL **15m** (and technical dialogue memory invalidation), with a separate 30m continuous-series reset; state model must ensure tabs renew lease only via authenticated anonymous cookie and bounded activity, not indefinite unauthenticated keepalive spam.

**IPv6 caveat:** exact-address quota can be evaded by frequently rotating temporary IPv6 addresses. A /64 grouping or separate network rate limit may be investigated for abuse defense but is **not** a universal identity; it can accidentally block legitimate neighbors. Preserve exact-IP primary invariant and add a separate measured network/global anti-abuse layer. VPN and NAT can share IP across different humans.

## 3. Daily quota semantics (approved policy DS-SEC-09; implementation proposed)

- Choose an **explicit fixed business timezone** and one daily accounting unit, e.g. `YYYY-MM-DD` in that timezone. After quota exhausted, UI shows `Предел обращений за день достигнут. Консультант станет доступен <timestamp>.`; static support contacts remain available. Business timezone **TBD by owner**, do not silently assume UTC or browser local time.
- Count one daily **visitor question** on atomic request admission, even if the answer is rendered locally or from cache. Count attempted provider POSTs independently just before dispatch; timeout still counts as an attempted model POST. A blocked validation/rate request is not an admitted visitor question (but may generate a bounded security event).
- One user clicking repeatedly before next allowed time must not increment paid quota or dispatch multiple calls; still monitor nonpaid abuse attempts.
- Multi-session from same canonical IP never permits additional quota; same IP across days resets per-IP daily count, not global monetary/account quotas.
- For user-facing fairness, allow same valid session to read its own previous replies after daily exhaustion; freeze the send control and avoid any further DeepSeek HTTP.

**Owner-approved pilot defaults (DS-SEC-07/08), not yet implemented:** 20 accepted visitor questions/IP/calendar day (including local answers), separately counted paid POSTs, 15m inactivity to release active IP lock; 30m inactivity to reset progressive series; max 1200 chars, input ≤10000 tokens (full provider request, hard maximum), output ≤450, Q6–10 waits 10/20/40/60/90s. Global daily/monthly budget limits must be set before implementation.

## 4. Private per-question audit record schema (proposal)

For each accepted provider-bound request create, transactionally:

```json
{
  "request_id": "opaque-random-id",
  "session_id_digest": "keyed-digest-not-session-cookie",
  "client_ip_encrypted": "<encrypted full canonical IP>",
  "client_ip_family": "IPv4 or IPv6",
  "question_received_at_utc": "ISO8601",
  "question_text_encrypted": "<encrypted question text>",
  "llm_request_started_at_utc": "ISO8601 or null",
  "answer_sent_at_utc": "ISO8601 or null",
  "answer_text_encrypted": "<encrypted final visitor-visible answer or null>",
  "decision": "answered | missing_data | clarification | blocked | failed",
  "reason_code": "policy/status if applicable",
  "source_snapshot_id": "trusted revision or null",
  "model": "provider model or null",
  "usage_input_tokens": 0,
  "usage_output_tokens": 0,
  "cost_estimate_usd": 0,
  "provider_billing_verified": false,
  "quota_day_key": "YYYY-MM-DD",
  "series_ordinal": 0
}
```

Implementation can store full IP and text as encrypted DB fields and use **separate** keyed HMAC token for fast IP quota/lease lookup; encryption is for confidentiality, keyed HMAC is not anonymization. This is a **design illustration**, not a final schema. Capture UTC exact time with timezone, monotonic/DB clock source where possible; display local business time in admin UI.

Create an event for every received attempt (including length rejects and rate blocks) with server time, IP, outcome and bounded sanitized metadata. Full accepted question and actual final reply logged per owner requirement, subject to approved privacy handling; rejected overlarge text stored as safe bounded excerpt/hash/length to prevent an attacker using the log system as unlimited storage. If log system fails, do not quietly claim full audit completeness: fail safely according to declared fail-closed policy and do not lose budget accounting.

**Never expose** real visitor IP, raw transcripts, untrusted user strings rendered as HTML, hidden provider key, system prompt secrets, signed session cookie, or private docs to the public GitHub repository, another visitor or the model unnecessarily.

## 5. Privacy and operational acceptance gate

- Even with no registration, **IP plus exact technical questions and replies can be personal information**, and questions themselves can contain contacts, passwords or commercial secrets. Applicable privacy law and international transfer/provider-processing requirements must be reviewed before public launch. EU GDPR scope requires a case-specific assessment; GDPR specifically lists IP addresses as personal data when applicable.
- Before implementation define **purposes** (security abuse prevention, operational analysis, quality), **lawful processing basis**, **visitor-facing privacy notice**, **data recipients**, **retention and deletion period**, staff roles and log access review. Raw full IP/transcripts should not be retained indefinitely. Owner-approved default **30 days private raw logs** (subject to privacy/lawful-processing launch review), **not a legal determination**; aggregate anonymous counters can be retained longer if truly unidentifiable.
- Apply encryption in transit/at rest, secret rotation, database access restrictions, no request-level logs in public repo, backup deletion alignment and log injection escaping/sanitization. Privacy notice does not by itself prove compliance.
- Trusted proxy/CND topology must be pinned before relying on IP-keyed state. Verify original-client IP authenticity through actual network tests; no "I saw X-Forwarded-For" trust by itself.

## 6. Proposed offline acceptance tests, no provider spending

1. Same IP and same cookie opens a second tab: same session, no duplicate independent session.
2. Same IP and **different cookie** simultaneously: deny `IP_BUSY`; no previous transcript returned.
3. Different IP simultaneous: each may acquire their own slot.
4. Shared NAT office clients: knowingly share one IP slot; UX message is neutral, no account/session information leak.
5. Three simultaneous calls race to acquire one IP slot: exactly one admission; zero unauthorized DeepSeek calls in mocked provider.
6. Cookie deletion or End Session then new conversation: active lease may change, but same IP daily quota remains unchanged.
7. 20 admitted attempts in daily bucket (if adopted), next blocked `DAY_QUOTA` until exact next business midnight, plus static support link; no model invocation.
8. Series 10/11 transition and 30m reset separate from daily count; false refusals prevented on a legitimate next-day visitor.
9. Header spoof attacks `X-Forwarded-For`, `CF-Connecting-IP`, IPv4-mapped IPv6 normalization and trusted-proxy chains; actual IP cannot be chosen by attacker-supplied header.
10. Logging stores every accepted full question and final answer with separate timestamps/full IP, and security events for rejected attempts. Redact/encrypt as required, prevent log injection and cap giant rejected payloads.
11. Provider timeout/unknown spend still consumes reserved attempt and prevents retry; accounting/lock remains sound after process restart.
12. No shared-store access or invalid canonical IP: fail closed for all routes. **Exhausted global paid DeepSeek USD** denies P1/P2 but owner DS-SEC-10 explicitly permits source-verified zero-provider **P0** with all IP/day/series/CPU/concurrency/audit guards; a separate non-monetary safety breaker can deny all routes. Never leak another visitor's session.
13. Retention expiry/deletion and staff log viewing tested; no private log data in GitHub/DeepSeek error messages.

**Implementation and any live HTTP/model calls require separate owner authorization**. All DS-QV-01 paid GO exhausted 6/6. No Merge, DS-02, production, Corpus Freeze, NEW RAG or Saturn site changes.

**Sources:** OWASP API4:2023 `https://api-security.owasp.org/editions/2023/en/0xa4-unrestricted-resource-consumption/`; OWASP Logging `https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html`; MDN `https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For`; European Commission GDPR scope `https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en`.
