# DS-LV-01 — Linux/WSL Validation Assignment

**Проект:** DS-консультант — МНПП «Сатурн»  
**Репозиторий долговременной памяти:** https://github.com/UkWood/ds-cosult  
**Рабочая документация:** Draft PR #1, ветка `docs/ds-01c-benchmark-memory`  
**Дата:** 17 ноября 2026  
**Исполнитель:** отдельная Linux/WSL Validation Session через команды, выполняемые владельцем  
**Архитектура и независимая приёмка:** Architecture Session A  
**Статус:** READY FOR CONTROLLED OWNER-OPERATED VALIDATION  
**Правило:** NO MERGE. NO PRODUCTION. NO FULL BENCHMARK. NO MODIFICATION OF TRUSTED SITE OR NEW RAG.

## 1. Основание и цель

Владелец подтвердил, что **прямой DeepSeek API key уже имеется**, но сам ключ никому не передавал. ADR-0004 определяет **прямой DeepSeek API**, без AI Tunnel. Цели этой Linux/WSL-сессии:

1. **LV-PDF-01:** скачать три публичных оригинала технических PDF, закрепить их SHA-256 и физические страницы, сверить выборочные таблицы/рисунки с предварительным веб-просмотром;
2. **LV-API-01:** при отдельном явном разрешении владельца на минимальный платный запрос проверить прямое подключение к DeepSeek API и модель `deepseek-flash`.

Треки независимы: отсутствие подтверждённого ключа не блокирует PDF, а неудачная загрузка PDF не мешает отдельной проверке chat API. **Никакое выполнение DSAPI-01 не означает проверку native Search, Deep Thinking, Files API, OCR или всего DS-02.**

## 2. Правила Linux Validation Session

- Давать владельцу **только один безопасный логический блок команд за раз**; после каждой команды/пакета запросить результат и анализировать его прежде следующего шага. Не требовать выполнить весь документ одним копированием.
- Нельзя спрашивать, просить показать или вставить DeepSeek API key в ChatGPT. Ключ вводится **только в интерактивном Linux/WSL терминале без эха**, не сохраняется в файлы, history, GitHub, отчёты, логи.
- Не использовать `set -x`, `curl -v`, echo переменной с ключом, `.env` в репозитории, скриншоты терминала с ключом, автоповторы платных запросов.
- Все материалы в отдельном каталоге `$HOME/ds-consult-validation` в Linux FS, **не** в `/mnt/c/` и **не** в Git clone. `umask 077`.
- Не изменять `UkWood/Saturn-Main-Site`, `UkWood/LLM-RAG-chat-bot` или `main` проекта. Рабочие scripts допускаются только временно в изолированной Linux папке.
- PDF/PNG не пушить в PUBLIC GitHub без отдельной проверки прав. В GitHub позже можно перенести только согласованный redacted manifest.
- Любой unexpected HTTP/JSON/PDF error: `BLOCKED`, ничего не заменять молча и не менять provenance.
- Обязательный **отдельный GO/NO-GO владельца** перед **каждым** новым классом платных DeepSeek-вызовов. Текущий LV-API-01 предусматривает только *один* короткий базовый Chat Completions вызов, без tools, uploads и retrieval; согласовать потолок расходов и права аккаунта до выполнения.

## 3. Контрольные ссылки и baselines

### Git
- Memory repo `UkWood/ds-cosult`, Draft PR #1.
- Trusted site `UkWood/Saturn-Main-Site`, commit candidate `084d759487bfab6e111549c9b5469711ac5fc13e`, tree `a5297822bf3a5e071b10cc1dca553481c1b84d47`. Site — READ-ONLY.
- Evidence seeds: `docs/research/DS-01C-PDF-EVIDENCE-SEEDS.md`.

### Public PDF originals (no DeepSeek upload on LV-PDF-01)
| File | URL | Page-count reference (unverified bytes) |
|---|---|---|
| `sos95_re.pdf` | `https://www.mnppsaturn.ru/ftp/public/doc/sos-95/re%20SOS-95.pdf` | 195 |
| `sldks1_re2011_p1.pdf` | `https://www.mnppsaturn.ru/ftp/public/doc/sldks/re%20SLDKS-1%20p1(3).pdf` | 83 |
| `easdkiu_re.pdf` | `https://www.mnppsaturn.ru/ftp/public/doc/iis/re_iis.pdf` | 79 |

Numbers are observations in a prior web PDF viewer, **not a frozen identity**. If a download differs, report drift, do not substitute.

### DeepSeek
- `https://api.deepseek.com/chat/completions`, Bearer authentication, `model: deepseek-flash` (official alias to V4.1 Flash at preparation date).
- Official docs: https://api-docs.deepseek.com/en/ , https://api-docs.deepseek.com/guides/web_tools/ , https://api-docs.deepseek.com/guides/files_api/ .
- W/A/B/C0 and B-text/B-entity experimental protocol unchanged. Actual direct API capabilities still UNTESTED.

## 4. LV-ENV-01 — Environment and tool readiness (NO API COST)

Linux/WSL Validation Session must start with this block only:

```bash
umask 077
mkdir -p "$HOME/ds-consult-validation"/{pdf,logs,evidence_png}
chmod 700 "$HOME/ds-consult-validation"
cd "$HOME/ds-consult-validation"
date -u +'%Y-%m-%dT%H:%M:%SZ'
uname -a
python3 --version
curl --version | head -n 1
command -v pdfinfo || true
command -v pdftoppm || true
```

If pdfinfo or pdftoppm is missing, ask owner before doing:
`sudo apt-get update && sudo apt-get install -y poppler-utils file`.
Do not execute a package install speculatively if these tools already exist.

**Exit criteria:** Linux identity, curl, Python, PDF tools present; permissions controlled.

## 5. LV-PDF-01 — Download and byte pin (NO API COST)

After LV-ENV-01 PASS, execute:

```bash
set -euo pipefail
cd "$HOME/ds-consult-validation/pdf"

curl --fail --location --retry 2 --connect-timeout 15 --max-time 180 \
  --output sos95_re.pdf \
  'https://www.mnppsaturn.ru/ftp/public/doc/sos-95/re%20SOS-95.pdf'
curl --fail --location --retry 2 --connect-timeout 15 --max-time 180 \
  --output sldks1_re2011_p1.pdf \
  'https://www.mnppsaturn.ru/ftp/public/doc/sldks/re%20SLDKS-1%20p1(3).pdf'
curl --fail --location --retry 2 --connect-timeout 15 --max-time 180 \
  --output easdkiu_re.pdf \
  'https://www.mnppsaturn.ru/ftp/public/doc/iis/re_iis.pdf'

file --mime-type sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf
sha256sum sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf | tee SHA256SUMS.txt
wc -c sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf
pdfinfo -v 2>&1 | head -n 2
for f in sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf; do
  echo "========== $f =========="
  pdfinfo "$f" | grep -E '^(Pages|Page size|PDF version|Encrypted|Title|CreationDate):'
done
```

**Critical:** If curl fails halfway, save the error and stop before interpreting an incomplete PDF. Avoid changing filename/URL silently. After original bytes pinned, repeat `sha256sum -c SHA256SUMS.txt` on the same files, then keep files unchanged for the page checks.

## 6. LV-PDF-02 — Physical pages, tables and diagrams

After hash and format PASS:

```bash
set -euo pipefail
cd "$HOME/ds-consult-validation"
pdftoppm -f 9  -l 9  -singlefile -scale-to 1600 -png pdf/sos95_re.pdf          evidence_png/sos95_p009
pdftoppm -f 7  -l 7  -singlefile -scale-to 1600 -png pdf/sldks1_re2011_p1.pdf evidence_png/sldks_p007
pdftoppm -f 18 -l 18 -singlefile -scale-to 1600 -png pdf/sldks1_re2011_p1.pdf evidence_png/sldks_p018
pdftoppm -f 3  -l 3  -singlefile -scale-to 1600 -png pdf/easdkiu_re.pdf       evidence_png/easdkiu_p003
pdftoppm -f 4  -l 4  -singlefile -scale-to 1600 -png pdf/easdkiu_re.pdf       evidence_png/easdkiu_p004
pdftoppm -f 12 -l 12 -singlefile -scale-to 1600 -png pdf/easdkiu_re.pdf       evidence_png/easdkiu_p012
ls -lh evidence_png/
(cd pdf && sha256sum -c SHA256SUMS.txt)
```

Compare visually; **do not OCR as a substitute for visual/source checking**:

- SOS-95, physical p.9, table 2: one ray without УСЛ ≤2 km, with УСЛ ≤10 km (scope/units carefully preserved).
- SLDKS-1, physical p.7, table 1: up to 255 address blocks for one master ray; cable ≤3 km coax, ≤1 km twisted pair without repeater. Physical p.18 has the named structure and table/figure, check variant conditions.
- EASDKIU, p.3 purpose, p.4 table of meters/interfaces, p.12 architecture diagram, roles of PostgreSQL/LanMon; diagram arrows require independent review.

For every evidence candidate return `CONFIRMED`, `AMBIGUOUS`, `CONTRADICTED` or `NOT_CHECKED` and the exact source page/table/figure. This **does not confer expert-approved GT**.

Create a short manifest with URL, file name, bytes, SHA-256, physical pages, review timestamp, PDF tool/version, review status. Local report may include complete file paths; GitHub text report must not embed proprietary images/binaries.

## 7. LV-API-01 — One minimum DIRECT API connectivity check (PAID, EXPLICIT GO REQUIRED)

**Only after owner explicitly approves one low-cost API call and its spending limit.** Availability of a key is not this authorization. No key is needed for LV-ENV or LV-PDF.

For maximum key safety, use a single interactive Python process: it asks for the key with terminal echo disabled using `getpass`, never places it on a shell command line, never writes it to `.env` and never prints it.

```bash
umask 077
cd "$HOME/ds-consult-validation"
python3 - <<'PY'
import getpass
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

key = getpass.getpass("DeepSeek API key (hidden): ")
if not key:
    raise SystemExit("BLOCKED: empty API key")

payload = {
    "model": "deepseek-flash",
    "thinking": {"type": "disabled"},
    "messages": [
        {"role": "user", "content": "Ответь одним словом: как называется столица Франции?"}
    ],
    "max_tokens": 48,
    "stream": False
}
body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(
    "https://api.deepseek.com/chat/completions",
    data=body,
    headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json"
    },
    method="POST"
)
started = time.monotonic()
status = {"test_id": "LV-API-01", "gateway": "direct", "model_requested": "deepseek-flash"}
try:
    with urllib.request.urlopen(req, timeout=45) as response:
        status["http_status"] = response.status
        parsed = json.load(response)
    status["response_id"] = parsed.get("id")
    status["model_observed"] = parsed.get("model")
    choices = parsed.get("choices") or []
    status["finish_reason"] = choices[0].get("finish_reason") if choices else None
    status["answer_preview"] = (
        (choices[0].get("message") or {}).get("content") or ""
    )[:120] if choices else None
    status["usage"] = parsed.get("usage")
    status["result"] = "PASS" if status["http_status"] == 200 and choices else "PARTIAL"
except urllib.error.HTTPError as exc:
    status["http_status"] = exc.code
    status["result"] = "BLOCKED_HTTP_ERROR"
except Exception as exc:
    status["result"] = "BLOCKED_TRANSPORT"
    status["error_type"] = type(exc).__name__
finally:
    key = None
    status["latency_ms"] = round((time.monotonic()-started)*1000)
    out = Path("logs/lv-api-01-redacted.json")
    out.parent.mkdir(mode=0o700, exist_ok=True)
    out.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(out, 0o600)
    print(json.dumps(status, ensure_ascii=False, indent=2))
PY
```

**STOP after one call.** No automatic second invocation, no retries, no web search, no thinking test, no Files upload, no OCR. Record HTTP 401, 402, 403, 429, 5xx distinctly. A technical failure should not trigger silently repeated charges. A `200` baseline PASS validates only basic Chat Completions, **not** search/Files/Deep Thinking.

## 8. DSAPI advanced — design only, NOT in LV-API-01

Future separately approved tests:
- DSAPI-03: thinking on/off; preserve observed reasoning metadata;
- DSAPI-04/05: `deepseek_web_search` and thinking+web; model decides whether to invoke and may use multiple tool calls;
- DSAPI-06: `deepseek_read_url`;
- DSAPI-07: Search & Fetch raw APIs;
- DSAPI-08/09: `POST /files` PDF `text_recognition` / `rich_layout_recognition`;
- DSAPI-10: OCR `POST /v1/tools/ocr`;
- DSAPI-11/12: continuity, errors, billing and safety.

Uploads can incur parsing charges and persist on server; never upload the Saturn originals or restricted corpus until user authorizes transmission/retention and the cost limit. Test files should be public or synthetic.

## 9. Evidence bundle / report handoff

Deliver **to Architecture Session A**, in a single self-contained message, not just terminal logs:

```text
DS-LV-01 — Final Linux/WSL Validation Report
Date and environment:
Source repositories and pinned site SHA:
LV-ENV-01: PASS/PARTIAL/BLOCKED + versions
LV-PDF-01: result; 3 exact URLs; file bytes; SHA-256; page counts
LV-PDF-02: result; checked pages and facts; ambiguous cases
LV-API-01: NOT_AUTHORIZED / PASS / PARTIAL / BLOCKED; HTTP status; model observed; usage; latency; NO SECRET
Deviations, errors and reproducibility:
Public manifest files:
Summary by BLOCKER / IMPORTANT / MINOR:
Recommendation: ACCEPT PDF PIN / REQUEST CORRECTIONS / NEEDS EXPERT REVIEW
NO MERGE / NO PRODUCTION / NO BENCHMARK FREEZE
```

Even if one track fails, report what was verified; do not replace with guessed values. Report *must* state explicitly that `expert_approved` is still pending and that no full DSAPI conformance or DS-02 was run.

## 10. Acceptance criteria

| Gate | PASS condition |
|---|---|
| LV-ENV-01 | Ubuntu/WSL info, curl, Python, Poppler tools recorded |
| LV-PDF-01 | Three original bytes pinned, SHA-256 + size, PDF format/pages |
| LV-PDF-02 | Six physical page images rendered and reviewed, file hashes stable |
| LV-API-01 | ONLY after explicit approval: single HTTP 200 Chat Completions, model/usage/latency recorded, no leaked key |
| DS-01C Evidence | Candidate evidence promoted only to byte-pinned status; **expert approval remains a separate task** |
| Security | No keys, hidden Core/GT or restricted PDF bytes in public commits or user-visible logs |

**No Merge. No changes to NEW RAG or Saturn-Main-Site. No production deployment. No hidden benchmark runs.**
