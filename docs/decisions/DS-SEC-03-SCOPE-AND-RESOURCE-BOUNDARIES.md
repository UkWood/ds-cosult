# DS-SEC-03 — Accepted Product Guardrails: Consultant Scope and Resource Boundaries


**CURRENT NUMERIC APPROVAL NOTE (2026-11-18):** The owner has now approved the previously proposed numeric pilot parameters as documented in `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md`; the originally pending count/delay values are therefore resolved by the later decision. Deployment configuration values are still pending.

**Recorded:** 2026-11-18  
**Decision type:** **OWNER ACCEPTED — PRINCIPLES / POLICY DIRECTION ONLY**  
**Implementation:** **NOT AUTHORISED / NOT DEPLOYED**  
**Repository:** `UkWood/ds-cosult`, existing Draft PR #1 `docs/ds-01c-benchmark-memory`.

## 1. Owner decisions and requested constraints

The owner accepted the previously proposed **strict specialization of the public Saturn technical consultant**: the assistant may understand and discuss natural technical questions, switch between supported devices, clarify questions and acknowledge missing data, but it must **not** become a general-purpose unconstrained chatbot due to visitor instructions. Out-of-domain queries should receive a short polite scoped response with a path back to the Saturn domain. A user instruction cannot modify source policy, system rules or verified technical specifications.

The owner also explicitly requested two **mandatory resource-protection capabilities**:
1. Bound the maximum **text length of each incoming visitor question**.
2. Bound **the number of questions over time** with progressive throttling: first five without added cooldown; longer continuous sequences progressively delayed; after more than ten in a sequence, display contact details of company technical support and stop further model inference for that sequence.

The owner presented the specific counts/delays as examples for discussion, not already approved code-level numerical defaults. Preserve these as the **requested policy shape**, but classify exact numeric limits, delay schedule, identity scheme, session reset and daily/monthly budgets as **proposals pending review**.

## 2. Unchangeable trust rules carried forward

- `DS-SEC-01` owner-accepted explicit system-level sentence: `Не выдумывай недостающие технические характеристики.`
- Visitor input always remains untrusted **user** text, never server/system/developer instructions.
- Saturn website and PDFs are **owner-declared trusted and prompt-injection-free**; this discussion targets direct abusive chat input, not indirect source injection.
- Trusted technical fact authority remains with the website/PDF evidence and provenance-bound Entity-Centric dossiers, not with the visitor's assertions.
- Rate-limit decisions, token quotas, cost accounting and support handoff must run in **backend code before any paid DeepSeek request**, not be delegated to model compliance or browser-side timers.

## 3. Requested user experience

- First five short in-scope questions in a continuous series: **no artificial added wait** but still subject to length, concurrency, request safety and global budget.
- Sixth through tenth: progressive **server-enforced** wait times (exact schedule proposed separately).
- More than ten consecutive accepted questions: do not call DeepSeek; show **operator-configured static** phone/email link for Saturn technical support. Never invent contact details, never let LLM produce arbitrary mail/telephone values. Do not automatically send mail to support.
- A legitimate topic change or conversation correction is not automatically a new quota identity or a mechanism to bypass a continuous series.
- Long or invalid input: transparent validation message explaining size limit; no paid model call. Rate limit / budget exhaustion: predictable UI notice with when to retry if possible, not silently waiting or spending.
- Genuine visitors behind the same shared corporate IP should not be subject to an indiscriminate hard per-IP only ban; account/session-based counters and abuse-level IP controls must be distinguished.

## 4. Governance

This is a **decision about the required behavior**, not agreement on the draft number 1200 characters, 30-minute reset, exact exponential backoff, 20 requests/day or a new model/provider/API test.

For the detailed numerical/implementation proposal see `docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md`. DS-QV-01 GO **fully consumed 6/6**, no new DeepSeek calls or new stage without separate owner decision. No Merge, DS-02 implementation, corpus freeze, production, changes to NEW RAG, or writes to read-only Saturn-Main-Site.
