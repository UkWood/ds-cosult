"""Resolve one-hop dossier links against the immutable site's Astro collections."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

MANIFEST = Path(__file__).resolve().parents[1] / "docs/corpus/DS-PILOT-02-SOURCE-MANIFEST.json"
ROOTS = {
    "bkd": "src/content/products/bkd-pk-rf-2.md",
    "sld": "src/content/systems/sistema-liftovogo-dispetcherskogo-kontrolya-sldks-1.md",
}
COMMIT = "084d759487bfab6e111549c9b5469711ac5fc13e"
SITE = "https://www.mnppsaturn.ru"


def front(raw):
    lines = raw.decode().splitlines()
    end = lines.index("---", 1)
    return lines, end, yaml.safe_load("\n".join(lines[1:end]))


def git(checkout, *args):
    return subprocess.check_output(["git", "-C", str(checkout), *args])


def discover(checkout):
    tree = {}
    for line in git(checkout, "ls-tree", "-r", COMMIT, "src/content").decode().splitlines():
        meta, path = line.split("\t")
        if path.endswith(".md"):
            tree[path] = meta.split()[-1]
    routes = {}
    for path in tree:
        collection, slug = path.removeprefix("src/content/").removesuffix(".md").split("/", 1)
        if collection in {"articles", "products", "systems", "pages"}:
            route = f"/{slug}/" if collection == "pages" else f"/{collection}/{slug}/"
            routes[route] = path
    selected = {path: ["pinned primary dossier"] for path in ROOTS.values()}
    excluded = []
    for key, root in ROOTS.items():
        lines, end, data = front(git(checkout, "show", f"{COMMIT}:{root}"))
        refs = []
        for field, collection in (("systems", "systems"), ("articles", "articles"), ("solutions", "pages")):
            for i, slug in enumerate(data.get(field, [])):
                refs.append((f"/{collection}/{slug}/" if collection != "pages" else f"/{slug}/",
                             f"{key} {field}[{i}]"))
        for n, line in enumerate(lines[end+1:], end+2):
            refs.extend((link, f"{key} L{n}") for link in re.findall(r"\]\(([^)]+)\)", line))
        for link, reason in refs:
            if link in routes:
                selected.setdefault(routes[link], []).append(reason)
            else:
                excluded.append(dict(url=link, reason=reason, status="out_of_scope"))
    files, sources, documents = {}, [], []
    for path, reasons in sorted(selected.items()):
        raw = git(checkout, "show", f"{COMMIT}:{path}")
        _, _, data = front(raw)
        route = next(route for route, target in routes.items() if target == path)
        collection, slug = path.removeprefix("src/content/").removesuffix(".md").split("/", 1)
        kind = {"products":"device","systems":"system","articles":"article","pages":"page"}[collection]
        key = next((k for k, p in ROOTS.items() if path == p), f"{collection}.{slug}")
        entity = f"saturn:{kind}:{slug}" if key != "sld" else "saturn:system:sldks-1"
        gen = {"sldks-1-vypusk-2001-2004-g":"gen1","sldks-1-vypusk-2005-2006-g":"gen2"}.get(slug)
        sources.append(dict(key=key, entity=entity, title=data['title'], type=kind, path=path,
                            route=route, url=SITE+route, blob=tree[path], sha256=hashlib.sha256(raw).hexdigest(),
                            bytes=len(raw), variant=gen, reason=reasons, status="included"))
        files[key] = raw
        for i, item in enumerate(data.get("documents", [])):
            url = item.get("url", "")
            documents.append(dict(entity=entity, path=path, locator=f"documents[{i}]", title=item["title"],
                                  original_url=SITE+url if url.startswith("/") and not url.startswith("//") else url,
                                  type=item.get("kind"), revision=item.get("version"), variant=gen,
                                  status="metadata_only", reason="manufacturer document listing; body requires local import"))
    return files, dict(commit=COMMIT, sources=sources, documents=documents, excluded=excluded)


def pins():
    return json.loads(MANIFEST.read_text())
