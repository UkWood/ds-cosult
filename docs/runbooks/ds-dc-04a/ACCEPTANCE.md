# DS-DC-04A · Offline Acceptance и подготовка GO

Используйте прежние WSL cache, подлинный исторический Q01 и Python 3.12 из `~/ds-dc03b-validation/`. Закреплённый checkout Saturn передаётся отдельным путём. Подготовительный Git fetch и проверка blob выполняются до сетевого ограничения. Подставьте точные SHA HEAD и Git blob из сообщения о поставке и выполните один блок:

```bash
dc04a_commit='<HEAD из сообщения о поставке>' dc04a_blob='<Git blob из сообщения о поставке>' dc04a_boot="$(mktemp -d)" &&
git -C "$dc04a_boot" init --quiet --template= &&
git -C "$dc04a_boot" fetch --quiet --no-tags --no-recurse-submodules https://github.com/UkWood/ds-cosult.git refs/heads/feat/ds-dc-01-document-centric-pilot &&
git -C "$dc04a_boot" show "$dc04a_commit:scripts/validation/validate_dc03c.py" > "$dc04a_boot/validate.py" &&
test "$(git -C "$dc04a_boot" hash-object --no-filters "$dc04a_boot/validate.py")" = "$dc04a_blob" &&
python3 -I "$dc04a_boot/validate.py" --prepare --commit "$dc04a_commit" --site "$HOME/ds-dc02-cal-validation/Saturn-Main-Site"
```

Если fetch или сверка blob завершается ошибкой, код лаунчера не запускается. ZIP формируется после запуска проверенного лаунчера.

По желанию добавьте `--financial-ledger /absolute/path/to/existing/private/ledger-directory`. Preflight читает существующие файлы под read-only lock и показывает остатки лимитов и статус исходной операции. При отсутствии приватного ввода проверка ledger остаётся NOT RUN. Системный namespace предпочтителен, `--network namespace` делает его обязательным. Совместимый fallback фиксирует Python socket audit. Прежние `--cache`, `--fixture`, `--python`, `--wsl-root` и `--extra-tests` сохраняются. Runner формирует один проверенный ZIP в `C:\DS-Validation\Reports`, в том числе при обычном отрицательном результате. Безопасный A/B mock по синтетическому источнику прилагается как JSON и Markdown. Score модели остаётся NOT RUN. [Регламент DC-03C-R2](../ds-dc-03c/OFFLINE-WSL.md)

## Допуск DC-04B

Команда `python -m ds_dc.quality_lab live` относится к отдельному закрытому входу. На поставке DC-04A она возвращает `live_not_authorized` до чтения ключа, ledger или HTTP. Для будущего отдельного решения:

1. Повторно сверить HEAD, manifest, порядок файлов, question/request, logical wire и payload digest. Зафиксировать актуальную модель, версию, тарифы, JSON/usage, native parser, TTL, правила биллинга и caps по официальным материалам с датой и SHA договора.
2. Прочитать фактический общий ledger. Сверить CAL-INC-01 с окончательным биллингом или письменным подтверждением провайдера о конкретной операции. Подтверждённое начисление или подтверждённый ноль требуют отдельно утверждённого append-only события, сохраняющего попытку и 65 страниц. При остающейся неопределённости hold и блокировка сохраняются. [План сверки CAL-INC-01](../ds-dc-02/CAL-INC-01-RECOVERY-DRAFT.md)
3. Утвердить остаточный риск и одноразовый permit, привязанный к реализации, manifest, request/wire, договору, fingerprint ключа, account/project, существующему ledger, expiry, операциям и caps. Ключ вводится локально скрытым запросом после GO. Предложение предусматривает 4 upload / 80 страниц и 1 chat, 0 status/delete/retry. Резерв 348 000 микроUSD не является доказанным пределом. REVIEWED_BOUNDS остаются пустыми.
4. После отдельного утверждения и реализации допуска предрезервировать одну попытку в том же campaign. Учесть известное usage при невалидном JSON и сохранить hold при неопределённой операции. Публичный маршрут сохраняется.

## Ручная карточка Q01-N

Проверить каждую позицию независимо в A и B, отличая утверждение факта, дословную выдержку и ссылку. Для потерянных корректных фактов указать причину. Возможные причины включают применимость, отсутствующее доказательство, проверку связи, рендеринг и уместное ограничение безопасности. [Независимый эталон Q01-N](../ds-dc-03b/ground-truth.md)

| Ручная оценка | A | B |
|---|---|---|
| Корректные факты, ошибочные и неподтверждённые утверждения | NOT RUN | NOT RUN |
| Полнота относительно эталона | NOT RUN | NOT RUN |
| Утраты корректных фактов и причины | — | NOT RUN |
| Полезность, доступность ссылок, модальность и безопасность | NOT RUN | NOT RUN |

Вывод относится к конкретному вопросу. Время и usage записываются отдельно от экспертного вывода.
