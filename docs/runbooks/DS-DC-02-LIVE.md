# DS-DC-02 · Протокол закрытого пилота

**Действие сейчас** · CAL-PREP. После отдельного GO владелец запускает один CAL-01 в доверенной WSL. Обычный live остаётся за строгим допуском. [Решение A-DS-DC-04](../architecture/A-DS-DC-04-CONTROLLED-CALIBRATION.md)

## Пакет freeze

- [Манифест байтов и связей](../reports/ds-dc-02/corpus-manifest.json) · site pin `084d759487bfab6e111549c9b5469711ac5fc13e`, 11 Markdown, 14 уникальных PDF, 483 физических страницы. `manifest_sha` — SHA-256 канонического JSON из команды `--freeze`: `13fd98159f05809c019dd11a522b1c87fff3faebc505621bde7318880e3051f9`.
- [Набор вопросов](ds-dc-02/live-questions.json) · SHA-256 файла `eda83041d26a32871860d3581fc363e6a3a61f73e8e47e560aa8d93c99dabee0`. [Опоры для независимой сверки](ds-dc-02/ground-truth.md) хранятся отдельно от входа модели.
- [Оценки входа](../reports/ds-dc-02/sizing.json) · локальный токенизатор и Poppler. Сверить состав хешей, редакции, locator, возможный объём OCR и таблиц. Страницы с иным поколением или компонентом требуют явной применимости.
- HEAD для GO — точный подтверждённый SHA поставки CAL-PREP в Draft PR #4. База CAL-PREP — `a4bcd85c8d371306815fb8a9f9c11bc72a82ee3f`. Манифест должен совпасть после восстановления исходников и оригиналов.

## Проверочный интерфейс

В доверенной Linux/WSL среде установить Git, curl, Poppler, `prlimit` и Python 3.12. Из корня DC-02 checkout выполнить:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt

export SATURN_SOURCE=/absolute/path/to/Saturn-Main-Site
export DS_DC_CACHE=/absolute/private/path/to/dc02-cache
install -d -m 700 "$DS_DC_CACHE"
git -C "$SATURN_SOURCE" rev-parse HEAD
# Команда скачивает только 14 закреплённых оригиналов у издателя.
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" --fetch \
  --freeze "$DS_DC_CACHE/corpus-manifest.json"
```

Положить локальный [токенизатор V4.1](https://github.com/deepseek-ai/deepseek-recipe/blob/935817c66f5d6e64838f419692545f06787e485f/static/tokenizers/v41/tokenizer.json) в `$DS_DC_CACHE/deepseek-v41-tokenizer.json` и сверить SHA-256 `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99`. Содержимое кэша и приватного финансового реестра хранится вне Git.

```sh
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" --chat
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" \
  --question 'Какая масса у БКД-ПК-RF.2?' --question 'Условия хранения?'
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" \
  --p0 --question 'Где документация СЛДКС-1?'
```

Для чата открыть `http://127.0.0.1:8765`. В проверочном режиме ответ модели имитируется, а выбираемые оригиналы и маршрутизация реальные. «Новый диалог» сбрасывает память сценария и оставляет дневной счётчик и реестр файлов. Если собственник выбирает ограниченную область по явному предложению интерфейса, запустить с `--reference-only` и использовать отдельный манифест этой области. Сравнение с full_available ведётся по исходному составу.

Воспроизведение на полном доступном freeze:

```sh
export SATURN_BKD_PDF="$DS_DC_CACHE/030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a.pdf"
export SATURN_SLD_PDF="$DS_DC_CACHE/f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f.pdf"
python -m pytest -q --tb=short
env -u DEEPSEEK_API_KEY python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" \
  --evaluate-dc02 /tmp/dc02-eval
cmp /tmp/dc02-eval/corpus-manifest.json docs/reports/ds-dc-02/corpus-manifest.json
```

Если `--fetch` вернул неполный freeze, сравнить манифесты и восстановить ровно недостающий оригинал по закреплённому URL, SHA и числу страниц. СЛД РЭ на 83 страницы может потребовать более 25 секунд. Утверждать новый неполный freeze как полный нельзя.

## Строгий допуск для ordinary и прежнего режима calibration

1. Проверить удалённый HEAD PR #4, чистый checkout согласованной реализации, два манифеста и SHA оригиналов. Зафиксировать дату, ревьюера, текущий контракт модели, тарификацию всех разрешённых операций, лимиты разбора и поведение на ошибках. [Публичные цены](https://api-docs.deepseek.com/quick_start/pricing/) · [Контракт Files](https://api-docs.deepseek.com/guides/document_parsing/) · [Контракт Chat](https://api-docs.deepseek.com/api/create-chat-completion/)
2. Получить доказанную границу полного тарифицируемого входа для каждого утверждённого wire, включая нативную экспансию, служебное оформление, систему, историю и реакцию провайдера на слишком длинный вход. Для калибровки потребуется отдельная доказанная верхняя граница цены, включая случаи неопределённого или отказавшего запроса. Опубликованное окно 1M и 8 МиБ разобранного текста оставляют эту часть контракта открытой. Сначала согласовать доказательство с Architecture Session A и внести утверждённые записи в `REVIEWED_BOUNDS` под новым проверенным SHA.
3. Отдельно собрать приватный `contract.json` с официальными ссылками `rates_evidence` и `paid_operation_evidence`, датой Unix `reviewed_at`, `reviewer`, `origin`, `model`, `parser`, `model_context_max`, `generation_max`, `rates` и `approved_bound_ids`. Каждая запись в коде связывает SHA запроса без file handles, SHA манифеста и обоснованные пределы `billable_input` и `parsed_bytes_max`. Для калибровки вид доказательства `provider_billable_maximum` привязан к точному wire. Обычный запрос допускает `complete_input_bound` для точного wire или `complete_scope_bound` для утверждённой области с произвольным вопросом и историей в пределах отдельно доказанного конверта. Этот конверт связывает `scope_sha256` и `wire_bytes_max`, причём проверка байтов лишь подтверждает принадлежность к утверждённой области доказательства. Доступные поля структуры зафиксированы в [адаптере](../../ds_dc/native.py).
4. В приватном GO владелец утверждает `run`, `kind` (`regular`, `calibration` либо отдельный `cleanup`), `head`, `manifest_sha`, `contract_sha`, `ledger_path`, `account`, `project`, `key_sha256`, `rates`, `expires` и `limits`. `expires` — Unix до 24 часов с момента сверки провайдера. Путь реестра абсолютный, общий для всех этапов пилота, с отдельным каталогом 0700. Файл GO — 0600. Хеши contract и manifest считают на каноническом JSON через `ds_dc.corpus.encoded`. Сохранить счётчики предыдущих фаз. Одобренное расходование отображается в USD через целые микроUSD в реестре.
5. Владелец предоставляет ключ в доверенной среде через переменную `DEEPSEEK_API_KEY`. Команда платной фазы возможна только после шагов выше и отдельного GO.

```sh
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" \
  --manifest "$DS_DC_CACHE/corpus-manifest.json" --contract "$DS_DC_CONTRACT" \
  --live-go "$DS_DC_GO" --ledger "$DS_DC_LEDGER" --chat
```

CLI принимает тот же комплект с `--question` вместо `--chat`. Калибровка возвращает только операторские показатели и остаётся вне памяти диалога. Затем требуется новое решение на обычный запуск.

## Controlled Calibration в доверенной WSL

### 1. Закрепить исходники, корпус и проверить TLS

Выполнить локальную установку из раздела «Проверочный интерфейс». Использовать чистый checkout из PR #4 на точном SHA, который владелец подтверждает в GO. Перед загрузкой PDF сверить site pin. Архив, который прошёл `--freeze`, представляет полный доступный набор из двух утверждённых досье.

```sh
set -e
umask 077
unset DEEPSEEK_API_KEY
export DS_DC_HEAD='<точный опубликованный SHA CAL-PREP>'
test "$(git rev-parse HEAD)" = "$DS_DC_HEAD"
test -z "$(git status --porcelain)"
test "$(git -C "$SATURN_SOURCE" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
test "$(sha256sum docs/runbooks/ds-dc-02/live-questions.json | cut -d ' ' -f 1)" = eda83041d26a32871860d3581fc363e6a3a61f73e8e47e560aa8d93c99dabee0
test "$(sha256sum "$DS_DC_CACHE/deepseek-v41-tokenizer.json" | cut -d ' ' -f 1)" = 81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99
manifest_sha=$(python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" --fetch \
  --freeze "$DS_DC_CACHE/corpus-manifest.json")
test "$manifest_sha" = 13fd98159f05809c019dd11a522b1c87fff3faebc505621bde7318880e3051f9
cmp "$DS_DC_CACHE/corpus-manifest.json" docs/reports/ds-dc-02/corpus-manifest.json
timeout 12 openssl s_client -connect api.deepseek.com:443 \
  -servername api.deepseek.com -verify_hostname api.deepseek.com \
  -verify_return_error -brief </dev/null
```

TLS-проверка обрывается до HTTP. Нативный клиент использует прямой маршрут (`trust_env=False`). Если не прошёл любой шаг, остановиться до ввода ключа. В случае повторной проверки уже восстановленного корпуса можно убрать `--fetch`, сохранив проверку freeze и SHA.

### 2. Оформить и выполнить GO строго на CAL-01

По отдельному GO владелец подтверждает реальный аккаунт/проект, общий приватный журнал, актуальные DeepSeek Flash, тарифы и риск начислений сверх $0,33/POST. Тарифы проверить по официальным ссылкам ниже. Выбрать **один** каталог ledger для всей кампании и сохранить его для дальнейших фаз. Если кампания уже использует ledger, передать именно этот путь, сверив финансовую историю. Команды выполнять в Bash без `xtrace`, в файловой системе WSL с правами Unix.

```sh
set +x
export DS_DC_PRIVATE="$HOME/.local/state/ds-dc02"
export DS_DC_LEDGER="$DS_DC_PRIVATE/ledger"
export DS_DC_CAL_ID=Q01
export DS_DC_CONTRACT="$DS_DC_PRIVATE/contract-$DS_DC_CAL_ID.json"
export DS_DC_GO="$DS_DC_PRIVATE/go-$DS_DC_CAL_ID.json"
install -d -m 700 "$DS_DC_PRIVATE" "$DS_DC_LEDGER"
read -r -p 'DeepSeek account label: ' DS_DC_ACCOUNT
read -r -p 'DeepSeek project label: ' DS_DC_PROJECT
read -r -p 'Owner reviewer: ' DS_DC_REVIEWER
read -r -p 'Enter ACCEPT for this GO after reviewing the terms and residual risk: ' DS_DC_RISK
test "$DS_DC_RISK" = ACCEPT
read -rs -p 'DeepSeek API key: ' DEEPSEEK_API_KEY
printf '\n'
export DS_DC_ACCOUNT DS_DC_PROJECT DS_DC_REVIEWER DS_DC_RISK DEEPSEEK_API_KEY
trap 'unset DEEPSEEK_API_KEY' EXIT

python - <<'PYGO'
import json
import os
import time
from pathlib import Path
from ds_dc.context import OUTPUT
from ds_dc.corpus import digest, encoded
from ds_dc.finance import RATES
from ds_dc.native import CAL_MANIFEST, CAL_POST_RESERVE, CAL_WIRES, CONTROLLED_CAL, MODEL_CONTEXT, ORIGIN
from ds_dc.runtime import PURPOSE

env = os.environ
if env["DS_DC_RISK"] != "ACCEPT" or not env["DEEPSEEK_API_KEY"] or not env["DS_DC_REVIEWER"].strip():
    raise SystemExit("Owner consent, key and reviewer are required")
cal_id = env["DS_DC_CAL_ID"]
wire_sha, uploads, pages = CAL_WIRES[cal_id]
now = int(time.time())
contract = dict(origin=ORIGIN, model="DeepSeek-V4.1-Flash-1017", rates=RATES,
                model_context_max=MODEL_CONTEXT, generation_max=OUTPUT, parser=PURPOSE,
                reviewed_at=now, reviewer=env["DS_DC_REVIEWER"], approved_bound_ids=[],
                rates_evidence="https://api-docs.deepseek.com/quick_start/pricing/",
                paid_operation_evidence="https://api-docs.deepseek.com/guides/document_parsing/")
go = dict(kind=CONTROLLED_CAL, cal_id=cal_id, wire_sha256=wire_sha,
          accepted_residual_risk=True, expires=now + 3600, run="dc02-cal-" + cal_id,
          head=env["DS_DC_HEAD"], account=env["DS_DC_ACCOUNT"], project=env["DS_DC_PROJECT"],
          ledger_path=str(Path(env["DS_DC_LEDGER"]).resolve()), rates=RATES,
          key_sha256=digest(env["DEEPSEEK_API_KEY"].encode()),
          contract_sha=digest(encoded(contract).encode()), manifest_sha=CAL_MANIFEST,
          limits=dict(budget=CAL_POST_RESERVE + pages * int(RATES["page"]),
                      normal=0, extended=1, chats=1, pages=pages, upload=uploads,
                      status=0, delete=0, calibration=1))
if cal_id == "Q02":
    go["cal01_permit_sha"] = env["DS_DC_CAL01_PERMIT_SHA"]
if Path(env["DS_DC_GO"]).exists():
    raise SystemExit("GO already exists. Preserve the permit and ledger and review the previous attempt.")
Path(env["DS_DC_CONTRACT"]).write_text(json.dumps(contract), encoding="utf-8")
with Path(env["DS_DC_GO"]).open("x", encoding="utf-8") as f:
    json.dump(go, f)
PYGO

DS_DC_QUESTION=$(python -c 'import json,os; from pathlib import Path; data=json.loads(Path("docs/runbooks/ds-dc-02/live-questions.json").read_text()); print(next(q["question"] for q in data["questions"] if q["id"] == os.environ["DS_DC_CAL_ID"]))')
python -m ds_dc --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE" \
  --manifest "$DS_DC_CACHE/corpus-manifest.json" --contract "$DS_DC_CONTRACT" \
  --live-go "$DS_DC_GO" --ledger "$DS_DC_LEDGER" --question "$DS_DC_QUESTION" \
  > "$DS_DC_PRIVATE/result-$DS_DC_CAL_ID.json" || {
    unset DEEPSEEK_API_KEY
    printf '%s\n' 'CAL stopped. Inspect private result and ledger. Do not retry.'
    exit 1
  }
unset DEEPSEEK_API_KEY
```

Код вернёт ненулевой статус при остановке. Result и `ledger.json` содержат приватные данные. Результат первой попытки сверить в локальном терминале.

```sh
env -u DEEPSEEK_API_KEY python - <<'PYRESULT'
import json
import os
from pathlib import Path
from ds_dc.native import CAL_WIRES

ledger = Path(os.environ["DS_DC_LEDGER"]) / "ledger.json"
state = json.loads(ledger.read_text())
key = "dc02-live/calibration/" + CAL_WIRES[os.environ["DS_DC_CAL_ID"]][0]
receipt = state["operations"].get(key)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
PYRESULT
```

Сверить `state=settled`, `calibration_result.finish_reason=stop`, usage, стоимость, четыре upload и фактическое списание в кабинете владельца. Проверить черновик и локаторы по GT01. При drift, unknown, отказе до POST, превышении резерва, несовпадении начисления или иной остановке сохранить журнал, GO и результат и остановить эксперимент. Не редактировать ledger и не повторять операцию.

### 3. CAL-02 только после нового решения владельца

Только после успешной сверки CAL-01 и получения отдельного GO установить `DS_DC_CAL_ID=Q02` в шаге 2, сохранить тот же `DS_DC_LEDGER` и подтвердить параметр `DS_DC_CAL01_PERMIT_SHA` значением `permit_sha` из просмотренной записи CAL-01:

```sh
read -r -p 'Reviewed CAL-01 permit_sha: ' DS_DC_CAL01_PERMIT_SHA
export DS_DC_CAL01_PERMIT_SHA
```

Затем повторить шаг 2 с новым файлом GO, свежим подтверждением риска и тем же аккаунтом/проектом/ключом. Проверить 10 upload на 403 страницы и GT02. Q10 union вне программы. Ключ вводится только локально.

| Операция | Локальный резерв |
|---|---:|
| Q01, 1 POST и 4 PDF / 80 страниц | $0,348000 |
| Q02, 1 POST и 10 PDF / 403 страницы | $0,420675 |
| Два extended-слота, 0 GET/List/DELETE, 0 retry | $0,768675 |

Приведённые суммы регулируют локальный допуск. Внешний расход может оказаться выше. Для обычных вопросов по окончании CAL действует самостоятельный строгий допуск. [Цены](https://api-docs.deepseek.com/quick_start/pricing/) · [Документы и разбор](https://api-docs.deepseek.com/guides/document_parsing/)

## Критерии и остановка

- **PASS** · правильная тема и доступная область, сохранён весь вопрос, по принятому D1 ровно одна попытка, все запрошенные аспекты независимо подтверждены. Проверить SHA и редакцию, физическую страницу/строку/таблицу, дословную опору, единицу, квалификатор, условия и область компонента. Для уточнения или отказа требуются ожидаемый маршрут и ноль API-операций.
- **partial** · одна часть подтверждена, остальные явно перечислены как открытые. Для подключения, электропитания, метрологии, схем и разных поколений требуется сверка специалистом с оригиналом, даже при совпадении цитаты.
- **fail** · приняты неподтверждённые характеристики, потеряна часть вопроса, подменена модификация, потеряна идентичность файла или тема перешла между сессиями. **BLOCKED** · доказанная граница не позволяет отправить или доказательства границы и тарифа отсутствуют.
- Немедленно остановить серию при unknown, overage, неожиданной тарифицируемой операции, drift контракта/входа, неправильном источнике или нарушении лимита. Сохранить удержание, журнал операций и исходные элементы для сверки. Повтор и разблокировка требуют решения владельца по биллингу и идентификатору операции.
- После приёмки для удаления использовать отдельный GO с новым run, `kind=cleanup`, `cleanup_sha` равным закреплённому SHA PDF, `limits.delete=1` и остальными лимитами 0. Передать `--cleanup-sha <проверенный SHA>` с теми же `--manifest`, `--contract` и `--ledger`. Успех требует ответа с совпадающим ID и `deleted:true`. Отдельная сверка отсутствия в аккаунте допустима только по заранее одобренному провайдерскому протоколу. Хранить ключ, handles и частные журналы в доверенной среде владельца.
