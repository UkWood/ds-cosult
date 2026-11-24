"""Read pinned Git objects and prepare an isolated compiler source archive."""
import argparse
import re
import shutil
import struct
import subprocess
from pathlib import Path
from urllib.parse import urljoin

from protocol import Stop, encode, load, save, sha, write

PDF_SHA = "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a"
PDF_URL = "https://www.mnppsaturn.ru/ftp/public/doc/bkd-pk-rf2/re%20BKD-PK-RF2.pdf"
SITE = "084d759487bfab6e111549c9b5469711ac5fc13e"
ORIGIN = "https://www.mnppsaturn.ru"
PRODUCT = "src/content/products/bkd-pk-rf-2.md"
SITE_MEDIA = {
    "3112376640116232.jpg": (73206, "504f11f654a5b3b7466715e5a30ede6a38c149b7f5a3c909e8164b209481bf73"),
    "3385755126930346.jpg": (179920, "b4912d21cea0b83974b5afe04d4067e66ee0392436117466c3daa994e95a017a"),
}
PRODUCT_BLOB = "86afcfe8be3be4e5022f0baf43143f64a2a9f7a0"
ROUTE = "src/pages/products/[slug].astro"
SCHEMA = "src/content.config.ts"
ENTITY = "BKD-PK-RF2"
MATCH = re.compile(r"бкд[-– ]пк[-– ]rf[. -]?2|bkd-pk-rf-?2", re.I)

def cmd(*args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE).stdout


def plan(pages, site_images=()):
    def task(id_, topic, bounds, instruction, family="pdf-astro", *, limit=8192, images=(), deps=()):
        return dict(id=id_, topic=topic, pages=list(bounds), instruction=instruction,
                    family=family, limit=limit, images=list(images), deps=list(deps))
    tasks = [
        task("K00", 0, (1, 65), "Карта разделов, таблиц, рисунков и пробелов", limit=4096),
        task("K01", 0, (1, 3), "Назначение, версии, идентификация"),
        task("K02", 1, (7, 17), "Архитектура, функции, состав, устройство"),
        task("K03", 2, (3, 7), "Таблица 1 и точные параметры с единицами и условиями"),
        task("K04", 3, (9, 15), "Сигналы, разъёмы, индикация, подключения, протоколы"),
        task("K05", 4, (20, 58), "Меню и конфигурация, заводские настройки, связь и диагностика"),
        task("K06", 5, (17, 61), "Монтаж, питание, меры безопасности, эксплуатация, хранение, перевозка и утилизация"),
        task("K07", 6, (59, 60), "Диагностика, обслуживание и таблица 12 в полном контексте безопасности"),
        task("K08", 7, (59, 65), "Поверка, метрология, сертификация, комплектность и приложения"),
    ]
    tasks[5]["split"] = ["S05A", "S05B"]
    for n in sorted(pages, key=lambda n: (n not in (3, 11, 60), n)):
        images = [f"pdf-{n:03}-full.png"]
        if n == 11:
            images.extend(["pdf-011-upper.png", "pdf-011-lower.png"])
        tasks.append(task(f"V{n:03}", 8, (n, n),
                          "Извлеки видимые связи, подписи, обозначения, единицы и нечитаемые зоны",
                          "pdf-astro-vision", limit=4096, images=images))
    for i, image in enumerate(site_images, 1):
        tasks.append(task(f"VA{i:02}", 8, (), "Опиши видимую маркировку и ограничения фото",
                          "astro-vision", limit=4096, images=[image]))
    for i, instruction in enumerate((
        "Назначение и конкретные практические применения", "Подтверждённое участие в системах и интеграция",
        "Связанные и заменяемые изделия, различие совместимости и соседства",
        "Функциональные возможности и ограничения редакций",
    ), 1):
        tasks.append(task(f"W{i:02}", 9 + i, (1, 65), instruction, limit=4096))
    tasks.append(task("F01", 9, (1, 65),
                      "Запиши только нерешённые различия и неоднозначности как unresolved. "
                      "Сохрани оба исходных значения, контексты и локаторы; не меняй предшествующие факты.",
                      "fusion", limit=4096, deps=["K03", "W04", "V011"]))
    priorities = {"V003", "V011", "V060"}
    tasks.sort(key=lambda item: (0 if item["id"].startswith("K") else
                                 1 if item["id"] in priorities else
                                 2 if item["id"].startswith("W") else
                                 3 if item["id"].startswith("F") else
                                 4 if item["id"].startswith("VA") else 5))
    tasks.extend([
        task("S05A", 4, (20, 36), "Конфигурация, часть 1", deps=["K05"]),
        task("S05B", 4, (37, 58), "Конфигурация, часть 2", deps=["K05"]),
    ])
    return tasks


def pdf_pages(data):
    pages = data.decode().split("\f")
    if pages[-1] == "":
        pages.pop()
    if len(pages) != 65 or not re.search(r"Таблица\s+1\b", pages[2], re.I) or not re.search(
            r"Таблица\s+12\b", pages[59], re.I):
        raise Stop("Physical page map or control tables differ from pin")
    return pages


def read_pdf(path):
    data = path.read_bytes()
    if len(data) != 3024578 or sha(data) != PDF_SHA:
        raise Stop("PDF pin mismatch")
    if not re.search(rb"(?m)^Pages:\s+65\s*$", cmd("pdfinfo", path)):
        raise Stop("PDF page count mismatch")
    return pdf_pages(cmd("pdftotext", "-layout", path, "-"))


def git(repo, *args):
    return cmd("git", "-C", repo, *args)


def astro(repo):
    tree = git(repo, "rev-parse", SITE + "^{tree}").decode().strip()
    entries = {}
    for row in git(repo, "ls-tree", "-rz", SITE, "src", "astro.config.mjs").split(b"\0"):
        if row:
            header, path = row.decode().split("\t", 1)
            mode, kind, blob = header.split()
            if kind == "blob" and mode == "100644":
                entries[path] = blob
    schema = next((path for path in (SCHEMA, "src/content/config.ts") if path in entries), None)
    if entries.get(PRODUCT) != PRODUCT_BLOB or ROUTE not in entries or not schema:
        raise Stop("Pinned product, route or collection schema missing")
    read = lambda name: git(repo, "cat-file", "blob", entries[name])
    route = read(ROUTE).decode()
    schema_text = read(schema).decode()
    if "slug: entry.id" not in route or "getCollection('products'" not in route or "products" not in schema_text:
        raise Stop("Unsupported Astro route or schema")
    root = read(PRODUCT).decode()
    records, contexts, relations, inventory = {}, {}, [], []
    paths = [path for path in entries if path.startswith(("src/content/", "src/data/"))
             and Path(path).suffix in {".md", ".mdx", ".yaml", ".yml", ".json"}]
    if "systems: [newel]" not in root or "group: newel" not in root:
        raise Stop("Pinned system relation missing")
    for path in sorted(paths):
        raw = read(path)
        body = raw.decode()
        hits = [i for i, line in enumerate(body.splitlines(), 1) if MATCH.search(line)]
        if path == PRODUCT:
            reason = "canonical_product"
        elif path in ("src/content/systems/newel.md", "src/content/groups/newel.md"):
            reason = "explicit_product_system_or_group_reference"
        elif hits:
            reason = "incoming_mention_unconfirmed_applicability"
        else:
            continue
        id_ = "A%03d" % (len(records) + 1)
        lines = body.splitlines()
        ranges = ([(1, len(lines))] if reason != "incoming_mention_unconfirmed_applicability"
                  or path.startswith("src/content/news/") else
                  [(max(1, i - 2), min(len(lines), i + 2)) for i in hits])
        selected = sorted({n for lo, hi in ranges for n in range(lo, hi + 1)})
        slug = str(Path(path).relative_to("src/content").with_suffix("")) if path.startswith("src/content/") else ""
        url = ORIGIN + "/" + slug + "/" if path == PRODUCT else None
        records[id_] = {"commit": SITE, "tree": tree, "blob": entries[path], "sha256": sha(raw),
                        "path": path, "canonical_url": url, "lines": len(lines),
                        "ranges": ranges, "selected_because": reason}
        contexts[id_] = "\n".join(f"{n}: {lines[n - 1]}" for n in selected)
        if path != PRODUCT:
            relations.append({"source": id_, "type": reason, "lines": hits or [1]})
        for i in selected:
            for link in re.findall(r'[/][^"\s)>]+\.(?:pdf|jpe?g|png|zip)', lines[i - 1], re.I):
                url = urljoin(ORIGIN, link)
                status = ("PINNED" if url == PDF_URL else "EXCLUDED" if
                          url.endswith("/photos/2278872612744825.pdf") else "DEFERRED")
                inventory.append({"url": url, "source": id_, "line": i, "status": status,
                                  "reason": {"PINNED": "approved manual", "EXCLUDED": "owner excluded stale link",
                                             "DEFERRED": "outside approved PDF and pinned site image scope"}[status]})
    return dict(records=records, context=contexts, relations=relations, inventory=inventory,
                route={"path": ROUTE, "blob": entries[ROUTE]}, schema={"path": schema, "blob": entries[schema]},
                indexed=len(paths), commit=SITE, tree=tree)


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


def prepare(pdf, site, root, media=None):
    if root.exists():
        raise Stop("Prepare needs a fresh SourceArchive directory")
    pages = read_pdf(pdf)
    website = astro(site)
    root.mkdir(mode=0o700, parents=True)
    (root / "pdf").mkdir()
    shutil.copyfile(pdf, root / "pdf/manual.pdf")
    records = []
    images = {}
    candidates = {3, 8, 11, 12, 60}
    for n, page in enumerate(pages, 1):
        captions = [line.strip() for line in page.splitlines()
                    if re.match(r"\s*Рисунок\s+\d+\s*[–—-]", line)]
        visual = n in candidates or bool(captions) or len(page.strip()) < 180
        records.append({"page": n, "chars": len(page.strip()), "captions": captions,
                        "tables": re.findall(r"Таблица\s+\d+", page, re.I),
                        "state": "RENDER_PLANNED" if visual else "TEXT_INSPECTED"})
        if visual:
            candidates.add(n)

    image_dir = root / "raw-illustrations"
    image_dir.mkdir()
    for n in sorted(candidates):
        stem = image_dir / f"pdf-{n:03}-full"
        base = ["pdftoppm", "-png", "-r", "220", "-f", str(n), "-l", str(n), "-singlefile"]
        cmd(*base, root / "pdf/manual.pdf", stem)
        def register(path, x, y):
            raw = path.read_bytes()
            width, height = png_dimensions(raw)
            images[path.name] = {"source": "P01", "page": n, "dpi": 220,
                                 "bbox_render_pixels_top_left": [x, y, x + width, y + height],
                                 "size": [width, height], "sha256": sha(raw),
                                 "orientation": "upright as rendered by Poppler"}
            return width, height
        width, height = register(stem.with_suffix(".png"), 0, 0)
        if n == 11:
            for kind, y, length in (("upper", 0, height * 3 // 5),
                                    ("lower", height * 2 // 5, height - height * 2 // 5)):
                crop = image_dir / f"pdf-{n:03}-{kind}"
                cmd(*base, "-x", "0", "-y", str(y), "-W", str(width), "-H", str(length),
                    root / "pdf/manual.pdf", crop)
                register(crop.with_suffix(".png"), 0, y)
    site_images = []
    for i, (filename, (size, digest)) in enumerate(SITE_MEDIA.items(), 1):
        url = ORIGIN + "/photos/" + filename
        path = media / filename if media else None
        targets = [item for item in website["inventory"] if item["url"] == url]
        if not path or not path.is_file():
            for item in targets:
                item.update(status="MISSING", reason="pinned site photo not provided to PREP")
            continue
        raw = path.read_bytes()
        if len(raw) != size or sha(raw) != digest:
            raise Stop("Astro photo pin mismatch: " + filename)
        name = f"astro-{i:03}-full.jpg"
        width, height = image_dimensions(raw)
        write(image_dir / name, raw)
        images[name] = {"source": targets[-1]["source"], "line": targets[-1]["line"],
                        "url": url, "size": [width, height], "sha256": digest,
                        "bbox_render_pixels_top_left": [0, 0, width, height],
                        "orientation": "original JPEG"}
        site_images.append(name)
        for item in targets:
            item.update(status="PINNED", reason="approved inline site photograph")
    for id_, row in website["records"].items():
        write(root / "astro-snapshot/blobs" / row["path"], git(site, "cat-file", "blob", row["blob"]))
    for row in (website["route"], website["schema"]):
        write(root / "astro-snapshot/blobs" / row["path"], git(site, "cat-file", "blob", row["blob"]))
    write(root / "plan/pages.txt", "\f".join(pages).encode())
    save(root / "astro-snapshot/context.json", website)
    save(root / "plan/inspection.json", records)
    save(root / "plan/images.json", images)
    save(root / "plan/tasks.json", plan(sorted(candidates), site_images))
    paths = {str(p.relative_to(root)): sha(p.read_bytes()) for p in sorted(root.rglob("*")) if p.is_file()}
    save(root / "snapshot.json", {"entity": ENTITY, "site": SITE, "pdf_sha": PDF_SHA, "files": paths})


def verify(root, site=None, *, reparse=True):
    manifest = load(root / "snapshot.json")
    if manifest["site"] != SITE or manifest["pdf_sha"] != PDF_SHA:
        raise Stop("Snapshot pin mismatch")
    for name, digest in manifest["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink() or sha(path.read_bytes()) != digest:
            raise Stop("Snapshot digest mismatch: " + name)
    pages = load(root / "plan/inspection.json")
    images = load(root / "plan/images.json")
    if [page["page"] for page in pages] != list(range(1, 66)) or not {"pdf-011-full.png",
            "pdf-011-upper.png", "pdf-011-lower.png"} <= images.keys():
        raise Stop("Incomplete physical page or image map")
    if reparse:
        read_pdf(root / "pdf/manual.pdf")
    for name, metadata in images.items():
        raw = (root / "raw-illustrations" / name).read_bytes()
        if sha(raw) != metadata["sha256"] or list(image_dimensions(raw)) != metadata["size"]:
            raise Stop("Image hash or dimension mismatch")
    if site:
        original = astro(site)
        prepared = load(root / "astro-snapshot/context.json")
        for key in original.keys() - {"inventory"}:
            if encode(original[key]) != encode(prepared[key]):
                raise Stop("Pinned Git material differs from prepared snapshot")
        for row in [*original["records"].values(), original["route"], original["schema"]]:
            if (root / "astro-snapshot/blobs" / row["path"]).read_bytes() != git(site, "cat-file", "blob", row["blob"]):
                raise Stop("Pinned archive blob mismatch")
    tasks = load(root / "plan/tasks.json")
    pdf_pages = sorted({item["page"] for item in images.values() if "page" in item})
    if tasks != plan(pdf_pages, sorted(name for name in images if name.endswith(".jpg"))):
        raise Stop("Task plan does not match the fixed compiler graph")
    return sha(encode(manifest))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--site", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--media", type=Path)
    args = parser.parse_args()
    prepare(args.pdf, args.site, args.sources, args.media)
