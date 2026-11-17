# DS-LV-02 — Direct DeepSeek Native Tool Conformance v0.2

**Дата:** 2026-11-17  
**Проект:** DS-консультант | Architecture Session A  
**Статус:** READY FOR OWNER APPROVAL OF EXECUTION — **NO PAID CALL AUTHORIZED**  
**Заменяет как детализация:** DS-LV-02 draft v0.1 (сохранён в Git-истории)

## 1. Основание

- ADR-0004 принят: только прямой `https://api.deepseek.com`, модель `deepseek-flash`.
- DS-LV-01 принят с замечаниями: один простой Chat Completions PASS; нативные инструменты НЕ проверены.
- У владельца есть ключ; значение ключа никому не передавать. Никакой запрос не совершать на основании одного документа.
- DS-01C: три PDF закреплены локально в Linux; исходные байты/6 PNG архитектурной сессией независимо не перепроверялись.
- **Этот этап — валидация возможностей, НЕ DS-02 coding / Pilot / Core / production.**

## 2. Что проверяем

Разделить `documented`, `declared`, `actually_invoked`, `completed`, `output_validated`, `billed`, `reproducible`. `HTTP 200` сам по себе означает только принятую HTTP-транзакцию, не PASS результата.

### Фазы, только последовательно

| Фаза | Проверки | Режим | Верхняя граница числа HTTP-запросов (предлагаемая) | Статус |
|---|---|---|---:|---|
| P0 | окружение, синтаксис и цены, fixtures, безопасное хранение ключа | офлайн, без отправки данных | 0 | подготовлено |
| P1 | DSAPI-03 thinking enabled + контроль без web tools | 1 Chat Completion | 1 | НЕ РАЗРЕШЕНО |
| P2 | DSAPI-07 managed Search (raw JSON) | 1 Search request | 1 | НЕ РАЗРЕШЕНО |
| P3 | DSAPI-06 native `deepseek_read_url` | 1 Chat Completion | 1 | НЕ РАЗРЕШЕНО |
| P4 | DSAPI-04 `deepseek_web_search`, thinking disabled | 1 Chat Completion | 1 | НЕ РАЗРЕШЕНО |
| P5 | DSAPI-05 deep thinking + search | 1 Chat Completion | 1 | НЕ РАЗРЕШЕНО |
| P6 | DSAPI-08/09 Files + text/rich recognition | отдельное разрешение на upload/parse+chat+delete | проектно 6 | НЕ РАЗРЕШЕНО |
| P7 | DSAPI-10 OCR synthetic single page | 1 multipart OCR | 1 | НЕ РАЗРЕШЕНО |
| P8 | DSAPI-11 4-turn short dialogue | 4 Chat Completions | 4 | НЕ РАЗРЕШЕНО |
| P9 | DSAPI-12 faults/billing/summary | офлайн анализ + по отдельному запросу диагностика | 0 по умолчанию | НЕ РАЗРЕШЕНО |

**Ни один последующий subgate не начинается, пока предыдущий не проверен Architecture Session A и владелец не разрешил соответствующую платную фазу и бюджет.** Старое GO на $0.01 и один вызов полностью использовано в LV-API-01. Предварительное число вызовов **не является разрешённым лимитом расходов**.

## 3. Официальный Chat Completions контракт

```json
{
  "model": "deepseek-flash",
  "thinking": {"type": "enabled"},
  "messages": [{"role": "user", "content": "Объясни одним предложением смысл аббревиатуры URL."}],
  "max_tokens": 192,
  "stream": false
}
```

Запрос P1: `POST https://api.deepseek.com/chat/completions` с `Authorization: Bearer ...`. Для P4 добавить `tools:[{"type":"deepseek_web_search"}]` и `thinking:{"type":"disabled"}`; для P5 — tools search + thinking enabled. Для P3 указать *только* `tools:[{"type":"deepseek_read_url"}]` и публичный URL `https://example.com/` в **последней пользовательской реплике**. Не устанавливать `tool_choice` в конкретный web tool: DeepSeek не позволяет принудительный вызов этих инструментов.

### Проверка ответа Chat Completions

- `http_status` и наличие JSON top-level `error` (**даже при HTTP 200**).
- `choices[].finish_reason`, content nonempty, `requested_model` / `observed_model`.
- `message.server_tool_calls[].calls[]`: `type`, `kind`, `action`, `status`, `url` / `page`, `signature` presence (не раскрывать encrypted signature в лог).
- `message.annotations[]` для URL citations, их реальная привязка к тексту ответа.
- `usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`; при наличии `usage.server_tool_use`, а также отдельные billed `tool_search`, `tool_fetch`.
- `thinking` requested ≠ достоверно наблюдаемое мышление; учитывать `reasoning_content` и поля thinking tokens, если возвращаются. **Не сохранять скрытые reasoning-тексты для публичной отчётности.**
- Не объявлять `supported`, если инструмент лишь присутствовал в `tools`, но фактического вызова нет. Допустимый статус `DECLARED_NOT_INVOKED` или `INCONCLUSIVE`.
- При множественных web/search вызовах внутри одного запроса стоимость суммируется; HTTP-call count и billed tool operations — разные показатели.

### Ошибки

`400/401/402/403/408/429/5xx`, transport timeout, invalid JSON, incomplete `finish_reason`, top-level `error` при `200`, empty `choices`, not-invoked tool, missing citation, unsupported file type. **Никаких автоматических повторов** и недокументированных исправлений payload во время контрольного прогона. Каждый новый запрос — отдельная authorisation decision.

## 4. Raw Search and Fetch / PDF-OCR contracts

- `POST /v1/tools/search`, поля `query` (1–128 символов), `count` (1–50), `need_content`. Для контролируемого preflight `count:1`, `need_content:false`; не связывать результат автоматически с доверенными техническими фактами.
- Fetch `POST /v1/tools/fetch` требует проверенного точного endpoint body по официальному reference, а не угаданного поля.
- Files `POST /files`: multipart `purpose=text_recognition` либо `rich_layout_recognition`, поле purpose **перед** file. В документации без `expires_after` файл хранится постоянно; для теста указывать `expires_after[anchor]=created_at`, `expires_after[seconds]=3600`. Возвращённый `file_id` использовать в chat, затем `DELETE /files/{file_id}` и проверить `deleted`. Не использовать документы «Сатурна» до авторизации передачи третьей стороне.
- `POST /v1/tools/ocr`: multipart `purpose` + `file`, `pages[].index` 0-based, каждый `finish_reason` проверять; OCR не сохраняется в Files API, но может выставлять оплату за распознанные страницы.

**На P6/P7** синтетический одностраничный документ с общедоступной таблицей/схемой, без логотипов «Сатурна» и реальных клиентских данных; фиксированный SHA-256 local bytes до upload. Сравнение text/rich требует двух отдельных uploads, которые должны быть явно санкционированы.

## 5. Budget and stop policy

**Актуальный тариф на момент подготовки (17.11.2026, DeepSeek official pricing):** Flash peak cache-miss input **$0.30/1M токенов**, output **$1.20/1M**; off-peak **$0.15/1M** и **$0.60/1M**. Search и Fetch **$0.75 за 1,000** операций, PDF parsing/OCR **$0.225 за 1,000 страниц**. Тарифы могут измениться до запуска; обновлять snapshot цены.

Иллюстрация (НЕ price cap): 1,000 prompt tokens + 500 completion tokens по пиковому тарифу `0.0003+0.0006=$0.0009`, плюс 1 search `$0.00075` и 1 fetch `$0.00075` = приблизительно **$0.0024**. Фактический thinking/search/tool count и другие charges могут увеличить сумму; эти вычисления **не доказывают верхнюю границу**.

Сначала предложить владельцу **P1: максимум 1 вызов, денежный лимит по отдельному GO**; затем P2 и т.д. **Нет подтверждённого механизма жёсткой остановки вложенных серверных поисков внутри одного API-вызова**, поэтому `max_tokens` + запрет auto-retry + 1 HTTP-request *не гарантируют* денежный максимум для multi-search; перед P4/P5 отдельно выяснить возможности account-level hard spend/quota либо принимать этот риск явно.

Вести:
```
estimated_max_exposure_usd: not_guaranteed
approved_spend_limit_usd: null  # set only by user GO
observed_billing_usd: null      # set only if verified with billing
usage_token_count: null
billed_search_count: null
billed_fetch_count: null
```

Не предоставлять платный доступ в одной batch-команде на несколько тестов. При ошибках остановиться, **не повторять запрос автоматически**, даже если первоначальный HTTP timeout.

## 6. Security / privacy

Ключ вводить локально с `getpass` без echo, не писать в shell history/argv/GitHub, no `set -x`/verbose. Логи только redacted metadata и проверяемые публичные URLs. Никаких закрытых Core/GT или непубличных оригиналов в API. Файлы `0600`, директории `0700`. PUBLIC `ds-cosult` — только протоколы и sanitized summaries.

## 7. Minimal evidence schema

```json
{
  "test_id": "DSAPI-03",
  "status": "UNTESTED",
  "requested_model": "deepseek-flash",
  "observed_model": null,
  "thinking_requested": "enabled",
  "web_tool_declared": false,
  "web_tool_invoked": false,
  "server_tool_calls": [],
  "citations_verified": null,
  "usage": null,
  "billed_tool_counts": null,
  "actual_billing_usd": null,
  "http_status": null,
  "latency_ms": null,
  "error_type": null,
  "secrets_redacted": true
}
```

Каждый вызов обязан выдать фактический JSON с историей статуса `UNTESTED → PASS/PARTIAL/INCONCLUSIVE/FAIL`, отдельный report для Architecture Session A, с затратами `estimated` / `billed` без путаницы.

## 8. Launch protocol

1. Architecture Session A оформляет *отдельное* разрешение для Linux/WSL выполнения фазы P1 после принятия количества и суммы у владельца.
2. Linux Session проверяет working tree read-only, URL / PDF / logs, выдаёт **одну команду** и дожидается результата.
3. Локальный `getpass` + один HTTP-request, безопасный сокращённый отчёт.
4. Architecture Session A проводит независимый gate review, документирует, затем решает, нужен ли P2.
5. Никакого Merge, DS-02, Pilot или Corpus Freeze в рамках DS-LV-02.
