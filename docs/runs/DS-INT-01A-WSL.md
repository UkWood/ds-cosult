# DS-INT-01A в WSL

Статус исходных PDF в облачной сессии `NOT_EXECUTED_IN_CODEX`. Выполняйте команды из независимого checkout или worktree с head Draft PR #3 после R0-CR01. Зафиксируйте точный SHA через `git rev-parse HEAD` и убедитесь, что status чистый. Чтобы повторить исторический R0 с форматом v1, используйте отдельный checkout на `90e4691453fc239352c8345e15f6c4c71ca7629b`; результаты храните в другом каталоге. После установки зависимостей сам ledger работает локально. Исходники и результаты храните вне Git.

```bash
set -eu
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt

(
  cd "$HOME/saturn-pdf"
  sha256sum -c <<'PINS'
030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a  bkd.pdf
f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f  sldks.pdf
PINS
)

export SATURN_SOURCE="$(realpath ../saturn-pilot-source)"
git -C "$SATURN_SOURCE" cat-file -e 084d759487bfab6e111549c9b5469711ac5fc13e^{commit}
export SATURN_BKD_PDF="$HOME/saturn-pdf/bkd.pdf"
export SATURN_SLD_PDF="$HOME/saturn-pdf/sldks.pdf"
umask 077
run_dir="$(mktemp -d "$HOME/ds-int-01a.XXXXXX")"
git rev-parse HEAD > "$run_dir/code-head.txt"
set -o pipefail
python -m pytest -q -rs | tee "$run_dir/pytest.txt"
python -m pip freeze > "$run_dir/python-environment.txt"
python -m ds_pilot.experimental.evidence_ledger \
  --pdf-dir "$HOME/saturn-pdf" --output "$run_dir/ledger"
(cd "$run_dir/ledger" && sha256sum -c SHA256SUMS)
cat "$run_dir/ledger/report.md"
python - "$run_dir/ledger/context_trace.json" <<'PYCODE'
import json
import sys
from pathlib import Path

trace = json.loads(Path(sys.argv[1]).read_text())
assert trace["schema"] == "experimental/ds-int-01a/2"
assert trace["metrics"]["published_verified_claims"] == 0
assert trace["coverage_state"] == "partial_index"
for case in trace["control_cases"]:
    print(case["case"], case["reason_code"], case["evidence_ref_scope"], case["candidate_scope"])
PYCODE
```

В `SATURN_SOURCE` нужен локальный Git-объект закреплённого коммита. Если его ещё нет, подготовьте отдельный read-only clone через `git clone --no-checkout https://github.com/UkWood/Saturn-Main-Site.git ../saturn-pilot-source`. Этот checkout нужен существующему suite. Для ledger достаточно двух PDF и проверенного манифеста из ветки. Код возврата CLI 1 означает, что хотя бы один документ заблокирован. Причину смотрите в `receipts`. Код 0 означает проверку байтов и количества физических страниц обоих документов. Состояние покрытия остаётся `partial_index`.

## Независимая R1-проверка и карточки DS-EVIDENCE-10

Для каждой записи в `context_trace.json` сверяйте исходный PDF и цепочку `source_document_id → scope_context.*.provenance[].evidence_id → attribute_evidence_id / evidence_id` с полным `diagnostics.json`. Поля provenance указывают физическую страницу, literal, SHA-256 и правило. На странице продолжения отдельно проверьте надпись, номер таблицы, соседство страниц и повтор заголовков. Для Q22 сверяйте scope АРМ, для Q24 каждый блок отдельно, для Q15 выполняйте обе проверки варианта. Проверьте, что записи с риском потери условий или сносок остаются `requires_review`. `MATCH` означает сопоставление scope, а значения и применимость утверждений сверяются независимо.

Счётчики scope в `metrics` суммируют решения по явно заданным контрольным запросам. Одна запись может учитываться в нескольких запросах. Знаменатели для EvidenceRef и пар различаются. Подсказки `label_hints` сужают только диагностический список для просмотра. Если список пуст, сверяйте все `evidence_ids` и `blocked_regions` на контрольных страницах, а также `tables` и `unresolved_rows` в diagnostics. При отсутствии положительных связей зафиксируйте, где оборвалась цепочка — caption, геометрия, заголовки, продолжение или scope. Запишите причину даже при 0 MATCH. Не рассчитывайте долю от всех локаторов как долю распознанных фактов.


Сформируйте локальный список точных областей для сверки. Для каждой из 35 карточек из локального CSV DS-EVIDENCE-10 откройте соответствующую физическую страницу оригинала, сопоставьте геометрию и буквальный текст, запишите ID карточки, номер страницы, таблицу и строку или текстовый блок, evidence ID, точный вариант и причину расхождения или UNKNOWN. Отчёт из архива содержит сводку, а полный набор карточек нужен из локального аналитического прогона. При отсутствии точной ячейки оставьте UNKNOWN. При продолжении таблицы или объединённой ячейке сверяйте её визуально в оригинале. Ручное наблюдение здесь остаётся диагностикой и не переключает статусы ledger.

```bash
python - "$run_dir/ledger/diagnostics.json" > "$run_dir/review-regions.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
assert data["metrics"]["published_verified_claims"] == 0
assert sorted((r["document"], r["physical_pages"]) for r in data["receipts"]) == [
    ("bkd.pdf", 65), ("sldks.pdf", 83)]
bkd, sld = (r["sha256"] for r in data["receipts"])
cases = {"N09": (sld, {7, 34}), "Q15": (sld, {7, 34}), "Q21": (sld, {34, 35}),
         "Q22": (sld, {25}), "Q24": (sld, {15}), "N10": (bkd, {4}),
         "N11": (sld, {7}), "Q11": (sld, {60})}
print(json.dumps({
    case: [ref for ref in data["evidence"]
           if ref["pdf_bytes_sha256"] == digest and ref["physical_page"] in pages]
    for case, (digest, pages) in cases.items()
}, ensure_ascii=False, indent=2))
PY
```

| Карточка | Что сопоставить с оригиналом |
|---|---|
| N09 | Указанная модель и вариант на стр. 7 и 34 против запрошенной СЛДКС-2 |
| Q15 | Две строки с частотой, отдельно общий scope и вариант без ПК |
| Q21 | Продолжение таблицы 13, условия ИБП и режим работы |
| Q22 | Отдельные строки RAM и HDD с исходными единицами и ограничениями |
| Q24 | Два блока, принадлежность питания и явное отрицание |
| N10 | Строка массы БКД и её ограничение. Отсутствие в shortlist не подтверждает отсутствие в источнике |
| N11 | Диапазон лифтов и его привязка к АРМ. Применяется то же правило покрытия |
| Q11 | Независимые ветви проверки Link и условия применения каждого действия |

Сохраните локальные наблюдения в `review-notes.md` внутри `run_dir`, затем сформируйте контрольные суммы для передачи Architecture Session A.

```bash
(cd "$run_dir" && sha256sum ledger/* code-head.txt pytest.txt python-environment.txt review-regions.json review-notes.md > RESULTS-SHA256SUMS)
(cd "$run_dir" && sha256sum -c RESULTS-SHA256SUMS)
```
