"""Private, append-only Markdown records for the local owner trial."""

from datetime import datetime, timezone
import errno
from ipaddress import ip_address
import json
import os
from pathlib import Path
import re
import stat
from tempfile import NamedTemporaryFile
import time
import unicodedata
from urllib.parse import unquote, urlsplit
from uuid import uuid4


RETENTION_SECONDS = 30 * 86400
WINDOWS_EXPORT = Path("/mnt/c/DS-Validation/Reports")
REQUEST_ID = re.compile(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}")
PUBLIC_HOSTS = {"www.mnppsaturn.ru", "mnppsaturn.ru", "ukwood.github.io"}
SOURCE_PATH = re.compile(r"/[A-Za-z0-9_.%()/+~-]*")
PAGE_FRAGMENT = re.compile(r"page=[1-9][0-9]{0,3}")
SENSITIVE_TEXT = re.compile(
    r"\b(?:sk-[a-z0-9_-]{8,}|file-api-[a-z0-9_-]+|file_[a-z0-9_-]{6,}|"
    r"chatcmpl-[a-z0-9_-]{6,}|bearer\s+\S+|"
    r"(?:authorization|api[ _-]?key|file[_ -]?id|reasoning[_ -]?content|raw[_ -]?http|"
    r"cookie|set-cookie|access[_ -]?token|password|secret)\s*[:=])", re.IGNORECASE,
)
PRIVATE_EXPORT_TEXT = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b|"
    r"(?:[A-Za-z]:[\\/]|\\\\|(?<![\w/])/(?:home|root|mnt|tmp|workspace)/|(?:~|\$HOME)[/\\])|"
    r"\b(?:https?|ftp|file|ssh|data)\s*:|\bwww\.", re.IGNORECASE,
)
IPV6_TEXT = re.compile(r"(?<!\w)[0-9a-f:]{2,}(?!\w)")


def normalized(text):
    return unicodedata.normalize("NFKC", unquote(unquote(text))).casefold()


def safe_source_url(value):
    """Recognize links to the pinned site's public URL namespaces."""
    if not isinstance(value, str) or len(value) > 512 or not value.startswith("https://"):
        return None
    try:
        target = urlsplit(value)
    except ValueError:
        return None
    path = unquote(unquote(target.path))
    if (target.netloc not in PUBLIC_HOSTS or target.query
            or not SOURCE_PATH.fullmatch(target.path or "/")
            or any(part in {".", ".."} for part in path.split("/"))
            or "//" in path or any(c in path for c in "\\@?#<>")
            or any(unicodedata.category(c).startswith("C") for c in path)
            or (target.fragment and not PAGE_FRAGMENT.fullmatch(target.fragment))
            or (target.netloc == "ukwood.github.io" and not path.startswith("/Saturn-Main-Site/"))):
        return None
    return value


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _checked_path(value):
    path = Path(value).absolute()
    if ".." in path.parts or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("trial_directory_symlink")
    if any(marker.is_file() or (marker / "HEAD").is_file()
           for marker in (parent / ".git" for parent in (path, *path.parents))):
        raise ValueError("trial_directory_inside_checkout")
    return path


def _private_directory(value):
    path = _checked_path(value)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ValueError("trial_directory_must_be_private")
    return path


def _directory_sync(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _append(path, content, *, windows=False):
    """Publish an already flushed record with exclusive creation."""
    with NamedTemporaryFile(dir=path.parent, prefix=".trial-", mode="w",
                            encoding="utf8", delete=False) as pending:
        temp = Path(pending.name)
        try:
            os.fchmod(pending.fileno(), 0o600)
            pending.write(content)
            pending.flush()
            os.fsync(pending.fileno())
            os.link(temp, path)
            try:
                _directory_sync(path.parent)
            except OSError as error:
                if not windows or error.errno not in {errno.EINVAL, errno.ENOTSUP}:
                    raise
        finally:
            temp.unlink(missing_ok=True)


def _read_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, encoding="utf8") as file:
        info = os.fstat(file.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("trial_record_must_be_private")
        return file.read()


_FENCE = chr(96) * 3


def _record(title, value):
    serialized = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
    # Preserve exact data in JSON while preventing Markdown fence injection,
    # embedded HTML and link syntax from owner/provider text.
    serialized = serialized.replace(chr(96), "\\u0060").replace("<", "\\u003c").replace(">", "\\u003e")
    return f"# {title}\n\n{_FENCE}json\n{serialized}\n{_FENCE}\n"


def _read_record(path):
    _, fenced = _read_private(path).split(f"{_FENCE}json\n", 1)
    payload, closing = fenced.rsplit(f"\n{_FENCE}\n", 1)
    if closing:
        raise ValueError("trial_record_invalid")
    return json.loads(payload)


def _export_text(value):
    # Approved links may appear as structured sources or inside the verified
    # answer and review note. Remove their match before looking for private URLs.
    stripped = re.sub(r"https://[^\s,]+",
                      lambda match: "" if safe_source_url(match[0]) else match[0], value)
    checked = normalized(stripped)
    if SENSITIVE_TEXT.search(checked) or PRIVATE_EXPORT_TEXT.search(checked):
        return "[скрыто]"
    for match in IPV6_TEXT.finditer(checked):
        token = match[0]
        if token.count(":") >= 2:
            try:
                ip_address(token)
            except ValueError:
                continue
            return "[скрыто]"
    return value


class TrialJournal:
    def __init__(self, directory, export_directory):
        self.directory = _private_directory(directory)
        self.export_directory = Path(export_directory).absolute()
        if (self.directory == self.export_directory or self.directory in self.export_directory.parents
                or self.export_directory in self.directory.parents):
            raise ValueError("trial_directories_must_be_separate")
        self.reservations = _private_directory(self.directory / ".requests")
        self.purge()

    def purge(self, now=None):
        """Apply historical raw retention locally, without provider operations."""
        cutoff = (time.time() if now is None else now) - RETENTION_SECONDS
        deleted = False
        for pattern in ("request-*.md", "feedback-*.md", ".trial-*"):
            for path in self.directory.glob(pattern):
                if path.lstat().st_mtime <= cutoff:
                    path.unlink(missing_ok=True)
                    deleted = True
        if deleted:
            _directory_sync(self.directory)

    def reserve(self, request_id):
        """Persist a one-use request ID before starting any provider operation.

        A receipt survives process exit and stays reserved if a call or journal
        write was interrupted. It contains no question, response or session data.
        """
        if not REQUEST_ID.fullmatch(request_id):
            raise ValueError("invalid_trial_request")
        try:
            _append(self.reservations / request_id, f"{utc()}\n")
        except FileExistsError:
            return False
        return True

    def record(self, turn, expert, session_id, started):
        request_id = turn["request"]
        _append(self.directory / f"request-{request_id}.md", _record("Вопрос и ответ DS-DC-05A", {
            "session": session_id,
            "started_utc": started,
            "completed_utc": utc(),
            "turn": turn,
            "expert": expert,
        }))

    def feedback(self, request_id, values):
        if not self.has_turn(request_id):
            raise FileNotFoundError("trial_turn_unavailable")
        now = utc()
        revision = {"request": request_id, "utc": now, **values}
        name = f"feedback-{request_id}-{now.replace(':', '')}-{uuid4().hex}.md"
        _append(self.directory / name, _record("Экспертная оценка DS-DC-05A", revision))
        return revision

    def has_turn(self, request_id):
        return bool(REQUEST_ID.fullmatch(request_id)) and (self.directory / f"request-{request_id}.md").is_file()

    def feedback_history(self, request_id):
        if not REQUEST_ID.fullmatch(request_id):
            raise ValueError("invalid_trial_request")
        cutoff = time.time() - RETENTION_SECONDS
        return [_read_record(path) for path in sorted(self.directory.glob(f"feedback-{request_id}-*.md"))
                if path.lstat().st_mtime > cutoff]

    def export(self, request_ids=None):
        cutoff = time.time() - RETENTION_SECONDS
        records = {}
        for path in sorted(self.directory.glob("request-*.md")):
            request_id = path.stem.removeprefix("request-")
            if (not REQUEST_ID.fullmatch(request_id) or path.lstat().st_mtime <= cutoff
                    or (request_ids is not None and request_id not in request_ids)):
                continue
            records[request_id] = _read_record(path)
        if not records or (request_ids is not None and set(records) != set(request_ids)):
            raise FileNotFoundError("trial_turn_unavailable")

        def cleaned(value):
            if isinstance(value, str):
                return _export_text(value)
            if isinstance(value, list):
                return [cleaned(item) for item in value]
            if isinstance(value, dict):
                return {key: cleaned(item) for key, item in value.items() if key != "session"}
            return value

        sections = []
        for request_id, record in sorted(records.items(), key=lambda item: item[1]["started_utc"]):
            sections.append(_record("Вопрос и ответ DS-DC-05A", cleaned(record)))
            for revision in self.feedback_history(request_id):
                sections.append(_record("Экспертная оценка DS-DC-05A", cleaned(revision)))
        windows = self.export_directory == WINDOWS_EXPORT
        if windows:
            destination = _checked_path(self.export_directory)
            if not Path("/mnt/c").is_mount():
                raise OSError("windows_export_mount_unavailable")
            destination.mkdir(mode=0o700, parents=True, exist_ok=True)
        else:
            destination = _private_directory(self.export_directory)
        name = f"ds-dc-05a-export-{uuid4().hex}.md"
        _append(destination / name, "\n".join(sections), windows=windows)
        return name
