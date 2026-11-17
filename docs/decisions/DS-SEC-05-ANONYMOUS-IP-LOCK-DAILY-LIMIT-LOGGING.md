# DS-SEC-05 — Owner-Accepted Anonymous Visitor Access, IP Lock, Daily Lockout and Dialogue Logging

**Recorded:** 2026-11-18  
**Decision:** **ACCEPTED OWNER REQUIREMENTS / IMPLEMENTATION NOT STARTED**  
**Scope:** DS-консультант, public Saturn technical consultant, existing Draft PR #1 `docs/ds-01c-benchmark-memory`.  
**Supersedes DS-SEC-04 where it previously proposed only per-session daily accounting.** Numeric quota values and retention periods remain open, separate from the adopted requirements.

## 1. Exact owner requirements

Owner explicitly added to DS-SEC-03:
1. `При превышении суточного лимита чат консультанта становится не доступен до сброса лимита.`
2. `Для использования консультанта не требуется ни какой регистрации или авторизации.`
3. `Но с одного IP нельзя вести несколько сессий консультанта одновременно.`
4. `Все вопросы и ответы должны логироваться с указанием даты/времени и IP посетителя, если это возможно.`

These are **binding product/architecture requirements** for the future prototype, not authorisation to deploy or perform external model calls.

## 2. Consequent accepted behavior

- **No account, password, registration or login** for visitor chatbot access; server-issued opaque short-lived anonymous session handle is not an identity login.
- **One active conversation/session per outward-facing client IP at any time**. Multiple tabs **with the same anonymous session cookie** may reference the **same** conversation; backend limits in-flight DeepSeek call concurrency to **one** per session/IP. A different token/browser session at the same IP must not receive the existing session's private dialogue. It must receive a neutral busy/locked message without private data.
- **Daily request quota keyed to canonical trusted IP** independent of session ID; deleting session cookies, starting a new conversation or inactivity-reset of the progressive series must not reset the daily spent quota. A newly created session from the same IP still sees the consumed count.
- **At daily quota exhaustion, paid consultant input is unavailable until the exact next quota reset**; no chat POST to model, no paid tokens. Existing conversation display may remain viewable to its original anonymous session, never to other users. Show a clear static message with remaining duration / exact reset time and verified support contacts.
- **Daily limit** and **continuous-series limit** are independent: after a series of ten accepted questions, the eleventh is redirected to static support handoff; a later new series may start only if daily quota is still available and other controls allow it.
- **Log accepted visitor questions and the actual final visitor-visible answers**, each with timestamps and the resolved visitor IP (when technically available and when permitted by applicable law), plus provenance: session identifier surrogate, request/correlation ID, status, policy reason, latency, token usage, estimated cost and source snapshot reference. Rejected/abusive requests should also create a security event even when **no model answer exists**. Avoid allowing long rejected payloads to create unbounded logs.
- Log storage must be backend-managed and access-restricted. Do **not** expose real IP, full transcripts, keys or private logs in this public GitHub repository.

## 3. Precise privacy and feasibility conditions

- A network **IP is not a reliable person identity**: one IP may represent many customers behind corporate NAT; visitor's IPv6 address may rotate; VPN/proxy users can share or switch IPs. The explicit owner preference is **one IP = one active session**, accepting the shared-IP service impact. This cannot guarantee one human visitor; cost protection still needs global spend controls.
- Use the real direct peer IP if directly connected; behind a reverse proxy/CDN read a forwarded original-client header **only from configured trusted proxy hops/networks**. Do not trust visitor-supplied `X-Forwarded-For` or `CF-Connecting-IP` when origin is publicly reachable/bypasses proxy. Canonicalize IPv4/IPv6, account for both address families, ensure proxy changes cannot change bucket keys unpredictably.
- Recording a full IP alongside conversation text is technically feasible in a backend, but such records can contain personal data and confidential user input. **No unconditional legality claim**: before public launch establish lawful purpose/basis under applicable regulations, clear visitor-facing notice, restricted operators and retention/deletion schedule; evaluate GDPR applicability if EU residents are in scope and relevant local privacy law. Encryption/pseudonymization can supplement but may not make linkable data non-personal.
- Authorized retention is **not yet set by owner**; neither unbounded storage nor default public export is permitted. Avoid logging provider keys, cookies, authentication tokens, system prompt internals, hidden thinking, other users' session data, or accidental secret strings. Use data validation/escaping to prevent log injection.

## 4. Invariants to preserve

- Domain remains Saturn-specific, with system non-fabrication sentence `Не выдумывай недостающие технические характеристики.` and independently verified source facts from trusted website/PDF dossiers. This IP/throttle decision does **not** allow visitor role/goal override.
- Server hard limits for question length, history/context tokens, output tokens and global daily/monthly provider budget remain mandatory, with exact numbers open.
- Client/browser cannot authorize a new IP session, change quota, forge session owner, override limit via `я администратор`, or recover someone else's dialogue.
- On full-day lockout **no paid API request** may be dispatched; no background queue/retry to later drain quota.
- Multiple backend workers must enforce these rules **atomically** and fail closed when shared quota/lock state unavailable, not independently accept competing sessions.
- IP and transcript logs are private security/operations data, not facts to train or feed into other visitor sessions.

## 5. Decisions still requiring owner agreement

1. Exact **daily count per IP**; 20/day remains a draft suggestion, not a binding accepted number.
2. Reset model: fixed calendar day at agreed company timezone versus sliding 24-hour window; a calendar-day reset gives an easily displayed single reopening timestamp. Provisional recommendation: **fixed timezone and midnight**, company timezone TBD.
3. Session idle lock TTL; candidate **15 minutes**, separate from previously proposed continuous-series idle reset **30 minutes**. Provide explicit End Session action but don't allow that action to reset per-IP daily quota.
4. Whether all same-cookie tabs can view one conversation (proposed yes) versus strictly one browser tab.
5. Actual IP/proxy infrastructure; logging retention period, privacy notice, legal review, on-site administrative access and anonymization controls.
6. Handling public IPv6 privacy-address rotation, office NAT sharing, VPN bypass and global anti-abuse controls.

**No API tests / no implementation / no Merge / no DS-02 / no production / no Corpus Freeze / no NEW RAG or read-only Saturn source writes.** Existing DS-QV-01 six paid calls exhausted.

**References:** `docs/decisions/DS-SEC-03-SCOPE-AND-RESOURCE-BOUNDARIES.md`, `docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md`; MDN X-Forwarded-For `https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Forwarded-For`; OWASP Logging Cheat Sheet `https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html`; European Commission `https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/application-gdpr_en`.
