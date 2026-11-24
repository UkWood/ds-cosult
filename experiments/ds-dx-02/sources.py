"""Prepare and verify a local, immutable source archive."""
import argparse
import re
import struct
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from astro import discover
from protocol import Stop, encode, load, save, sha, write

MAX_SOURCE = 48 * 1024**2


def cmd(*args):
    command = [arg.resolve() if isinstance(arg, Path) else arg for arg in args]
    return subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          cwd=tempfile.gettempdir(), timeout=120).stdout


def pdf_pages(data, expected):
    pages = data.decode().split("\f")
    if pages[-1] == "":
        pages.pop()
    if len(pages) != expected:
        raise Stop("Physical page map differs from pdfinfo")
    return pages


def read_pdf(path):
    match = re.search(rb"(?m)^Pages:\s+(\d+)\s*$", cmd("pdfinfo", path))
    if not match or not 1 <= int(match[1]) <= 500:
        raise Stop("Unsupported physical PDF page count")
    return pdf_pages(cmd("pdftotext", "-layout", path, "-"), int(match[1]))
def png_dimensions(data):
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise Stop("Invalid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if not 0 < width <= 8192 or not 0 < height <= 8192 or len(data) > 8 * 1024**2:
        raise Stop("Image outside local dimensions or byte limit")
    return width, height


def image_dimensions(raw):
    if raw.startswith(b"\x89PNG"):
        return png_dimensions(raw)
    if not raw.startswith(b"\xff\xd8") or len(raw) > 8 * 1024**2:
        raise Stop("Unsupported or oversized image")
    i = 2
    while i + 8 < len(raw) and raw[i] == 255:
        marker = raw[i + 1]
        size = int.from_bytes(raw[i+2:i+4], "big")
        if size < 2:
            break
        if marker in {0xC0, 0xC1, 0xC2}:
            height, width = struct.unpack(">HH", raw[i+5:i+9])
            if 0 < width <= 8192 and 0 < height <= 8192:
                return width, height
            break
        i += 2 + size
    raise Stop("Cannot read JPEG dimensions")


def retrieve(item, base, online, origin):
    if item.get("file"):
        path = (base / item["file"]).resolve()
        return path.read_bytes() if path.stat().st_size <= MAX_SOURCE else b""
    if online and urlsplit(item["url"]).netloc == urlsplit(origin).netloc:
        with urlopen(item["url"], timeout=30) as response:
            if urlsplit(response.url).netloc != urlsplit(origin).netloc:
                raise Stop("Material redirected away from approved origin")
            return response.read(MAX_SOURCE + 1)
    raise Stop("Material bytes not supplied")


def register(root, name, source, raw, **meta):
    width, height = image_dimensions(raw)
    write(root / "raw-illustrations" / name, raw)
    x, y = meta.pop("origin", (0, 0))
    return dict(meta, source=source, size=[width, height], sha256=sha(raw),
                orientation="upright render" if "dpi" in meta else "original file orientation",
                bbox_render_pixels_top_left=[x, y, x + width, y + height])


def survey_vectors(path, page):
    """Inspect painted paths outside SVG glyph definitions, using Poppler's vector renderer."""
    raw = cmd("pdftocairo", "-svg", "-f", str(page), "-l", str(page), path, "-")
    if len(raw) > 12 * 1024**2:
        return True
    root = ET.fromstring(raw)
    pending = list(root)
    strokes = 0
    while pending:
        node = pending.pop()
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in {"defs", "clipPath", "symbol"}:
            continue
        if tag == "image":
            return True
        if tag == "path":
            strokes += 1 + node.get("d", "").count(" L ") // 8
        pending.extend(node)
    return strokes >= 8


def inspect_pdf(root, id_, path, pages, images):
    graphics = set()
    for line in cmd("pdfimages", "-list", path).decode().splitlines()[2:]:
        if line.split() and line.split()[0].isdigit():
            graphics.add(int(line.split()[0]))
    inspection = []
    for n, page in enumerate(pages, 1):
        captions = re.findall(r"(?im)^\s*(?:рисунок|figure|fig\.)\s+[^\n]+", page)
        tables = re.findall(r"(?im)^\s*(?:таблица|table)\s+[^\n]+", page)
        weak = len(page.strip()) < 180
        reasons = [name for name, present in (("embedded_raster", n in graphics), ("caption", captions),
                                              ("table", tables), ("weak_text", weak)) if present]
        if not reasons:
            try:
                if survey_vectors(path, n):
                    reasons.append("painted_vector_paths")
            except (OSError, ET.ParseError, subprocess.SubprocessError):
                reasons.append("vector_survey_unavailable")
        visual = bool(reasons)
        inspection.append(dict(page=n, chars=len(page.strip()), captions=captions, tables=tables,
                               visual_reasons=reasons,
                               state="VISUAL_CANDIDATE" if visual else "TEXT_INSPECTED"))
        if not visual:
            continue
        base = ["pdftoppm", "-png", "-r", "160", "-f", str(n), "-l", str(n), "-singlefile"]
        stem = root / "raw-illustrations" / f"{id_}-{n:03}-full"
        cmd(*base, path, stem)
        full = stem.with_suffix(".png")
        images[full.name] = register(root, full.name, id_, full.read_bytes(), page=n, dpi=160)
        if set(reasons) != {"table"}:
            width, height = images[full.name]["size"]
            for part, y, end in (("upper", 0, height * 3 // 5), ("lower", height * 2 // 5, height)):
                crop = stem.with_name(stem.name.removesuffix("full") + part)
                cmd(*base, "-x", "0", "-y", str(y), "-W", str(width), "-H", str(end - y), path, crop)
                target = crop.with_suffix(".png")
                images[target.name] = register(root, target.name, id_, target.read_bytes(), page=n,
                                               dpi=160, origin=(0, y))
    save(root / "plan" / (id_ + ".json"), inspection)


def provider_fragments(root, id_, original, pages, limit):
    """Derive checked page spans only when a whole file would exceed a local input bound."""
    text_limit = 512 * 1024
    byte_limit = 46 * 1024**2
    if len(pages) <= limit and original.stat().st_size <= byte_limit and (
            sum(len(page.encode()) for page in pages) <= text_limit):
        return []
    spans = []
    first = 1
    size = 0
    for number, page in enumerate(pages, 1):
        cost = len(page.encode())
        if cost > text_limit:
            raise Stop(f"Physical page {number} exceeds the provider text input limit")
        if number - first >= limit or size + cost > text_limit:
            spans.append((first, number - 1))
            first, size = number, 0
        size += cost
    spans.append((first, len(pages)))
    output = []
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        cmd("pdfseparate", original, scratch / "page-%d.pdf")

        def add(start, finish):
            name = f"pdf-derivatives/{id_}-{start:03}-{finish:03}.pdf"
            pdf = scratch / "fragment.pdf"
            if pdf.exists():
                pdf.unlink()
            cmd("pdfunite", *(scratch / f"page-{n}.pdf" for n in range(start, finish + 1)), pdf)
            if pdf.stat().st_size > byte_limit:
                if start == finish:
                    raise Stop(f"Physical page {start} exceeds the provider byte limit")
                mid = (start + finish) // 2
                add(start, mid)
                add(mid + 1, finish)
                return
            if len(read_pdf(pdf)) != finish - start + 1:
                raise Stop("Derived PDF span page count mismatch")
            raw = pdf.read_bytes()
            write(root / name, raw)
            output.append(dict(path=name, first=start, last=finish, size=len(raw), sha256=sha(raw)))
        for start, finish in spans:
            add(start, finish)
    return output


def prepare(config_path, site, root, online=False):
    config = load(config_path)
    mode = config.get("source_discovery", "automatic")
    if mode not in {"automatic", "explicit"}:
        raise Stop("Unsupported discovery mode")
    limits = config.get("limits", {})
    pages_per_file = limits.get("pages_per_provider_file", 100)
    max_tasks = limits.get("max_tasks", 2048)
    split_depth = limits.get("split_depth", 2)
    if any(type(value) is not int or not lo <= value <= hi for value, lo, hi in (
            (pages_per_file, 1, 500), (max_tasks, 1, 8192), (split_depth, 0, 4))):
        raise Stop("Invalid compile limits")
    if config.get("compile_mode", "complete") != "complete":
        raise Stop("Unsupported compile mode")
    website, originals = discover(site, config)
    root.mkdir(mode=0o700, parents=True)
    (root / "raw-illustrations").mkdir()
    for path, raw in originals.items():
        write(root / "astro-snapshot/blobs" / path, raw)
    records = dict(website["records"])
    items = {}
    for item in website.pop("inventory"):
        entry = items.setdefault(item["url"], {"url": item["url"], "refs": []})
        entry["refs"].append({"source": item["source"], "line": item["line"]})
        for key in ("title", "edition"):
            if item[key] is not None:
                entry.setdefault(key, item[key])
    for url in config.get("exclude", {}):
        items.setdefault(url, {"url": url, "refs": []})
    for item in config.get("materials", []):
        origin = item.get("url") or item["file"]
        items.setdefault(origin, {"refs": []}).update(item)
        items[origin]["manual"] = True
    context = website.pop("context")
    images = {}
    for origin, item in items.items():
        suffix = Path(urlsplit(origin).path).suffix.lower()
        kind = "pdf" if suffix == ".pdf" else "image" if suffix in {".jpg", ".jpeg", ".png"} else "other"
        id_ = kind[0].upper() + "-" + sha(origin.encode())[:16]
        row = records[id_] = {k: v for k, v in item.items() if k not in {"file", "sha256", "size", "pages"}}
        row.update(kind=kind, origin=origin, pin={k: item[k] for k in ("sha256", "size", "pages") if k in item})
        if origin in config.get("exclude", {}):
            row.update(status="EXCLUDED", reason=config["exclude"][origin])
            continue
        if kind == "other" or (mode == "explicit" and not item.get("manual")):
            row.update(status="DEFERRED", reason="Unsupported format or outside explicit material list")
            continue
        try:
            raw = retrieve(item, config_path.parent, online, config["site"]["origin"])
            if not raw or len(raw) > MAX_SOURCE:
                raise Stop("Source byte limit")
            digest = sha(raw)
            if item.get("sha256", digest) != digest or item.get("size", len(raw)) != len(raw):
                raise Stop("Source pin mismatch")
            row.update(sha256=digest, size=len(raw))
            if kind == "pdf":
                if not raw.startswith(b"%PDF-"):
                    raise Stop("Invalid PDF signature")
                path = root / "pdf" / (id_ + ".pdf")
                write(path, raw)
                pages = read_pdf(path)
                if len(pages) != item.get("pages", len(pages)):
                    raise Stop("Physical page pin mismatch")
                row.update(pages=len(pages), mime="application/pdf")
                fragments = provider_fragments(root, id_, path, pages, pages_per_file)
                if fragments:
                    row["provider_fragments"] = fragments
                inspect_pdf(root, id_, path, pages, images)
                context[id_] = pages
            else:
                ext = "png" if raw.startswith(b"\x89PNG") else "jpg"
                row.update(mime="image/png" if ext == "png" else "image/jpeg", lines=1)
                name = id_ + "-001-full." + ext
                images[name] = register(root, name, id_, raw, line=1, url=item.get("url"))
                context[id_] = ["Исходное изображение"]
            row["status"] = "PINNED"
        except (OSError, ValueError, Stop, subprocess.SubprocessError) as error:
            for name in list(images):
                if images[name]["source"] == id_:
                    del images[name]
            reason = str(error) if isinstance(error, Stop) or hasattr(error, "code") else type(error).__name__
            row.update(status="UNAVAILABLE", reason=reason)
    website.update(records=records, entity=config["entity"], settings=config.get("limits", {}))
    save(root / "source-manifest.json", website)
    save(root / "plan/context.json", context)
    save(root / "plan/images.json", images)
    save(root / "configuration.json", config)
    files = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in root.rglob("*") if p.is_file()}
    save(root / "snapshot.json", {"entity": config["entity"], "site": website["commit"], "files": files})


def verify(root, site=None, *, reparse=True):
    manifest = load(root / "snapshot.json")
    entries = list(root.rglob("*"))
    if root.is_symlink() or any(p.is_symlink() for p in entries):
        raise Stop("Source archive contains a symlink")
    actual = {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in entries
              if p.is_file() and p != root / "snapshot.json"}
    if actual != manifest["files"]:
        raise Stop("Snapshot digest mismatch")
    website = load(root / "source-manifest.json")
    if site:
        found, originals = discover(site, load(root / "configuration.json"))
        if found["tree"] != website["tree"] or any(
                (root / "astro-snapshot/blobs" / path).read_bytes() != raw for path, raw in originals.items()):
            raise Stop("Pinned Astro archive differs from git")
    if reparse:
        for id_, row in website["records"].items():
            if row["kind"] == "pdf" and row["status"] == "PINNED":
                if len(read_pdf(root / "pdf" / (id_ + ".pdf"))) != row["pages"]:
                    raise Stop("Physical PDF map changed")
                for fragment in row.get("provider_fragments", []):
                    if len(read_pdf(root / fragment["path"])) != fragment["last"] - fragment["first"] + 1:
                        raise Stop("Derived PDF map changed")
    return sha(encode(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for arg in ("config", "site", "sources"):
        parser.add_argument("--" + arg, type=Path, required=True)
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    prepare(args.config, args.site, args.sources, args.online)
