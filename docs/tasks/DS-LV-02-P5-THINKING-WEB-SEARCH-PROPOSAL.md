# DS-LV-02/P5 — Deep Thinking + Native Web Search (Proposal Only)

**Date:** 2026-11-17  
**Status:** **PROPOSED ONLY — NO OWNER GO, NO PAID EXECUTION**  
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
