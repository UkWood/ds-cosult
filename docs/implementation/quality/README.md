# DS-PILOT-02 public question comparison

The 27 Russian questions in `questions.json` are synthetic. The fixture specifies the expected semantic needs, status and minimal source-backed content for the pinned site bundle with no successfully acquired manufacturer PDFs. Q02 replays Q01 as context. All other questions start with an empty referent. The benchmark opens a temporary turn database for each question and never instantiates the paid adapter.

From the repository root with the project environment active, run:

```sh
PYTHONPATH=. python scripts/validation/pilot02_quality.py /path/to/Saturn-Main-Site --data .pilot --output .pilot/quality-p0.json
```

Each output row contains the original question, detected needs, answer status, every published claim, metadata reference or conflict position, and its source location. Citation checks resolve the record identity and compare the citation to the immutable Git bytes, YAML value or physical Markdown lines. The recall denominator counts expected entity/attribute/variant combinations. An engine label of `unknown` does not earn credit for a specific question such as the housing color. Grounded coverage counts answerable needs with every expected content marker present in verified, need-bound objects. A citation for a document listing verifies its metadata only. The abstention metric counts unsupported needs for which the engine published no claim or document for the turn (or the unsupported need in a mixed question). Read it alongside the status and need recall: a missed need can also yield silence. These content markers test selected observations, not the completeness of the entire corpus or every sentence in an answer. Q19 and Q20 ask about wiring diagrams, which are outside the eligible visual channel. Q27 requests a specific physical page from an unavailable manual. Importing eligible PDF bytes changes the corpus and may require a separate gold standard for the page questions.

## Owner-operated paired comparison

Use the interactive live WSL startup from the runbook with the same site/PDF bundle. The deliberately selected subset covers new fields, ordinary and indirect wording, multi-need questions, generations, missing scope, and compatibility. List the exact text and route in the WSL terminal:

```sh
python - <<'PYTHON'
import json
from pathlib import Path
for row in json.loads(Path("docs/implementation/quality/questions.json").read_text()):
    if "owner_route" in row:
        print(row["id"], row["owner_route"], row["question"])
PYTHON
```

For each selected case the owner wants to run, click **Новый диалог**, select the specified P1/P2 experiment route and paste the question exactly. Send it once after reviewing the budget display. A new dialogue isolates its referent and retains earlier records. Use a distinct new dialogue for any interactive P0 repeat. All selected questions are context-free. Fewer than 12 comparisons are valid when the remaining global allowance is smaller, a request errors or the owner stops. A received error counts as an observation. Keep local experiment history until the report has been generated.

```sh
PYTHONPATH=. python scripts/validation/pilot02_quality.py /path/to/Saturn-Main-Site --data .pilot --owner-db .pilot/lab.sqlite --output .pilot/quality-compared.json
```

The comparison opens the owner database read-only, selects completed matching questions, requires identical admitted source manifests and an empty starting referent, and checks the route and durable paid receipt. It includes one paired row per selected turn plus matched-subset summaries. A dispatch intent with missing usage remains an uncertain attempt. If more than one matching owner record exists, use `--requests .pilot/selected.json` with a JSON object mapping case IDs to their chosen local request IDs. The comparer never sends a request or prompts for a key. Keep owner receipts local.

## Recorded offline results

| Metric | Original P0 at `fec0d56` | Expanded P0 |
| --- | ---: | ---: |
| Expected status | 22/27 | 26/27 |
| Semantic needs recalled | 21/28 | 26/28 |
| Answerable needs with all tested content and verified citations | 15/19 | 19/19 |
| Unsupported needs correctly withheld | 8/9 | 9/9 |
| Cited output objects verified | 31/31 | 42/42 |

The expanded import answers Q09 with 16 years from the controller’s `lifetime_years` field. It also answers Q26 with the first-generation component list from the linked 2001–2004 article, including ЛИФТ-3 and К-ЛУЧ. The original P0 abstained on Q09 and requested clarification on Q26. Q24 retrieves the dimensions but marks the conversational lead-in as an unresolved need, producing a partial answer. Q20 identifies a PDF question without recognizing the specific wiring request. Q25 withholds the housing color but labels the need unknown. No owner-operated calls were available for the recorded comparison.

The full expanded responses and citation locations are in `p0-observations.json`. To reproduce the original baseline with the current public fixture and scorer in the same environment:

```sh
baseline_dir=$(mktemp -d)
git archive fec0d56 ds_pilot | tar -x -C "$baseline_dir"
PYTHONPATH="$baseline_dir" python scripts/validation/pilot02_quality.py /path/to/Saturn-Main-Site --output .pilot/quality-original.json
```
