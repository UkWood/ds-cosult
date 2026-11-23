"""Bootstrap and serve the pinned DS-DC-05A owner stand on WSL loopback."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import getpass
from hashlib import file_digest, sha1, sha256
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
from secrets import token_urlsafe
import shutil
import socket
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import warnings


BASELINE = "c8e0ed0e1122e3a17781c4a5497bbc4c8830d38b"
SITE = "084d759487bfab6e111549c9b5469711ac5fc13e"
REMOTE = "https://github.com/UkWood/ds-cosult.git"
REF = "refs/heads/feat/ds-dc-01-document-centric-pilot"
LAUNCHER = "scripts/validation/launch_dc05a.py"
PRIOR_RUNNER = "scripts/validation/validate_dc03c.py"
HOST = "127.0.0.1"
PORT = 8765
REPORTS = Path("/mnt/c/DS-Validation/Reports")
PIN = re.compile(r"[0-9a-f]{40}")
REVIEWED_AT = datetime(2026, 11, 23, 5, 13, 43, tzinfo=timezone.utc)
REVIEW_EXPIRES = datetime(2026, 12, 23, 5, 13, 43, tzinfo=timezone.utc)
PROVIDER_EVIDENCE = {
    "https://api-docs.deepseek.com/quick_start/pricing/": "b61db7d97374d37819b4dcdd41e86aa2d6bfa4d50bf059e700327727a4462e02",
    "https://api-docs.deepseek.com/api/create-chat-completion/": "0e36b6cd7edf17d59e61bc5588b58cd440237aac9a57d86552a6a87ea1c7416d",
    "https://api-docs.deepseek.com/api/create-file/": "a2d2e7a13c6ba0d1ff179fbafaf9458d6edf55e8c1b219984949159ad6b2bbe4",
    "https://api-docs.deepseek.com/guides/document_parsing/": "600befff8c42fee41d6ade23df1a1a676cca479de284bdc7476f1b3293ece0e0",
    "https://api-docs.deepseek.com/guides/thinking_mode/": "1fb7208ceb7a8aebbd6549cf158649b78414b606bb7dc9b134884e92156009d9",
}
CONTRACT_DIGEST = "80d43e4731235e7867de31b55269524231989f17b8de506157d73ff0dee6916d"


class LaunchError(ValueError):
    """An owner-facing startup problem with a fixed safe status code."""


def require(condition, code):
    if not condition:
        raise LaunchError(code)


def contract():
    return {
        "schema": "dc05a-provider-contract/1",
        "reviewed_at": REVIEWED_AT.isoformat(),
        "valid_until": REVIEW_EXPIRES.isoformat(),
        "origin": "https://api.deepseek.com",
        "model_alias": "deepseek-flash", "model_version": "DeepSeek-V4.1-Flash-1017",
        "model_context": 1048576, "model_output_doc": "384K",
        "routes": ["POST /files", "POST /chat/completions"],
        "purpose": "text_recognition", "ttl": 3600,
        "pdf_max_bytes": 100 * 1024 * 1024, "pdf_max_pages": 1000,
        "max_files": 20, "max_parsed_bytes": 8 * 1024 * 1024,
        "normal_input_estimate": 128000, "extended_input_estimate": 256000, "max_tokens": 8192,
        "prompt_version": "evidence-integration/2",
        "thinking": "enabled", "reasoning_effort": "high",
        "response_format": "json_object", "stream": False, "tools": False, "web_search": False,
        "retry": 0, "redirect": 0, "verified_billable_input_bound": None,
        "valuation": "approved_peak_rates",
        "peak_rates": {"hit": "0.006", "miss": "0.30", "completion": "1.20", "page": "225"},
        "off_peak_token_rates": {"hit": "0.003", "miss": "0.15", "completion": "0.60"},
        "evidence": PROVIDER_EVIDENCE.copy(),
    }


def check_contract(now):
    raw = json.dumps(contract(), sort_keys=True, separators=(",", ":")).encode()
    require(sha256(raw).hexdigest() == CONTRACT_DIGEST, "provider_contract_digest_mismatch")
    require(REVIEWED_AT <= now < REVIEW_EXPIRES, "provider_contract_expired_or_unreviewed")


def utc_now():
    return datetime.now(timezone.utc)


def validate_runtime_contract():
    from ds_dc import context, evidence_integration, finance, native

    terms = contract()
    pairs = {
        "origin": native.ORIGIN, "model_context": native.MODEL_CONTEXT, "purpose": native.PURPOSE,
        "ttl": native.PARSE_TTL, "max_parsed_bytes": native.PARSED_BYTES_LIMIT,
        "normal_input_estimate": context.NORMAL, "extended_input_estimate": context.EXTENDED,
        "max_files": context.FILE_LIMIT, "max_tokens": context.OUTPUT,
        "prompt_version": evidence_integration.FUTURE_PROMPT_VERSION, "peak_rates": finance.RATES,
    }
    require(all(terms[field] == value for field, value in pairs.items()), "provider_contract_runtime_mismatch")


def trusted_wsl():
    return platform.system() == "Linux" and "microsoft" in platform.release().casefold()


def git_environment(*, online=False):
    return {"PATH": os.environ.get("PATH", os.defpath), "LANG": "C.UTF-8",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0", "GIT_ALLOW_PROTOCOL": "https" if online else ""}


def git(checkout, *command, online=False):
    return subprocess.check_output([
        "git", "-C", str(checkout), "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false", *command,
    ], env=git_environment(online=online), timeout=180, stderr=subprocess.PIPE).strip()


def blob_digest(path):
    raw = path.read_bytes()
    return sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def verify_checkout(checkout, commit, blob):
    try:
        require(git(checkout, "rev-parse", "HEAD").decode("ascii") == commit, "checkout_pin_mismatch")
        require(not git(checkout, "status", "--porcelain", "--untracked-files=all"), "checkout_dirty")
        require(git(checkout, "rev-parse", f"HEAD:{LAUNCHER}").decode("ascii") == blob
                and blob_digest(checkout / LAUNCHER) == blob, "launcher_blob_mismatch")
        require(commit != BASELINE and git(checkout, "merge-base", BASELINE, commit).decode("ascii") == BASELINE,
                "checkout_baseline_mismatch")
        require(git(checkout, "merge-base", commit, "FETCH_HEAD").decode("ascii") == commit,
                "commit_not_in_draft_branch")
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise LaunchError("checkout_provenance_invalid") from error


def prepare_checkout(checkout, commit, blob):
    checkout.mkdir(mode=0o700)
    try:
        git(checkout, "init", "--quiet", "--template=")
        git(checkout, "fetch", "--quiet", "--no-tags", "--no-recurse-submodules", REMOTE, REF, online=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise LaunchError("draft_checkout_fetch_failed") from error
    try:
        git(checkout, "checkout", "--quiet", "--detach", commit)
    except (OSError, subprocess.SubprocessError) as error:
        raise LaunchError("checkout_pin_mismatch") from error
    verify_checkout(checkout, commit, blob)


def bounded_directories(root):
    require(root.is_dir(), "validation_root_not_found")
    excluded = {".git", "__pycache__", ".pytest_cache", "node_modules", "Old_Site", "site-packages"}
    for count, (directory, subdirs, files) in enumerate(os.walk(root, followlinks=False), 1):
        require(count <= 8192, "validation_discovery_limit")
        path = Path(directory)
        if len(path.relative_to(root).parts) >= 6 or "pyvenv.cfg" in files:
            subdirs.clear()
        else:
            subdirs[:] = sorted(name for name in subdirs if name not in excluded)
        yield path, set(files)


def matches_file(path, digest, *, size=None):
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or (info.st_size > 10_000_000 if size is None else info.st_size != size):
            return False
        with path.open("rb") as stream:
            return file_digest(stream, "sha256").hexdigest() == digest
    except OSError:
        return False


def unique_path(paths, name):
    options = set(paths)
    require(bool(options), name + "_not_found")
    require(len(options) == 1, name + "_ambiguous")
    return options.pop()


def discover_cache(root, tokenizer, tokenizer_sha, pdfs):
    full, partial = [], []
    for path, files in bounded_directories(root):
        if {"audit.json", tokenizer} <= files and matches_file(path / tokenizer, tokenizer_sha):
            count = sum(matches_file(path / (sha + ".pdf"), sha, size=size) for sha, size in pdfs.items())
            if count:
                (full if count == len(pdfs) else partial).append(path)
    return unique_path(full or partial, "trial_cache")


def discover_python(root):
    paths = []
    for path, files in bounded_directories(root):
        binary = path / "bin/python"
        if "pyvenv.cfg" in files and binary.is_file() and os.access(binary, os.X_OK):
            try:
                config = (path / "pyvenv.cfg").read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if re.search(r"^version\s*=\s*3\.12(?:\.\d+)?\s*$", config, re.M):
                paths.append(binary)
    return unique_path(paths, "trial_venv")


def check_site(site):
    try:
        require(git(site, "rev-parse", "HEAD").decode("ascii") == SITE, "site_pin_mismatch")
        require(not git(site, "status", "--porcelain", "--untracked-files=all"), "site_checkout_dirty")
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        raise LaunchError("site_checkout_unavailable") from error


def discover_inputs(args, checkout):
    home = Path.home()
    root = args.wsl_root or home / "ds-dc03b-validation"
    site = (args.site or home / "ds-dc02-cal-validation/Saturn-Main-Site").absolute()
    check_site(site)
    if args.cache is None:
        spec = importlib.util.spec_from_file_location("dc05a_prior_material_pins", checkout / PRIOR_RUNNER)
        prior = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prior)
        args.cache = discover_cache(root, prior.TOKENIZER_FILE, prior.TOKENIZER, prior.CACHE_PDFS)
    python = (args.python or discover_python(root)).absolute()
    require(python.is_file() and os.access(python, os.X_OK), "trial_venv_not_found")
    return site, args.cache.absolute(), python


def validate_dependencies(checkout):
    require(sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix, "trial_python_venv_invalid")
    for requirement in (checkout / "requirements.txt").read_text(encoding="utf-8").splitlines():
        package, version = requirement.split("==", 1)
        try:
            installed = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        require(installed == version, "trial_dependency_pin_mismatch")
    require(all(shutil.which(program) for program in ("git", "pdfinfo", "pdftotext", "prlimit")),
            "trial_dependency_program_missing")


def parse_budget(raw):
    amount = re.fullmatch(r"([0-9]+)(?:[.,]([0-9]{1,6}))?", raw.strip())
    require(bool(amount), "session_budget_invalid")
    dollars, fraction = amount.groups()
    value = int(dollars) * 1_000_000 + int((fraction or "").ljust(6, "0"))
    require(value > 0, "session_budget_invalid")
    return value


def operator_activation(stdin, stderr, *, key_reader=getpass.getpass):
    print("После решения Architecture Session A и проверки актуальности условий DeepSeek "
          "введите LIVE для запуска платного режима.", file=stderr, flush=True)
    confirmation = stdin.readline(64)
    require(confirmation.endswith("\n") and confirmation.strip() == "LIVE", "live_activation_not_confirmed")
    print("Введите отдельный лимит этой сессии в USD. Значение не задано.", file=stderr, flush=True)
    amount = stdin.readline(64)
    require(amount.endswith("\n"), "session_budget_invalid")
    cap = parse_budget(amount)
    check_contract(utc_now())
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = key_reader("DeepSeek API KEY: ", stream=stderr)
        except (EOFError, OSError, getpass.GetPassWarning) as error:
            raise LaunchError("hidden_key_input_unavailable") from error
    require(isinstance(key, str) and re.fullmatch(r"[!-~]{1,512}", key), "trial_key_invalid")
    return cap, key


def activate_from_tty():
    try:
        with open("/dev/tty", "r", encoding="utf-8") as tty_in, open("/dev/tty", "w", encoding="utf-8") as tty_out:
            return operator_activation(tty_in, tty_out)
    except OSError as error:
        raise LaunchError("owner_terminal_required") from error


@contextmanager
def listen_on_loopback(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((HOST, port))
            listener.listen(128)
        except OSError as error:
            raise LaunchError("loopback_port_unavailable") from error
        yield listener


@contextmanager
def trial_state():
    directory = Path.home().resolve() / ".local/state/ds-dc05a"
    require(directory.resolve() == directory, "trial_state_not_private")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077,
            "trial_state_not_private")
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(directory / ".server.lock", flags, 0o600), "r+b") as lock:
        info = os.fstat(lock.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077
                and info.st_nlink == 1, "trial_state_not_private")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise LaunchError("trial_already_running") from error
        yield directory


def serve_checkout(site, cache, *, live=False, port=PORT):
    checkout = Path(__file__).resolve().parents[2]
    with listen_on_loopback(port) as listener:
        validate_dependencies(checkout)
        from ds_dc import context
        from ds_dc.trial import TrialConsultant, load_trial_materials
        from ds_dc.trial_journal import TrialJournal
        from ds_dc.trial_web import create_app
        import uvicorn

        check_site(site)
        require(matches_file(cache / context.TOKENIZER_NAME, context.TOKENIZER_SHA),
                "trial_tokenizer_pin_mismatch")
        try:
            entries, dossiers = load_trial_materials(site, cache)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise LaunchError("trial_corpus_pins_invalid") from error
        validate_runtime_contract()
        if live:
            require(trusted_wsl(), "trusted_wsl_required")
            check_contract(utc_now())

        with trial_state() as directory:
            journal = TrialJournal(directory / "journal", REPORTS)
            native = None
            mode = "live" if live else "offline"
            if live:
                from ds_dc.trial_native import TrialNative

                provider = directory / "provider"
                require(not TrialNative.check_state(provider), "trial_pending_provider_charge")
                cap, key = activate_from_tty()
                check_contract(utc_now())
                native = TrialNative(cache, provider, cap, key=key, expires_at=REVIEW_EXPIRES.timestamp())
                del key
            consultant = TrialConsultant(entries, dossiers, cache, native, mode=mode)
            address = f"http://{HOST}:{port}"
            app_settings = dict(mode=mode, host=HOST, port=port)
            if live:
                owner_token = token_urlsafe(32)
                app_settings["owner_token"] = owner_token
                address += f"/#owner={owner_token}"
            app = create_app(consultant, journal, **app_settings)
            config = uvicorn.Config(app, host=HOST, port=port, proxy_headers=False, access_log=False,
                                    server_header=False)
            server = uvicorn.Server(config)
            message = f"DS-DC-05A {mode} · {address} · Ctrl+C"
            if live:
                with open("/dev/tty", "w", encoding="utf-8") as terminal:
                    print(message, file=terminal, flush=True)
            else:
                print(message, flush=True)
            server.run(sockets=[listener])
            require(server.started, "trial_server_start_failed")


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True, help="Exact 40-character Draft PR commit")
    parser.add_argument("--blob", required=True, help="Exact Git blob of this launcher")
    parser.add_argument("--live", action="store_true", help="Owner activation after architecture acceptance")
    parser.add_argument("--port", type=int, default=PORT, help="Loopback port")
    parser.add_argument("--wsl-root", type=Path)
    parser.add_argument("--site", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--serve", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        require(PIN.fullmatch(args.commit) and PIN.fullmatch(args.blob), "invalid_launch_pin")
        require(1 <= args.port <= 65535, "loopback_port_invalid")
        require(not args.live or trusted_wsl(), "trusted_wsl_required")
        require(blob_digest(Path(__file__).resolve()) == args.blob, "launcher_blob_mismatch")
        if args.serve:
            checkout = Path(__file__).resolve().parents[2]
            verify_checkout(checkout, args.commit, args.blob)
            require(args.site and args.cache, "trial_material_paths_missing")
            os.umask(0o077)
            sys.path.insert(0, str(checkout))
            serve_checkout(args.site, args.cache, live=args.live, port=args.port)
            return 0

        with TemporaryDirectory(prefix="ds-dc05a-checkout-") as tmp:
            checkout = Path(tmp) / "checkout"
            prepare_checkout(checkout, args.commit, args.blob)
            site, cache, python = discover_inputs(args, checkout)
            command = [str(python), "-I", "-B", str(checkout / LAUNCHER), "--serve",
                       "--commit", args.commit, "--blob", args.blob, "--port", str(args.port),
                       "--site", str(site), "--cache", str(cache)]
            if args.live:
                command.append("--live")
            with subprocess.Popen(command, cwd=checkout, env=git_environment()) as child:
                try:
                    return child.wait()
                except KeyboardInterrupt:
                    # The same terminal signal reaches the child. Leave time for
                    # its server and any in-flight accounting to finish cleanly.
                    return child.wait()
    except LaunchError as error:
        print(f"DS-DC-05A blocked [{error}]", file=sys.stderr)
        return 2
    except (ImportError, OSError, ValueError, subprocess.SubprocessError):
        print("DS-DC-05A blocked [trial_startup_unavailable]", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
