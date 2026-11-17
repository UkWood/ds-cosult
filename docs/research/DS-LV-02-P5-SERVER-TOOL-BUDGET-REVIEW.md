# DS-LV-02/P5 — Deep Thinking Search: Cost and Controllability Review

**Дата:** 2026-11-17  
**Scope:** official documentation investigation only, zero DeepSeek API charges  
**Status:** **NO DOCUMENTED HARD PER-REQUEST MONETARY CAP CONFIRMED**.

## Verified official findings

1. DeepSeek Web Tools documentation (https://api-docs.deepseek.com/guides/web_tools/) says thinking enabled + `deepseek_web_search` triggers **deep thinking search**; model may independently search, open pages (`open_page`) and locate text (`find_in_page`). The guide says "**up to about 20 tool calls**" per answer, **not an enforceable hard cap**.
2. Each `action=search` may contain multiple `queries`; successful individual queries are billed, not just outer Chat Completions HTTP calls. `open_page` causes separately billed Fetch when successful. `find_in_page` itself is not billed in the Web Tools accounting description. The documented aggregation is `usage.server_tool_use.tool_search/tool_fetch/tool_image_search`.
3. The compatible Responses API documentation (https://api-docs.deepseek.com/guides/responses_api/) explicitly lists **`max_tool_calls` as ignored**. The Chat Completions API documentation does **not** offer a verified parameter for bounding `deepseek_web_search` nested calls.
4. The tool's `tool_choice` cannot force the web tools; `required` is treated as `auto`. The model controls whether and how much it searches. A prompt urging "few searches" is **not an enforceable safety cap**.
5. Current published prices (https://api-docs.deepseek.com/quick_start/pricing/):
   - successful Search $0.00075 each; successful Fetch $0.00075 each;
   - `deepseek-flash` peak cache-miss input $0.30 per 1M; cache-hit input $0.006 per 1M; output $1.20 per 1M;
   - off-peak $0.15, $0.003, $0.60 per 1M, respectively.
6. Neither published rate/concurrency pages nor the consulted Web Tools guide confirms an account-level hard dollar stop for a **single native-tool call**. The documented concurrency quota is not a monetary quota. Do not assert that other account-level controls categorically do not exist; they are simply **not verified** in these references.

## Measured calibration from P4

Actual user-reported P4 (no thinking, 1 outer HTTP POST):
- 1 completed search step, **3 billed Search queries**, 0 Fetch;
- 9,393 prompt tokens and 303 completion tokens;
- estimated peak $0.0054315 and off-peak cache-miss $0.00384075;
- actual invoice **unverified**.

P5 may perform multiple searches and page reads, with expanded context and thinking output. Even a hypothetical ~20 actions **is not a budget cap**: some search actions can include multiple billable queries. Illustrative only: 20 successful search queries alone cost $0.015, before fetches or model tokens; 20 actions with three successful queries each would cost $0.045 in search charges. These are scenarios, **not predictions or maxima**.

## Safety controls and limits

- **Mechanical local controls available:** 1 client HTTP attempt; exclusive on-disk attempt marker; no retries/no redirects; bounded `max_tokens=1536` for generated tokens; `reasoning_effort=low` for a minimal capability smoke; prompt asks for limited source use; hidden API key; no private data.
- **Not mechanically controlled:** number of server-side searches/queries/fetches; total prompt tokens produced by retrieved context; exact bill; latency; model decision to search.
- **No hard P5 USD maximum can be certified from these inputs.** Do not label any rough spending estimate as maximum.
- The P5 script's default mode refuses paid execution; `--self-test` is offline, zero network. Future `--execute-after-owner-go` explicitly requires new numeric GO and a local confirmation string, but **does not enforce a provider monetary cap**.
- The script preserves safe metadata of reasoning (`reasoning_present`, token counts), **never raw reasoning contents**. It stores only the final answer privately in Linux (0600) to permit later independent factual review; only redacted metadata may be published to PUBLIC GitHub.
- A response without tool use, no citations, or truncated answer is INCONCLUSIVE/PARTIAL, not "PASS" on text substring.

## Architecture decision before any paid P5

**Proceed with OFFLINE preflight only.** Before granting P5 paid GO, request a clearly defined organizational budget from the owner, explain that exceedance is technically possible, and consider checking any real account-side spending limits in the user's DeepSeek console. A strict hard $0.01 cap **cannot be promised** by this native multi-search workflow.

P6–P9 and DS-02 not authorized. NO MERGE, no NEW RAG writes, site read-only.
