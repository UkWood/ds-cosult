# DS-LV-02/P5 — Deep Thinking + Native Web Search (Proposal Only)

**Date:** 2026-11-17  
**Status:** **P5 PAID OWNER GO RECEIVED — 1 POST / ORGANIZATIONAL $0.05; NOT EXECUTED**  
**Previous gates:** P1 thinking PASS, P2 standalone Search PASS, P3 URL-reading capability PASS WITH REVIEW NOTES, P4 model-managed Web Search PASS WITH REVIEW NOTES.

## Test objective

Verify whether `deepseek-flash` can perform **multi-step thinking + server-managed web search** using one direct Chat Completions request with both `thinking:{"type":"enabled"}` and `tools:[{"type":"deepseek_web_search"}]`.

This verifies **P5 capability**, not production reasoning correctness; keep source claim checks separate.

## Test design (not permission)

- Use `POST https://api.deepseek.com/chat/completions` with non-streaming mode.
- Proposed one public, low-risk question comparing **official DeepSeek 2026 release** claims on Deep Thinking and Web Search, asking for an official citation. No real Saturn corpus, private GT, proprietary data or PDFs.
- Document `reasoning_content` presence/length only, do not persist chain-of-thought.
- Inspect `message.server_tool_calls[]`: actual completed search(s), queries/actions, sources, any page reads, citations/annotations and source overlap. Be prepared for multiple internal tool calls, fetches and large prompt assembly.
- Separate gates: `THINKING_OBSERVED`, `WEB_TOOL_INVOKED`, `CITATIONS_TRACE`, `ANSWER_SOURCE_FIDELITY`, `LANGUAGE`, `BILLING`.
- Do not reuse P4 simple question as proof of improved thinking; a true comparison needs controlled paired questions and an agreed Ground Truth.
- Do **not** treat the existence of citations or good-looking answers as a claim-level grounding certificate.
- No retries, hidden getpass, protected output, no raw response or reasoning in public repo.

## Billing risk: must resolve before any P5 GO

P4 provided an important measured warning: **one external POST generated 3 internal Search charges and 9,393 prompt tokens**, with $0.0054315 conservative peak estimate, $0.00384075 off-peak cache-miss estimate, actual invoice not checked.

With thinking enabled, automatic multi-step searches and page reading could create **more searches/fetches**, reasoning tokens, and model-context tokens even under a single HTTP POST. An organizational $0.01 limit **cannot be guaranteed mechanically** by the current script; **do not presume $0.01 is safe**. Before requesting a P5 GO, research provider-enforced account budget/quota and tool stop constraints or choose a risk limit that the owner explicitly understands.

Proposed next actions: (1) free official docs/price/tool-budget review, (2) offline-only P5 script + synthetic tests, (3) explicit separate GO for paid call including numerical amount, max requests, and acknowledged residual risk. P4 GO is already exhausted.

## No automatic escalation

P6..P9 remain unauthorized; no merges, DS-02, production or Corpus Freeze. NEW RAG and Saturn-Main-Site remain out of scope / read-only.

## Offline preparation follow-up (2026-11-17)
Owner replied «Разрешаю» to a proposal for **free documentation/cost research and offline code preparation**, not to a specific dollar budget. Therefore paid P5 is not authorized. Consulted official Web Tools / Chat Completions / Responses API / pricing / rate-limit guides. The Web Tools guide describes up to *about* 20 steps; search action may include multiple billed queries; Responses API `max_tool_calls` is explicitly ignored. No verified server-side hard dollar cap. See `docs/research/DS-LV-02-P5-SERVER-TOOL-BUDGET-REVIEW.md`.

Script `scripts/validation/ds_lv_02_p5_thinking_search.py` supports offline-only `--self-test` (4 synthetic test scenarios, 0 HTTP/0 USD). **Do not use `--execute-after-owner-go` without separately signed numerical GO.** Request uses only `deepseek_web_search`, thinking enabled, reasoning_effort low, max_tokens 1536 and one public official-doc comparison question. Tests completed `deep_search` search/open/find calls, citations, presence of reasoning metadata, billed tool counters, language. Full final answer stored **locally only** for human quality review; raw reasoning never recorded.

P5 is not a comparative evaluation of quality and does not complete any Saturn Ground Truth. P6..P9 blocked.

## WSL Offline Preflight — PASS (2026-11-17)
User-provided execution of pinned `scripts/validation/ds_lv_02_p5_thinking_search.py`: Python compilation and synthetic `--self-test` both PASS, **0 network / $0**. Local SHA256: `4a9dd93517ae09a1e0f1ec61415d1ab65666cdb127a2d0dd2681c43941882608`. Evidence record: `../evidence/DS-LV-02-P5-OFFLINE-PREFLIGHT.md`. This is not a paid-test GO. No paid execution or real P5 capability verification has occurred.

## Separate explicit paid owner GO (2026-11-17)
Owner has replied «Да» to an exact proposal to allow one paid P5 POST at organizational USD $0.05, **acknowledging the risk of exceeding it**. See `DS-LV-02-P5-OWNER-GO.md`. No provider-enforced monetary cap has been proven; no retries permitted; P6..P9 and all production activity unauthorized. The P5 Python script is unchanged from its successful offline preflight. **P5 live NOT EXECUTED at this update.**
