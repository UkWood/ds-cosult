# 05A-CR01 · Итоговый отчёт Architecture Session A

**Исправление готово к независимой WSL-приёмке.**

Входной ZIP прошёл проверку CRC и SHA‑256 членов. В нём подтверждены 499 PASS и один FAIL в `test_dc05a_launcher::test_internal_worker_cannot_write_outside_isolation` с `AssertionError`. Внутренний worker записывал маркер до сверки workspace.

Родитель передаёт открытый дескриптор своего приватного каталога. До первой записи worker проверяет изоляцию, владельца и права каталога, совпадение устройства и inode, положение скрипта и Git-пины обоих checkout. Дескриптор сохраняется при переходе на подготовленный Python через execve. Изменение ограничено лаунчером и одним целевым тестом на отсутствие дескриптора и его несоответствие каталогу. Исходный отрицательный тест сохранён.

В облаке **501 PASS, 0 FAIL, 0 ERROR, 0 SKIP** при закреплённых публичных материалах и аудите сокетов. Отдельно проверено сохранение дескриптора при execve. Полный WSL namespace и новый прогон с приватными материалами **NOT RUN**. Новых операций DeepSeek и расходов нет.

Baseline `05a6096c58804598087a3ef3ce394b7aaf00c9c4`. Коммит исправления `2a0fb33ebaf90dafd3285df557437baddc7e1b41`. Git blob лаунчера `c7820eab1bde01382a845d6c1469e88375d9b094`. Отчёт добавлен отдельным коммитом в Draft PR #4.

## Команда полной бесплатной WSL-приёмки

Выполните блок целиком. Лаунчер сформирует один ZIP в `C:\DS-Validation\Reports`. При сбое регрессии безопасные идентификаторы попадут в `checks.json`.

```bash
python3 -I - 2a0fb33ebaf90dafd3285df557437baddc7e1b41 c7820eab1bde01382a845d6c1469e88375d9b094 <<'PY'
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

**NO MERGE · NO DEPLOY · NO PAID API.**
