# 05A-CR01 · Диагностика регрессии WSL

**Статус: требуется диагностический прогон WSL.**

CRC и пять контрольных сумм входного ZIP совпали. Pytest вернул код 1. Из 500 тестов один завершился с FAIL, без ERROR и SKIP. Authentic R1 replay, ASGI smoke, изоляция и побайтовая сверка ledger и корпуса прошли. Пять критериев унаследовали FAIL от общей регрессии.

Прежний runner читает случаи из JUnit, но экспорт 05A оставляет только счётчики и общий `full_regression_unverified`. В присланном архиве нет идентификатора теста, поэтому причина самой регрессии пока не доказана.

Диагностический коммит `ef578f92e7f8ab034558aab07aa671b216de38fd`, blob лаунчера `6356585dba14d4fccc7add56e3aab6fa1f969944`. Изменён только acceptance launcher. При FAIL он читает JUnit до удаления приватного временного каталога. В `checks.json` поле `regression.diagnostics.nonpassing_tests` содержит модуль, имя теста, порядковый номер варианта в семействе, фиксированный код и тип исключения из списка допустимых. Параметры, сообщения исключений, пути и traceback остаются локальными. Git SHA, blob, scope, namespace, исторический replay и проверки неизменности продолжают действовать. Облачная проверка дала 10 пройденных тестов лаунчера. Отдельная проверка JUnit подтвердила отсутствие приватного содержимого в проекции.

## Следующее действие в WSL

Выполнить блок целиком и передать единственный ZIP из `C:\DS-Validation\Reports`. При повторном FAIL идентификатор даст основание для точечного исправления. При PASS такой прогон следует оценить как отдельное доказательство, сохранив факт исходного сбоя. Операции DeepSeek и ввод ключа отсутствуют.

```bash
python3 -I - ef578f92e7f8ab034558aab07aa671b216de38fd 6356585dba14d4fccc7add56e3aab6fa1f969944 <<'PY'
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

**NO PAID API · NO MERGE · NO PUBLIC DEPLOY**
