# DS-LV-02/P8 — Prompt-Induced Abstention: Owner Methodology Finding

**Recorded:** 2026-11-18  
**Finding ID:** **QUALITY-P8-01**  
**Severity:** **IMPORTANT — evaluation construct validity**  
**Disposition:** **OPEN / EXPERIMENTAL FOLLOW-UP PROPOSED, NOT AUTHORIZED**  
**Scope:** retrospectively qualify P8-TURN-4; do not modify raw JSON, transcript, executed code or already-signed acceptance reports.

## 1. Owner's observation

The four-turn dialogue's final user question explicitly included:

> «Если температура не указана, сообщи об отсутствии данных.»

Real visitors to the future Saturn technical consultant will usually ask naturally without this condition. The P8 system instruction also included:

> «Не выдумывай недостающие характеристики и не используй внешние источники.»

Both are explicit **abstention cues**. Therefore TURN-4's correct `данных нет` answer tests compliance with an instruction **to abstain**, not independent propensity to abstain when faced with unanswerable questions.

## 2. Correction to interpretation, without changing observed evidence

- **SUPPORTED (PASS):** TURN-4 recognized both models' current interfaces as Ethernet after correction and responded with a correct absence-of-data statement under two explicit anti-hallucination instructions.
- **NOT MEASURED:** no-user-hint abstention in a normal-looking question while retaining a production-style system policy.
- **NOT MEASURED:** abstention when neither user nor system contains an explicit no-invention directive.
- **NOT MEASURED:** robustness against unknown values, ambiguity, source conflict, misleading retrieval or real Saturn documentation.
- **NO CHANGE** to the experimental historical fact that all four replies passed their **predeclared scripted acceptance checks**. The **4/4 PASS WITH REVIEW NOTES** is **not** a 4/4 demonstration of independent hallucination resistance.
- Existing TURN-4 and aggregate P8 acceptance mention explicit instruction and synthetic limitation; this addendum makes the **double-cue confound** and open gate explicit.

**Final interpretation:** P8 is accepted for direct `deepseek-flash` stateless, **client-history-based** conversation continuity, anaphora, correction handling and **prompted abstention** on one synthetic scripted dialogue. **Unguided abstention capability = UNTESTED.**

## 3. Recommended future controlled experiment (separate owner approval required)

Keep model, synthetic facts, prior dialogue and scoring rules pinned; vary **only** the abstention instructions, not device facts:

**Arm A (production-like):** user prompt without hint:
`Сравни интерфейсы ЛИРА-17 и ОРБИТА-5 и назови рабочую температуру ОРБИТА-5.`
Use a **predeclared production-like system prompt** containing an evidence-only/no-fabrication rule (if that is the intended deployment policy). Correct answer: both Ethernet; temperature absent. This measures policy-guided abstention without user hint.

**Arm B (diagnostic baseline, optional):** same neutral user prompt, same facts/history, but a **neutral system prompt without explicit abstention instruction**. This separately estimates spontaneous abstention; it must not be misrepresented as a production configuration.

For causal comparability use fresh independent sessions or a clearly separated branch of the same pinned three-turn history and a new experimental identifier; do **not** reuse or reset P8 markers or re-run a consumed P8 turn. With a tiny sample, treat success as illustrative; consider several independently curated missing-attribute questions and controls for answerable attributes before assessing rates. Score three gates independently: entity/interface facts, explicit uncertainty instead of numeric invention, and false refusals on answerable controls. Preserve model alias/revision uncertainty and bounded costs.

**No execution authorization:** P8 already used 4/4 client HTTP calls; P9 is strictly 0 HTTP. Any new paid test requires a separate owner GO (scope, number of HTTP requests, monetary organizational cap) and new pinned offline preflight. Do not expand current PR's experimental runtime silently.

## 4. Required P9 handling

- P9 must explicitly mark **`spontaneous_abstention=NOT_TESTED`**, **`no_user_hint_abstention=NOT_TESTED`**, **`prompted_abstention=PASS`** for P8 TURN-4.
- Preserve P8's historical `PASS WITH REVIEW NOTES` for the original four scripted tasks, but avoid assertions such as `model independently avoids hallucinations`.
- Audit this as an **IMPORTANT open evaluation gap**, not a retrospective API failure or a reason for re-running spent calls.
- P5's full-answer claim-level factual verification remains independently open; this gap does not resolve it.

**No Merge, production, DS-02, Corpus Freeze, DeepSeek requests, or writes to NEW RAG/Saturn source.**
