# DS-LV-02 / P1 — Owner-Authorized Deep Thinking Smoke Check

**Дата решения:** 2026-11-17  
**Статус:** **OWNER GO FOR ONE P1 REQUEST ONLY — NOT YET EXECUTED**  
**Разрешённый лимит:** **$0.01 USD**, один прямой DeepSeek Chat Completions вызов.  
**Основание:** владелец ответил «Разрешаю, продолжай» на предложение одной P1-проверки с лимитом $0.01.  
**Задание Linux/WSL:** `scripts/validation/ds_lv_02_p1_thinking.py` — публичный код без ключа.

## 1. Scope

- Endpoint: `POST https://api.deepseek.com/chat/completions`, модель `deepseek-flash`.
- `thinking={"type":"enabled"}`, default high reasoning, `max_tokens=512`, `stream=false`.
- Вопрос с известным ответом: «Что больше: 9.11 или 9.8? Ответь только числом». Ожидаемый ответ: 9.8.
- **Только один HTTP POST**, без инструментов, Search, Fetch, PDF/OCR/Files, приложенных источников и автоматического retry.
- Следующие P2..P9 **NOT AUTHORIZED**. Новый GO нужен отдельно.

## 2. Execution contract

Исполнять в Linux/WSL только после загрузки и инспекции точного скрипта из GitHub рабочей ветки. Скрипт содержит `getpass`: ключ вводится локально без эха и не записывается в GitHub, аргументы команды, shell history или отчет.

1. Проверить Python и файл, создать защищённую папку `$HOME/ds-consult-validation/logs`, `umask 077`.
2. Проверить отсутствие `logs/ds-lv-02-p1-redacted.json`, иначе **STOP — no rerun**.
3. Однократно выполнить `python3 scripts/validation/ds_lv_02_p1_thinking.py` из локальной проверенной копии.
4. Передать Architecture Session A **только redacted JSON**, без raw response, reasoning text, ключа, персональных данных, session cookies.
5. При любом HTTP/timeout/parse failure остановиться; **нового вызова не делать**.

### Evaluation
- HTTP 200 + `observed_model=deepseek-flash` + `finish_reason=stop` + ответ 9.8 + наличие непустого `reasoning_content` → PASS.
- HTTP 200, но нет `reasoning_content` или неверный ответ → PARTIAL (не притворяться, что thinking доказан).
- HTTP error, top-level error, timeout, parse error → BLOCKED/FAIL.
- `reasoning_content` не записывать; метаданные и количество символов достаточны для этого smoke.
- `completion_tokens` обычно включает reasoning tokens; не путать их с длиной финального текста.
- Денежную оценку считать **ориентировочной**, не фактическим billing.

## 3. Cost control

Официальный Flash peak pricing на 2026-11-17: cache-miss input $0.30 за 1M, output $1.20 за 1M. При `max_tokens=512`, если входных токенов до 500, ориентировочный пиковый верх расчёта model tokens: `500*0.30/1e6 + 512*1.20/1e6 = $0.0007644`. Нет web tool и file parsing charges. Но это **не банковский/аккаунтный hard spending cap**, тариф и побочные накладные расходы проверить по факту, запрос не повторять. Прекратить работу после единственного запроса.

## 4. Evidence

`$HOME/ds-consult-validation/logs/ds-lv-02-p1-redacted.json` (0600):
- test ID, authorisation, exact model, thinking_requested, max_tokens, HTTP, finish_reason, result, observed_model, answer, presence and length of reasoning, usage, conservative peak cost estimate, latency.
- No API key, raw reasoning or unreviewed model output except safe short answer.
- Store outcome in GitHub only after architecture review; current status remains NOT YET EXECUTED.

## 5. Official references

- https://api-docs.deepseek.com/guides/thinking_mode/
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/quick_start/pricing/

No Merge / No DS-02 / No production.
