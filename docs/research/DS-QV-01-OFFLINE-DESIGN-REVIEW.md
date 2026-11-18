# DS-QV-01 — Architecture Design & Pinned Source Review (No Paid Execution)

**Recorded:** 2026-11-18  
**Status:** **DESIGN REVIEW COMPLETED; WSL OFFLINE PREFLIGHT PENDING; PAID EXECUTION NOT AUTHORISED**  
**Scope:** Follow-up to `QUALITY-P8-01` after completed P9; no DS-02 implementation.

## 1. Need / test separation

P8-TURN-4 demonstrates **prompted** abstention, not spontaneous/no-user-hint technical uncertainty handling. DS-QV-01 separates system evidence guard from natural user language with a 2×3 paired design: system arms A/B; two missing-attribute tasks M1/M2, one answerable control K1. Six independent one-POST conditions, not a sequential conversation and not a P8 replay.

Critical retention: each trial uses the SAME six-message frozen history taken from three historically accepted P8 prompts + exact model responses; assistant hashes checked against accepted P8 evidence. For M1 the user message is the P8-TURN-4 wording **without** its anti-hallucination instruction. Only the system message changes between the A/B pair for each question. System B drops the anti-fabrication clause and retains the same no-external-sources policy.

No benchmark comparisons on real Saturn documents, no unsupported claim-level acceptance, no promotion of Ground Truth.

## 2. New source and preliminary independent static check

- New file: `scripts/validation/ds_qv_01_no_hint.py`.
- Immutable source commit from initial creation: `75dff3402034225aa8ca324170bd1aaa23381de4`.
- Git blob at source: `9b9511d53928a7a0ed1d86566f96f2ceed8b69cb`.
- Independently calculated UTF-8 file SHA256 from GitHub content:
  `1e4bf763137bc4082117d9bc2329e4a9ba3f9785075d139bc3dcf5c4d441feb7`.
- Static review confirms separate `--self-test` and six one-request `--trial-N` modes, no batch execution; exact P8 frozen prior assistant answers have expected SHA hashes; only synthetic facts.
- `deepseek-flash`, `thinking.disabled`, `tool_choice:none`, no tools, temperature zero, max output 160, nonstreaming.
- No automatic retries or redirects. Secret key entered locally through hidden getpass; exclusive one-shot marker `O_EXCL` before POST; redacted per-trial JSON produced with tokens, sha, complete bounded preview, observed response model, error flags and estimated cost; no full private P8 state read.
- The script has a local cost gate using six-trial proposed `$0.01` ceiling. This is a **risk-budget design parameter**, **not owner authorization** and **not a provider-enforced cap**.
- Python syntax / `--self-test` execution in the owner's WSL is **NOT YET PERFORMED**; this static review is not a substitute for mandatory owner offline preflight.

## 3. API contract corroboration (official DeepSeek docs, checked 2026-11-18)

- https://api-docs.deepseek.com/api/create-chat-completion/ — Chat Completions `thinking.disabled` is valid; messages carry explicit dialogue history; `tool_choice:none` disables tools; `max_tokens` bounds output; `temperature` is a documented field.
- https://api-docs.deepseek.com/quick_start/pricing/ — `deepseek-flash` peak input cache-hit $0.006/1M, cache-miss $0.30/1M, output $1.20/1M, separate provider invoice.
- Current pricing page identifies a model version for the alias, but **no snapshot/model_revision identifier is provided by the tested response schema**. Do not turn vendor page text into cryptographically pinned model version or assume no alias drift.

## 4. Planned Acceptance gates

1. WSL downloads exactly the pinned source commit and verifies its SHA256.
2. `python3 -m py_compile` PASS.
3. `--self-test` prints six configured cases, two system arms and three question IDs; no DeepSeek traffic or actual API spend.
4. Architecture reviews WSL output and **only then** seeks a separate numeric owner paid GO for `≤6` HTTP and `$0.01` organizational total. Owner's current "continue research" covers **offline study preparation**; no paid numerical authorization was stated.
5. If owner GO is provided, Architecture issues exactly **one** trial command at a time; independent semantic and telemetry review after each trial, saving sanitized evidence/acceptance in existing PR #1 before progressing.
6. Final report distinguishes `no_user_hint_abstention`, `system_guard_effect`, `answerable_control` and user/system prompt effects. A single run per condition does not support any statistical effectiveness rate.

## 5. Governance

Do not modify original P8/P9 evidence, do not reuse prior markers or HTTP budget. No Merge, DS-02, Corpus Freeze, production or uploads of actual Saturn technical documents/GT. `Saturn-Main-Site` READ-ONLY; NEW RAG isolated.

**Next immediate operation:** only owner WSL GitHub source fetch, pin checksum, `py_compile` and `--self-test`. This is **not** a paid DeepSeek trial.
