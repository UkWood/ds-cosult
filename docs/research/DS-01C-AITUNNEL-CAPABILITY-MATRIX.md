# DS-01C — AI Tunnel Capability Matrix v0.1

Дата: 2026-11-17. Источник: официальная документация провайдера. **Documented ≠ Runtime Verified**.

| Capability | Contract / field | Evidence | Status |
|---|---|---|---|
| OpenAI Chat Completions | `POST /v1/chat/completions` | https://aitunnel.ru/docs | DOCUMENTED |
| Bearer auth | `Authorization: Bearer sk-aitunnel-…` | https://aitunnel.ru/docs | DOCUMENTED, secret unavailable |
| DeepSeek V4.1 Flash | `deepseek-v4.1-flash` | https://aitunnel.ru/models/deepseek-v4-1-flash | DOCUMENTED, account untested |
| Version-pinned model candidate | `deepseek-v4.1-flash-1017` | https://aitunnel.ru/faq/kak-podklyuchit-deepseek-v4-1-flash-1017 | DOCUMENTED, exact routing not verified |
| DeepSeek official alias | `deepseek-flash` | https://api-docs.deepseek.com/guides/web_tools/ | DIRECT API ONLY; gateway mapping unverified |
| Reasoning | `reasoning: {enabled:true}` / effort | https://aitunnel.ru/docs/reasoning | DOCUMENTED generic; behavior on chosen model untested |
| Gateway web search | `tools: [{type:"aitunnel:web_search"}]` | https://aitunnel.ru/docs/web-search | DOCUMENTED, actual model invocation untested |
| Search engine choice | `engine: auto/native/exa/parallel/perplexity` | https://aitunnel.ru/docs/web-search | DOCUMENTED; native not guaranteed |
| Search domain allowlist | `allowed_domains` for gateway search (engine dependent) | https://aitunnel.ru/docs/web-search | DOCUMENTED with caveats, not replacement for trusted source gate |
| Gateway PDF input | `type:file`, `file_data`: URL or base64 | https://aitunnel.ru/docs/pdf | DOCUMENTED, model-specific path untested |
| Gateway PDF parsing | `plugins: [{id:"file-parser",pdf:{engine:"mistral-ocr"}}]` or cloudflare-ai | https://aitunnel.ru/docs/pdf | DOCUMENTED, no input file verified |
| Reasoning raw metadata | `message.reasoning`, usage fields | https://aitunnel.ru/docs/reasoning | DOCUMENTED, response-specific |
| Usage / cost | `usage.cost_rub` | https://aitunnel.ru/docs/models | DOCUMENTED, key-specific |
| Downstream provider policy | `provider.only`, `allow_fallbacks:false`, `require_parameters:true` | https://aitunnel.ru/docs/provider | DOCUMENTED, no live verification |
| Native DeepSeek web tools | `deepseek_web_search`, `deepseek_read_url` | https://api-docs.deepseek.com/guides/web_tools/ | NOT CONFIRMED via AI Tunnel |
| Native DeepSeek Search & Fetch | direct `/v1/tools/search` and `/v1/tools/fetch` | https://api-docs.deepseek.com/guides/search/ | NOT CONFIRMED via AI Tunnel |
| Native DeepSeek OCR / Files | DeepSeek-specific APIs | https://api-docs.deepseek.com/ | NOT CONFIRMED via AI Tunnel |

## Risks
1. Auto route may select a different downstream provider, altering latency, price, modalities and parameter support.
2. Unsupported parameters may silently be ignored unless `require_parameters:true`; a 200 response does not prove the requested tool or thinking mode operated.
3. Gateway PDF preprocessing can send input to third-party OCR engine, not necessarily to the claimed model directly.
4. Gateway search citations may differ from DeepSeek-native search and from trusted corpus sources.
5. Public price pages and FAQ examples show inconsistent prices; use current catalog and billed `usage.cost_rub`, not static inferred costs.
6. Tool outputs and model reasoning metadata may be absent even when capability is available; classify independently.

## Exact test data rules
Do not use hidden Core or non-public site files for capability smoke tests. Prepare public tiny examples, locally scoped synthetic text, and publicly permitted PDFs. Key values never logged.
