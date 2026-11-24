"""Portable knowledge serialization, integrity checks and allowlisted ZIP export."""
import re
import zipfile
from pathlib import Path

from protocol import Stop, encode, sha, write

TOPICS = (
    "00-overview", "01-architecture", "02-specifications", "03-interfaces",
    "04-configuration", "05-operation-and-safety", "06-troubleshooting",
    "07-metrology", "08-visual-knowledge", "09-uncertainties",
    "10-applications", "11-system-integration", "12-related-products", "13-capabilities",
)
FIXED = {"README.md", "ESSENCE.md", "manifest.json", "sources.json", "index.json",
         "coverage.json", "SHA256SUMS", "illustrations/image-manifest.json"}
LIMIT = 96 * 1024**2
FORBIDDEN = re.compile(rb"file-api-|\bfile_id\b|%PDF-\d|JVBERi0|data:[^;,\s]+;base64,|SourceArchive|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{18,}", re.I)


def checked_name(name):
    return (name in FIXED or name in {topic + ".md" for topic in TOPICS}
            or bool(re.fullmatch(r"visual/fig-(?:pdf|astro)-\d{3}-01\.md", name))
            or bool(re.fullmatch(r"illustrations/(?:pdf|astro)-\d{3}-(?:full|upper|lower)\.(?:png|jpg)", name)))


def checked_bytes(name, raw):
    if not checked_name(name) or len(raw) > 8 * 1024**2:
        raise Stop("Unsupported knowledge entry")
    if name.endswith(".png"):
        if not raw.startswith(b"\x89PNG\r\n\x1a\n") or not raw.endswith(b"IEND\xaeB\x60\x82"):
            raise Stop("Invalid portable image")
    elif name.endswith(".jpg"):
        if not raw.startswith(b"\xff\xd8") or not raw.endswith(b"\xff\xd9"):
            raise Stop("Invalid portable JPEG")
    elif FORBIDDEN.search(raw):
        raise Stop("Forbidden raw content or provider identifier in knowledge")


def sums(entries):
    return "".join(f"{sha(raw)}  {name}\n" for name, raw in sorted(entries.items())).encode()


def descriptors(entries):
    return {key: {"sha256": sha(raw), "size": len(raw)} for key, raw in sorted(entries.items())}


def validate(entries):
    import json

    if sum(map(len, entries.values())) > LIMIT or not FIXED <= entries.keys():
        raise Stop("Missing or oversized knowledge bundle")
    for name, raw in entries.items():
        checked_bytes(name, raw)
    actual = {key: raw for key, raw in entries.items() if key != "SHA256SUMS"}
    if entries["SHA256SUMS"] != sums(actual):
        raise Stop("Knowledge checksum mismatch")
    manifest = json.loads(actual.pop("manifest.json"))
    expected = descriptors(actual)
    if (manifest["schema"] != 1 or manifest["entity"] != "BKD-PK-RF2"
            or manifest["status"] not in {"PARTIAL", "COMPLETE_UNREVIEWED"}
            or manifest["files"] != expected or manifest["identity"] != sha(encode(expected))):
        raise Stop("Knowledge manifest mismatch")
    images = json.loads(entries["illustrations/image-manifest.json"])
    if set(images) != {name for name in entries if name.endswith((".png", ".jpg"))}:
        raise Stop("Image allowlist mismatch")
    for name, metadata in images.items():
        if sha(entries[name]) != metadata["sha256"]:
            raise Stop("Image hash mismatch")
    return manifest


def read_bundle(root):
    if root.is_symlink() or not root.is_dir():
        raise Stop("Knowledge must be a real directory")
    entries = {}
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        if path.is_symlink() or (not path.is_file() and name not in {"visual", "illustrations"}):
            raise Stop("Unsafe knowledge path")
        if path.is_file():
            if not checked_name(name) or path.stat().st_size > 8 * 1024**2:
                raise Stop("Unexpected knowledge entry")
            entries[name] = path.read_bytes()
    return entries, validate(entries)


def archive(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    from io import BytesIO
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, raw in sorted(entries.items()):
            entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(entry, raw)
    write(path, buffer.getvalue())
    write(path.with_suffix(".zip.sha256"), (sha(buffer.getvalue()) + "  " + path.name + "\n").encode())


def export(root, path):
    entries, _ = read_bundle(root)
    archive(path, entries)
    verify_zip(path)


def verify_zip(path):
    import stat

    with zipfile.ZipFile(path) as source:
        entries = {}
        total = 0
        for info in source.infolist():
            total += info.file_size
            if (not checked_name(info.filename) or info.filename in entries
                    or stat.S_ISLNK(info.external_attr >> 16)
                    or info.file_size > 8 * 1024**2 or total > LIMIT):
                raise Stop("Unsafe archive entry")
            entries[info.filename] = source.read(info)
    return validate(entries)


def publish(root, entries, metadata):
    files = descriptors(entries)
    entries["manifest.json"] = encode(dict(metadata, schema=1, entity="BKD-PK-RF2", files=files,
                                           identity=sha(encode(files))))
    entries["SHA256SUMS"] = sums(entries)
    validate(entries)
    if root.exists():
        old, _ = read_bundle(root)
        if old == entries:
            return
        raise Stop("Knowledge root exists with different content")
    import tempfile
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root.parent) as tmp:
        stage = Path(tmp) / "knowledge"
        for name, raw in entries.items():
            write(stage / name, raw)
        stage.rename(root)
