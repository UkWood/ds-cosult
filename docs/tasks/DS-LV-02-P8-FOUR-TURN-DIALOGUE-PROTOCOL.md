# DS-LV-02/P8 — 4-Turn Synthetic Conversational Continuity Test

**Recorded:** 2026-11-18  
**Status:** **OWNER BLANKET GO ACTIVE — OFFLINE PREFLIGHT PENDING; NO P8 PAID CALLS**  
**Previous stage:** P7 direct OCR accepted with review notes.  
**Limit:** **four** `POST /chat/completions` at most, **$0.020 organizational total** (not provider-enforced hard cap).

## Architecture question

Does the direct DeepSeek Flash Chat Completions API, used as a stateless API with **explicit prior message history**, produce consistent answers to four turns testing:
1. Two synthetic entities and an explicit attribute request;
2. anaphora ("А у второй?");
3. correction of an attribute for the first entity, preserved state;
4. comparison of both entities and abstention for an absent attribute?

**Synthetic-only ground truth:** ЛИРА-17 = 12 В, RS-485 initially; ОРБИТА-5 = 24 В, Ethernet; correction LIRA-17 interface = Ethernet; neither entity has a specified operating temperature. No genuine Saturn site content or benchmarks.

## Model and API

Official docs: https://api-docs.deepseek.com/api/create-chat-completion/ ; https://api-docs.deepseek.com/guides/build_a_chatbot/

- `POST https://api.deepseek.com/chat/completions`; model `deepseek-flash`, `thinking:{"type":"disabled"}`, `tool_choice:"none"`, no declared `tools`, `stream:false`, `max_tokens:192`, low temperature.
- Each turn is a **separate HTTP POST**. Request includes system message, all prior user prompts, exact prior assistant answers, then current user prompt. This tests explicit conversation-memory management; it does not prove hidden provider memory between independent requests.
- Check one nonempty answer, `finish_reason:stop`, observed model, absence of tool calls and reasoning. Snapshot synthetic history in WSL mode `0600`; only redacted per-turn diagnostic with excerpt, answer SHA256, usage, token-cost estimate and HTTP metadata.
- Each `--turn-N` creates exclusive `logs/ds-lv-02-p8-turn-N-attempted.marker` before POST; no automatic retry, redirects or extra confirmation string. Hidden `getpass` for key only.
- Continue to N+1 only when prior N complete, prior reports match private history by SHA and Architecture Session A independently reviewed the outcome. No stage-wide `--run-all` mode.
- Each step requires a separate WSL invocation; one command block at a time from Architecture Session. `--self-test` is offline and cost-free. P8 actual requests remain zero until offline preflight acceptance.
- At each turn, estimate worst-case spending conservatively; stop if projected cumulative organization budget would be exceeded. Actual provider charge may differ and there is no guaranteed API hard spending cap.

## Turn-by-turn acceptance

| Turn | Input concept | Expected ground truth |
|---|---|---|
| 1 | explicit LIRA-17 question with two-card facts | 12 В, RS-485 for ЛИРА-17 |
| 2 | "А у второй?" | ОРБИТА-5, 24 В, Ethernet |
| 3 | correction "Ethernet instead of RS-485" for LIRA-17 | updated ЛИРА-17: 12 В, Ethernet |
| 4 | compare both interfaces, ask absent temperature | both Ethernet; ОРБИТА-5 temperature **not given**, don't invent |

No external evidence retrieval in this test; the ground truth is provided in the synthetic conversation.

## Next operation

Architect commits script plus P7 acceptance/evidence. Owner WSL downloads pinned script, runs `py_compile`, `--self-test`, reports checksum. **No P8 live POST before Architecture accepted the offline result.** Afterward, only `--turn-1` will be provided (not multiple turns at once), within general owner GO. No `P8-APPROVED` phrase.

P9 offline evaluation after four-turn results; no production, no merge, no NEW RAG or Saturn source changes.
