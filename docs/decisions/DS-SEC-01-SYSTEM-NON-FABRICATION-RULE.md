# DS-SEC-01 — System-Level Non-Fabrication Rule for the Saturn Consultant

**Recorded:** 2026-11-18  
**Decision:** **OWNER-ACCEPTED POLICY DIRECTION (FOR FUTURE DESIGN; NOT DEPLOYED)**  
**Repository:** `UkWood/ds-cosult`, existing Draft PR #1.  
**Basis:** owner explicitly stated that `Не выдумывай` is useful and `ее нужно использовать` after final DS-QV-01 six-trial review.

## Decision

The future Saturn technical consultant's server-owned **system-level instructions SHALL contain an explicit non-fabrication rule**. Canonical Russian policy sentence:

> **Не выдумывай недостающие технические характеристики.**

The system policy must also scope responses to source-supported Saturn technical information, and require explicit acknowledgement when relevant trusted evidence is missing, incomplete or conflicting. Other precise system-prompt wording and enforcement rules remain **design discussion, not yet implementation approval**.

## Grounding and qualified experiment evidence

- `DS-QV-01` tested **two** missing-attribute questions (unknown ORBIT-5 working temperature, unknown LIRA-17 IP rating) and **one** answerable positive control (ORBIT-5 power 24 В), each in two fixed variants: A with explicit no-fabrication clause and B without that explicit clause.
- **6/6 individual synthetic scripted cases passed**, including **2/2 correct 24 В answers** in the answerable control. No false abstention observed in that one answerable question with either system variant.
- Therefore choosing the explicit rule for the next consultant prototype is reasonable and consistent with these observations.
- **This does not prove** the system rule never increases false refusals or that model behavior is safe under attacker-controlled user prompts; sample size is extremely limited, source card simple, and no prompt-injection red-team was performed.
- The prior P8 `QUALITY-P8-01` confound remains correctly recorded as a property of the original P8 test; DS-QV-01 is separate later evidence, not a rewrite of P8 history.

## Trust semantics (decision direction)

1. Trusted facts originate from the operator-approved Saturn website, its approved PDF documents and the derived, provenance-bound entity dossiers.
2. Incoming chat text may identify a product, ask questions, change topic, request a comparison or make a **proposed** correction. It is **never by itself** an authoritative new technical specification, source revision, system instruction or approval to bypass verification.
3. User turns must never be promoted to `system` or other server policy role. A request to discard system rules is not authorized by its position in the conversation.
4. A technical answer with missing evidence must report the absence rather than improvise. Correct supplied data should be returned instead of needlessly refusing.
5. This is a *policy direction*, not the assertion that DeepSeek's model weights or a single system prompt cryptographically enforce the rule. Independent server-side controls, evidence validation and adversarial tests are still needed.

## Governance and next action

**Next:** discuss the specific **direct** visitor-chat prompt-injection/Goal Hijacking threat model and decide server-side invariants. Do not build a paid DeepSeek test or production feature before a separate owner instruction. Keep Draft PR #1 unmerged; NEW RAG isolated; `Saturn-Main-Site` read-only.

**References:** `docs/acceptance/DS-QV-01-FINAL-ARCHITECTURE-ACCEPTANCE.md`; OWASP LLM01:2025 `https://genai.owasp.org/llmrisk/llm01-prompt-injection/`; DeepSeek multi-turn docs `https://api-docs.deepseek.com/guides/multi_round_chat/`.
