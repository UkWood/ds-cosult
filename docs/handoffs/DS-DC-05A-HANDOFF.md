# DS-DC-05A · Отчёт Architecture Session A

**READY FOR ARCHITECTURE REVIEW AND ONE-COMMAND OFFLINE WSL ACCEPTANCE**

**LIVE_NOT_RUN** · Личная оценка **NOT RUN** · Операции DeepSeek **0** · Новые расходы **0** · **NO MERGE · NO PUBLIC DEPLOY**

## Поставка и охват

- Принятый R1 `9f9bb5b489c71daaae309a60d4be6535ce7e64e9`, baseline PR `c8e0ed0e1122e3a17781c4a5497bbc4c8830d38b`. Код 05A для приёмки `847d7cc47ff9208adfd9e33fa78b61d66a518d68`. Отчёт добавлен отдельным коммитом документации. [Draft PR #4](https://github.com/UkWood/ds-cosult/pull/4)
- У входного ZIP R1 проверены CRC, состав и пять SHA‑256. SHA‑256 архива `31f7c098c74020002312b647ad38e726a63f780686bb35eb73c9ced2ba00106f`. Приёмка владельца зафиксировала 428 тестов, десять PASS, baseline 0/5, R1 5/5 и публикацию обеих условных пар. [Решение A-DS-DC-12](../architecture/A-DS-DC-12-OWNER-DRIVEN-PRACTICAL-EVALUATION.md)
- Сайт `084d759487bfab6e111549c9b5469711ac5fc13e`, manifest `13fd98159f05809c019dd11a522b1c87fff3faebc505621bde7318880e3051f9`. БКД‑ПК‑RF.2 — 4 PDF и 80 страниц, СЛДКС‑1 — 10 уникальных PDF и 403 страницы. Сайт использован read-only. Scope diff оставляет NEW RAG, финансовые модули, исторические тесты, permit и старые лаунчеры за пределами изменений.

## Рабочий тракт

Код стенда добавлен в `ds_dc/trial.py`, `trial_native.py`, `trial_web.py`, `trial_journal.py` и браузерные файлы `trial.html`, `trial.js`, `trial.css`. Приёмка и запуск используют отдельные скрипты в `scripts/validation/`. Пять файлов `tests/test_dc05a_*.py` проверяют границы и сквозной тракт.

FastAPI-интерфейс соединён с принятым resolver, подбором досье, R1 и детерминированной выдачей. Submit получает устойчивый ID до отправки. Смена изделия разделяет историю. Недоступные PDF исключаются с пометкой об ограничении, сохраняются пригодные источники. При превышении EXTENDED владелец может явно выбрать основное руководство СЛДКС‑1. Действуют NORMAL 128k, EXTENDED 256k, OUTPUT 8192 и лимит 20 PDF.

Нативный адаптер использует `evidence-integration/2` и `candidate-answer/2.1`. На одну отправку приходится не более одного chat. PDF загружаются по необходимости. Проверенные handles привязаны к исходнику и учётной области до истечения TTL. R1 проверяет ответ по текущим wire, досье и реестру. Изменение принятого модуля интеграции ограничено выделением общей функции верификации. Историческое построение v1 сохраняется.

Посетитель видит B и проверенные ссылки. Эксперт отдельно видит очищенный A, B, причины отказов, применённые документы и телеметрию. Запросы и редакции человеческой оценки сохраняются отдельными приватными Markdown-записями. Сырой ответ провайдера в стенде не сохраняется. Очищенный экспорт в Windows выполняется явным действием. [Запуск, остановка и обратная связь](../runbooks/DS-DC-05A-OWNER-TRIAL.md)

## Provider Contract и активация

Официальная документация проверена 23 ноября 2026 года в 08:13 МСК. Контракт `80d43e4731235e7867de31b55269524231989f17b8de506157d73ff0dee6916d` действует до 23 декабря 2026 года, 08:13 МСК. Закреплены Direct API, `deepseek-flash` / DeepSeek‑V4.1‑Flash‑1017, Thinking enabled/high, JSON, `text_recognition` и TTL 3600 секунд. Пиковые ставки за миллион токенов — $0,006 при попадании в кэш, $0,30 при промахе, $1,20 за вывод. Парсинг — $0,225 за 1000 страниц. [Тарифы](https://api-docs.deepseek.com/quick_start/pricing/) · [Chat](https://api-docs.deepseek.com/api/create-chat-completion/) · [Files](https://api-docs.deepseek.com/api/create-file/) · [Парсинг](https://api-docs.deepseek.com/guides/document_parsing/) · [Thinking](https://api-docs.deepseek.com/guides/thinking_mode/)

Перед активацией владелец подтверждает приёмку и актуальность условий, сам задаёт лимит на запуск и один раз скрыто вводит API-ключ. Терминал показывает локальную ссылку с одноразово сгенерированным кодом доступа на текущий запуск. Код доступа отделён от ключа провайдера. Учёт расходов ведётся в отдельном атомарном состоянии. Резерв допуска рассчитывается по пределу модели и новым страницам. Неопределённое начисление блокирует новые платные операции, в том числе после перезапуска. [DeepSeek Usage](https://platform.deepseek.com/usage)

## Проверки

- **500 passed, 0 failed, 0 skipped**, включая 428 исторических. Использованы закреплённые публичные материалы и Python socket audit. Три ASGI-отправки прошли до MockTransport и R1. Проверены два mock upload, три mock chat, переиспользование handle, уточнение, смена изделия, F5, оценка и экспорт.
- Chromium в облаке подтвердил работу офлайн-интерфейса, каталога, явной отправки, F5 и переключения экспертного режима. Внешних запросов страницы не наблюдалось. В отдельной синтетической проверке браузера подтверждён код доступа к локальной live-сессии.
- Облачный Linux не предоставил network namespace. Подлинный повтор R1 с приватным исходником и независимая приёмка 05A запускаются в WSL владельца. Новый prompt в live, фактический DeepSeek Usage и браузер Windows через WSL — **NOT RUN**.

Облачная команда проверки использовала `SATURN_SOURCE`, `DS_DC_CACHE`, `SATURN_BKD_PDF`, `SATURN_SLD_PDF` на закреплённые материалы и `DC03C_GUARD_LOG` на приватный журнал сокетов.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=scripts/validation/dc03c-offline \
    python -m pytest -q -o junit_family=xunit1 --junitxml="$dc05a_junit"
```

## Бесплатная независимая приёмка WSL

Лаунчер `scripts/validation/validate_dc05a.py`, blob `7c82330232b599126a564377d888a43a98fdc530`. После бесплатного GitHub fetch вычисления проходят в отдельном namespace с аудитом Python sockets. Принятый ZIP R1 обнаруживается в Windows Reports или рядом с подготовленными WSL-материалами. При другом размещении доступен `--r1-report`. Результат — один ZIP в `C:\DS-Validation\Reports` со статусом PASS, FAIL или BLOCKED. Члены архива — `summary.json`, `checks.json`, `integrity.json`, `ui-pipeline-feedback.json`, `report.md`, `SHA256SUMS`.

```bash
python3 -I - 847d7cc47ff9208adfd9e33fa78b61d66a518d68 7c82330232b599126a564377d888a43a98fdc530 <<'PY'
from hashlib import sha1, sha256
import json, os, subprocess, sys, tempfile, urllib.request, uuid, zipfile
from pathlib import Path

pin, blob = sys.argv[1:]
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix="dc05a-accept-") as work:
    try:
        path = "scripts/validation/validate_dc05a.py"
        url = f"https://raw.githubusercontent.com/UkWood/ds-cosult/{pin}/{path}"
        with urllib.request.urlopen(url, timeout=30) as remote:
            data = remote.read(1_000_001)
        if sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != blob:
            raise ValueError("bootstrap_blob_mismatch")
        launcher = Path(work) / "validate_dc05a.py"
        launcher.write_bytes(data)
    except (Exception, KeyboardInterrupt):
        report_dir = Path("/mnt/c/DS-Validation/Reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        zip_path = report_dir / f"dc05a-bootstrap-{uuid.uuid4().hex}.zip"
        summary = dict(task="DS-DC-05A", status="BLOCKED", failure_code="bootstrap_failed",
                       pin=pin, launcher_blob=blob, live="LIVE_NOT_RUN", new_cost_micro_usd=0,
                       operations=dict.fromkeys(("upload", "chat", "status", "delete", "retry", "key_prompts"), 0))
        def encoded(record):
            return json.dumps(record, ensure_ascii=True).encode() + b"\n"
        files = {"summary.json": encoded(summary), "checks.json": encoded({"bootstrap": "BLOCKED"}),
                 "integrity.json": encoded({"pin": pin, "launcher_blob": blob}),
                 "ui-pipeline-feedback.json": encoded({"status": "BLOCKED"}),
                 "report.md": b"# DS-DC-05A - BLOCKED\n\nbootstrap_failed\n"}
        sums = "".join(f"{sha256(body).hexdigest()}  {name}\n" for name, body in files.items()).encode()
        with zipfile.ZipFile(zip_path, "x", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
            archive.writestr("SHA256SUMS", sums)
        with zipfile.ZipFile(zip_path) as archive:
            assert archive.testzip() is None
            assert all(archive.read(name) == content for name, content in files.items())
            assert archive.read("SHA256SUMS") == sums
        print(f"DC-05A ZIP: {zip_path}")
        sys.exit(2)
    result = subprocess.run([sys.executable, "-I", str(launcher), "--commit", pin, "--blob", blob],
                            stdin=subprocess.DEVNULL, check=False)
    sys.exit(result.returncode)
PY
```

## Запуск рабочего стенда после решения Architecture Session A

Лаунчер `scripts/validation/launch_dc05a.py`, blob `511772419f8111cd80890e637efed4a3caae817c`. Запустите блок из терминала WSL. Откройте напечатанную локальную ссылку. Остановка — **Ctrl+C**. Удаление `--live` в последней строке запуска открывает офлайн-режим.

```bash
python3 -I - 847d7cc47ff9208adfd9e33fa78b61d66a518d68 511772419f8111cd80890e637efed4a3caae817c <<'PY'
from hashlib import sha1
from pathlib import Path
import os, subprocess, sys, tempfile, urllib.request

pin, blob = sys.argv[1:]
os.umask(0o077)
path = "scripts/validation/launch_dc05a.py"
url = f"https://raw.githubusercontent.com/UkWood/ds-cosult/{pin}/{path}"
with tempfile.TemporaryDirectory(prefix="dc05a-owner-") as work:
    with urllib.request.urlopen(url, timeout=30) as remote:
        data = remote.read(1_000_001)
    if sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != blob:
        sys.exit("bootstrap_blob_mismatch")
    launcher = Path(work) / "launch_dc05a.py"
    launcher.write_bytes(data)
    result = subprocess.run([sys.executable, "-I", str(launcher), "--commit", pin, "--blob", blob, "--live"])
    sys.exit(result.returncode)
PY
```
