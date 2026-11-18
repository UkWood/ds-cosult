# DS-SEC-08 — Independent Documentation Consistency Review (10,000 Input Tokens)

**Date:** 2026-11-18  
**Type:** Architecture/documentation-only verification, **not** runnable-code acceptance  
**Decision:** **DOCUMENT CONSISTENCY PASS WITH IMPLEMENTATION GATES STILL OPEN**  
**Owner instruction:** increase full DeepSeek input cap from 3,000 to 10,000 tokens and carefully correct corresponding documents.

## 1. Sources inspected and updated

| Document | Change and verified current reading |
|---|---|
| `docs/decisions/DS-SEC-08-OWNER-APPROVED-10000-INPUT-TOKEN-CAP.md` | New owner-accepted superseding decision, previous policy preserved historically |
| `docs/decisions/DS-SEC-07-ACCEPTED-PUBLIC-CONSULTANT-GUARDRAILS.md` | Current authoritative table **10,000** input; full request cost reserve, 10,001 over-limit test |
| `docs/security/DS-SEC-04-RESOURCE-LIMITS-AND-SPENDING-GUARDS-PROPOSAL.md` | Proposal values and cost examples updated; previously unapproved/rolling-day wording annotated as superseded by owner approvals |
| `docs/security/DS-SEC-06-IP-LEASE-DAILY-LOCKOUT-AUDIT-PROPOSAL.md` | IP/session audit still unchanged; the one LLM input line and reservation note now 10k |
| `docs/architecture/DS-EC-01-ENTITY-CENTRIC-VERIFIABLE-RAG-REFERENCE.md` | End-to-end bound, cost and source-context overflow conditions now 10k |
| `docs/architecture/DS-EC-03-EVIDENCE-PACKET-CONTEXT-AND-ANSWER-GATE.md` | Entire assembled prompt 10k, illustrated distribution + 10,000/10,001 tests, updated reserve |
| `docs/architecture/DS-EC-02-03-DESIGN-CONSISTENCY-REVIEW.md` | Updated documentation review with historical change noted, not misrepresented as runtime validation |
| `docs/status/PROJECT_STATE.md` and `docs/history/ARCHITECTURE_LOG.md` | Append-only change and owner decision to be recorded, historical 3k entries left intact |

`docs/architecture/DS-EC-02-CANONICAL-ENTITY-FACT-RELATION-CONTRACTS.md` was also considered: it defines source/evidence types rather than any token cap, so it **did not need edits**. Other earlier test acceptance/usage reports and API results remain historically immutable; none may be recalculated or reinterpreted due to this future runtime change.

## 2. Current exact boundaries

- **Full provider input** max **10,000 counted tokens**, including true system prompt, user text, canonical entities, compact history/state, typed facts/relations, evidence quotes, formatting schema and request framing.
- **Max model output** **450 generated tokens** separately, not a 10,000-input quota subtraction.
- **Visitor question length** still **1,200 Unicode characters**; HTTP JSON body still **8 KiB**. Character and input token guards are independent.
- **0 or 1 paid `deepseek-flash` model call per accepted visitor turn** in initial runtime; no default paid native search/Fetch/File/OCR.
- 10k is **a ceiling, not a prompt target**. Retrieval chooses the shortest evidence-sufficient packet; plain questions usually need substantially less input and may be fully local with 0 provider calls.
- For a complex question that cannot retain all mandatory revision/condition/conflict evidence within 10k, answer partial/clarification/needs-support/error instead of truncating vital qualifiers.
- The backend must count model-compatible tokens for the **entire actual API input before paid dispatch** and use validated conservative margin when exact prediction cannot be established. A false claim of exact enforcement based on a character approximation is not acceptable.
- All previous visitor IP, cooldown, daily quota, private log retention and global spending protections remain owner-approved **unchanged**.

## 3. Independent mechanical document checks

Read back the seven changed architecture/security documents from the existing PR #1 branch and checked active token-cap assertions (historical comparison references excluded):
- **No remaining active 3,000-token hard requirement** in those documents;
- All seven carry current 10k cap and the new cost expectation;
- The seven illustrative ceiling-capacity budget segments in DS-EC-03 were recomputed: **600 + 500 + 500 + 2,400 + 4,300 + 300 + 1,400 = 10,000**;
- **10,000** boundary permitted when other guards pass; **10,001** rejected or packet rebuilt below the limit before provider call;
- Model-only **fixed peak** math rechecked against official DeepSeek Flash table on 2026-11-18:
  - Previous: `3000 × 0.30/1e6 + 450 × 1.20/1e6 = $0.001440`;
  - Updated: `10000 × 0.30/1e6 + 450 × 1.20/1e6 = $0.003540`;
  - **2.4583×** previous model-only worst case on those rates;
  - 10 calls **$0.03540**; 1,000 calls **$3.54**; 1,000 visitors each using 10 full-cap calls **$35.40**.
- Runtime **not tested**: official provider token-counting may differ from local estimates, prices may change, and actual invoice is unknown. A reserve of $0.00354 at today's assumed peak rates is a model-only **risk estimate**, not a hard provider dollar cap.

Verified price reference: https://api-docs.deepseek.com/quick_start/pricing/.

## 4. Required future acceptance scenarios — NOT EXECUTED

| Case | Expected server behavior |
|---|---|
| Complete assembled input 9,999 model-compatible tokens | Allowed by input cap, subject to other guards |
| Complete input exactly 10,000 tokens | Allowed by input cap, subject to other guards and cost reservation |
| Complete input 10,001 tokens | Reject/prevent paid POST or safely rebuild to <=10,000 |
| New user question <=1,200 characters but evidence/history exceeds cap | Rebuild packet, safe partial/clarification, no over-limit POST |
| Required conflicting source omitted to fit cap | Reject unsafe packet; cannot quietly suppress contradiction |
| Zero-call deterministic answer | No provider token spend, logging/IP policy still applies |
| Concurrent accepted requests nearing global daily/monthly budget | Atomic reserve using revised possible max; fail closed on shortage |
| Provider token estimate exceeds actual input cap under production serialization | Hold request until counter/overhead verified; no false hard-cap claim |
| API usage unknown after timeout | Conservative charge reservation held; no automatic retry |

## 5. Final conclusion

**PASS (documentation alignment only).** DS-SEC-08 is the currently owner-approved override; the active design consistently uses **10,000** full input tokens and **450** output tokens. Relevant cost calculations, budgets and boundary tests are consistent. It does **not** authorize code changes or paid tests.

**No Merge, DS-02 coding, new HTTP calls, deployment, Corpus Freeze, NEW RAG or read-only Saturn source writes.** Prior DS-QV-01 authorization is fully exhausted 6/6.
