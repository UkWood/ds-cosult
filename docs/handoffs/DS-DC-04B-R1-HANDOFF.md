# DS-DC-04B-R1 · Отчёт Architecture Session A

**READY FOR ARCHITECTURE REVIEW AND ONE-COMMAND OFFLINE WSL ACCEPTANCE**

**LIVE_NOT_RUN** · Независимая приёмка **NOT RUN** · Экспертная оценка **NOT RUN**

## Версии и материалы

- Принятый baseline `2dac638843b1ce4ac7506de8fb3e3bb222d2199d`.
- Код к независимой приёмке `9f9bb5b489c71daaae309a60d4be6535ce7e64e9`. Лаунчер `scripts/validation/validate_dc04b_r1.py`, Git blob `5e328e699820e02941667bae2a4530da45bbf032`. Отчёт сохранён отдельным коммитом документации в той же ветке. [Draft PR #4](https://github.com/UkWood/ds-cosult/pull/4)
- CRC, точный состав и SHA‑256 всех четырёх членов входного архива подтверждены. SHA‑256 ZIP `7d38da0eec91e8db293267e86c383983a749da54309f4eccb163d1c9c56bf5e7`. SHA‑256 `experiment.json` `062a7656a1afdb324506e80392f8bbba5f2be6282cb4411508501a6e7ce501ff`. Исторический A digest `5fbae4db9a008331e1f1f1314144856b120a65901172f7d48199b38389018c7c`.
- Облачная регрессия `428 passed, 0 failed, 0 skipped` с 371 историческим тестом и 57 новыми. Пин Saturn, публичные PDF и токенизатор проверены. Исторические wire, payload и реестр совпали. Отдельная проверка на публичном PDF со специально собранным синтетическим пакетом дала пять поддержанных связей, две опубликованные пары и `partial`.

Изменения ограничены `ds_dc/{technical_verifier,structural_pdf,evidence_answer,evidence_integration,quality_report}.py`, новым `ds_dc/dc04b_r1_replay.py`, одним лаунчером и новыми `tests/test_dc04b_r1.py`, `tests/test_dc04b_r1_launcher.py` и `tests/test_dc04b_r1_replay.py`. Финансовый код, исторические тесты, permit, прошлый лаунчер, сайт и NEW RAG в scope diff отсутствуют.

## Что изменилось

В принятом экспорте Q01‑N содержались пять технически обоснованных элементов. Все прошли проверки схемы, источника, цитат и применимости. Историческое сравнение полей не признало размещение условия в `subject`, текста ячейки в `value` и пустого `qualifier`. B остался `needs_support`.

R1 допускает ровно описанные наблюдавшиеся формы. Сначала проверяются исходная схема, идентичность данных, соответствие полным цитатам, уникальность связи, применимость и контекст. Кандидат и его идентификаторы сохраняются. Канонизированная копия повторно проходит исходную проверку отношения. Отчёт показывает исходную форму, подтверждённые поля и локаторы, преобразование и итог. Числовой тракт и подтверждённые извлечения проверяются историческими сценариями.

Действие публикуется справочно при подтверждённой причине из той же физической строки, явно привязанной к этой таблице оговорке о квалификации и допустимой форме проверки состояния или дефекта. Методика, последовательность и опасные приёмы не выдаются. Физическая страница 60 таблицы 12 даёт оговорки о квалифицированном персонале, предварительном ознакомлении и заземлении оборудования, подлежащего заземлению. Правила физической страницы 18 ограничивают работы при напряжении. Техническая верификация, публикация, полезность и полнота измеряются отдельно. [Руководство, физическая страница 60](https://www.mnppsaturn.ru/ftp/public/doc/bkd-pk-rf2/re%20BKD-PK-RF2.pdf#page=60) · [Правила безопасности, физическая страница 18](https://www.mnppsaturn.ru/ftp/public/doc/bkd-pk-rf2/re%20BKD-PK-RF2.pdf#page=18)

Исторический `evidence-integration/1` остаётся способом сборки того же wire. Будущий запрос выбирает `prompt_version=FUTURE_PROMPT_VERSION` явно. `evidence-integration/2` задаёт каноническое заполнение полей и собственный wire. Реакция модели на него **NOT RUN**.

## Как проверялось

```bash
env SATURN_SOURCE="$r1_site" DS_DC_CACHE="$r1_cache" \
    SATURN_BKD_PDF="$r1_bkd" SATURN_SLD_PDF="$r1_sld" \
    PYTHONPATH=scripts/validation/dc03c-offline DC03C_GUARD_LOG="$r1_socket_audit" \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 "$r1_python" -m pytest -q -o junit_family=xunit1 \
    --junitxml="$r1_junit"
```

Облако блокирует создание network namespace. Здесь выполнены регрессия с Python socket audit и синтетические проверки. В облаке нет приватного `native-response.bin`, поэтому подлинные B_before и B_after ожидают WSL. Архив владельца использован как историческое доказательство. В облаке не собирался кандидат из экспортированной проекции A.

WSL-лаунчер сверяет SHA закреплённых материалов, сохранённый report digest и исходный кандидат. Два независимых checkout выполняют локальный replay с историческим wire. Результат baseline сверяется с принятым экспортом. Исторический ledger и доказательства сравниваются побайтно до и после. Все вычисления выполняются в network namespace с аудитом Python sockets. Новые операции DeepSeek, расходы и запросы ключа равны нулю. Исторические $0.037337 отражаются как данные DC‑04B.

## Одна команда WSL

Запустить следующий блок целиком. Ожидаемый выходной каталог — `C:\DS-Validation\Reports`. При успешной подготовке единственный ZIP содержит `summary.json`, `checks.json`, `ab-before-after.json`, `integrity.json`, `report.md` и `SHA256SUMS`. При сбое bootstrap ZIP содержит безопасную сводку и её контрольную сумму. Остальные ошибки лаунчера отражаются статусом FAIL или BLOCKED и диагностическим кодом. Автоматический PASS и решение Architecture Session A фиксируются отдельно.

```bash
python3 -I - 9f9bb5b489c71daaae309a60d4be6535ce7e64e9 5e328e699820e02941667bae2a4530da45bbf032 <<'PY'
import hashlib, json, os, subprocess, sys, tempfile, urllib.request, uuid, zipfile
from pathlib import Path

pin, blob = sys.argv[1:]
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix="dc04b-r1-bootstrap-") as directory:
    try:
        url = f"https://raw.githubusercontent.com/UkWood/ds-cosult/{pin}/scripts/validation/validate_dc04b_r1.py"
        with urllib.request.urlopen(url, timeout=30) as response:
            source = response.read(1_000_001)
        git_object = f"blob {len(source)}\0".encode() + source
        if hashlib.sha1(git_object).hexdigest() != blob:
            raise ValueError("launcher_blob_mismatch")
        launcher = Path(directory) / "validate_dc04b_r1.py"
        launcher.write_bytes(source)
    except (Exception, KeyboardInterrupt):
        reports = Path("/mnt/c/DS-Validation/Reports")
        reports.mkdir(parents=True, exist_ok=True)
        output = reports / f"dc04b-r1-bootstrap-{uuid.uuid4().hex}.zip"
        summary = json.dumps(dict(task="DS-DC-04B-R1", status="BLOCKED", failure_code="bootstrap_failed",
                                  pin=pin, launcher_blob=blob, live="LIVE_NOT_RUN", expert_score="NOT RUN",
                                  new_provider_operations=0, new_cost_micro_usd=0)).encode()
        with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("summary.json", summary)
            archive.writestr("SHA256SUMS", f"{hashlib.sha256(summary).hexdigest()}  summary.json\n")
        print(f"DC-04B-R1 ZIP: {output}")
        sys.exit(2)
    result = subprocess.run([sys.executable, "-I", str(launcher), "--commit", pin, "--blob", blob],
                            stdin=subprocess.DEVNULL, check=False)
    sys.exit(result.returncode)
PY
```

**NO MERGE. NO DEPLOY.**
