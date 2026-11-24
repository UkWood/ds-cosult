"""Read only the pinned Saturn Astro collections and their route definitions."""
import re
import subprocess
from pathlib import PurePosixPath
from urllib.parse import quote, urljoin

import yaml

from protocol import Stop, sha


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args])


def discover(repo, config):
    revision = config["site"]["revision"]
    if not re.fullmatch("[a-f0-9]{40}", revision):
        raise Stop("An immutable Astro revision is required")
    tree = git(repo, "rev-parse", revision + "^{tree}").decode().strip()
    blobs = {}
    for entry in git(repo, "ls-tree", "-rz", revision, "src", "astro.config.mjs").split(b"\0"):
        if entry:
            header, path = entry.decode().split("\t", 1)
            mode, kind, digest = header.split()
            if kind == "blob" and mode == "100644":
                blobs[path] = digest
    read = lambda path: git(repo, "cat-file", "blob", blobs[path])
    schema = "src/content.config.ts"
    schema_text = read(schema).decode()
    origin = config["site"]["origin"]
    base_config = "astro.config.mjs"
    origin_confirmed = base_config not in blobs or re.search(
        r"""const site\s*=\s*process\.env\.SITE_URL\s*\|\|\s*['"]""" + re.escape(origin) + r"""['"]""",
        read(base_config).decode())
    depth_limit = config.get("relation_depth", 1)
    record_limit = config.get("max_records", 64)
    if (type(depth_limit) is not int or not 0 <= depth_limit <= 8
            or type(record_limit) is not int or not 1 <= record_limit <= 1024):
        raise Stop("Invalid Astro relation bounds")
    entries = {}
    fields = {}
    routes = {}
    for collection, block in re.findall(
            r"(?ms)^  (\w+): defineCollection\(\{(.*?)(?=^  \w+: defineCollection|^\};)", schema_text):
        fields[collection] = dict(
            re.findall(r"(\w+):\s*(?:z\.array\()?reference\('([^']+)'\)", block))
        for route in (f"src/pages/{collection}/[...slug].astro", f"src/pages/{collection}/[slug].astro"):
            if route in blobs:
                code = read(route).decode()
                if f"getCollection('{collection}'" in code and "slug: entry.id" in code:
                    routes[collection] = route
                    break
    for path in blobs:
        if not path.startswith("src/content/") or not path.endswith(".md"):
            continue
        _, _, collection, slug = path.split("/", 3)
        if collection not in fields:
            continue
        raw = read(path)
        body = raw.decode()
        front = body.split("\n---", 1)[0][4:] if body.startswith("---\n") else ""
        data = yaml.safe_load(front) or {}
        if data.get("draft"):
            continue
        entries[collection, slug.removesuffix(".md")] = (path, raw, body, data)
    entity = config["entity"]
    if entity["type"] not in {"product", "system"}:
        raise Stop("Unsupported entity type")
    start = (entity["type"] + "s", entity["id"])
    if start not in entries or entries[start][3].get("kind") == "category":
        if config.get("source_discovery") == "explicit" and not config.get("card"):
            return (dict(records={}, context={}, inventory=[], relations=[], indexed=len(entries),
                         boundary=[{"record": "/".join(start), "reason": "entity_missing_from_astro"}],
                         commit=revision, tree=tree), {schema: read(schema)})
        raise Stop("Entity missing from pinned Astro collections")
    if config.get("card") and entries[start][0] != config["card"]:
        raise Stop("Astro card differs from configured pin")
    edges = []
    for key, (_, _, _, data) in entries.items():
        for field, collection in fields[key[0]].items():
            targets = data.get(field, [])
            for target in targets if isinstance(targets, list) else [targets]:
                if not isinstance(target, str):
                    continue
                other = (collection, target)
                kind = ("mention" if key[0] == "news" else "group_membership" if collection == "groups"
                        else "compatibility" if field == "software" else "explicit_reference")
                edges.append((key, other, field, kind))
    selected = {start: (0, "entity_card")}
    boundary = []
    for depth in range(depth_limit + 1):
        frontier = {key for key, (distance, _) in selected.items() if distance == depth}
        for a, b, field, kind in edges:
            if a in frontier:
                other, direction = b, "outgoing"
            elif b in frontier:
                other, direction = a, "incoming"
            else:
                continue
            if other not in entries or (other not in selected and (
                    depth == depth_limit or len(selected) >= record_limit
                    or (direction == "incoming" and kind == "group_membership"))):
                boundary.append({"record": "/".join(other), "field": field, "reason": "unresolved_or_outside_scope"})
            elif other not in selected:
                selected[other] = (depth + 1, direction + "_" + kind)
    title = entries[start][3]["title"]
    for key, (_, _, body, _) in entries.items():
        if key in selected or key[0] not in {"articles", "news", "pages"}:
            continue
        if len(title) >= 5 and re.search(r"(?<!\w)" + re.escape(title) + r"(?!\w)", body, re.I):
            if len(selected) < record_limit:
                selected[key] = (1, "incoming_mention")
            else:
                boundary.append({"record": "/".join(key), "reason": "mention_outside_limit"})
    ids = {key: "A-" + sha("/".join(key).encode())[:16] for key in selected}
    records, context, inventory, originals = {}, {}, [], {}
    for key, (_, reason) in selected.items():
        collection, slug = key
        path, raw, body, data = entries[key]
        id_ = ids[key]
        lines = body.splitlines()
        route = routes.get(collection)
        confirmed = origin_confirmed and route and ("/" not in slug or "[...slug]" in route)
        records[id_] = {"kind": "astro", "path": path, "commit": revision, "tree": tree,
                        "blob": blobs[path], "sha256": sha(raw), "size": len(raw), "lines": len(lines),
                        "ranges": [[1, len(lines)]], "relation": reason,
                        "canonical_url": urljoin(origin, f"/{collection}/{quote(slug)}/") if confirmed else None,
                        "route_blob": blobs[route] if route else None,
                        "site_config_blob": blobs.get(base_config)}
        context[id_] = lines
        originals[path] = raw
        if route:
            originals[route] = read(route)
        metadata = {urljoin(origin, item["url"]): item for field in ("documents", "certificates")
                    for item in data.get(field, []) if isinstance(item, dict) and "url" in item}
        for n, line in enumerate(lines, 1):
            for link in re.findall(r"""(?:https?://[^\s"'<>()[\]{},]+|/[^\s"'<>()[\]{},]+)\.(?:pdf|png|jpe?g|webp|zip)\b""", line, re.I):
                url = urljoin(origin, link)
                inventory.append({"url": url, "source": id_, "line": n,
                                  "edition": metadata.get(url, {}).get("version"),
                                  "title": metadata.get(url, {}).get("title")})
    originals[schema] = read(schema)
    if base_config in blobs:
        originals[base_config] = read(base_config)
    relations = [{"from": ids[a], "to": ids[b], "field": field, "type": kind}
                 for a, b, field, kind in edges if a in ids and b in ids]
    return dict(records=records, context=context, inventory=inventory, relations=relations,
                boundary=boundary, indexed=len(entries), commit=revision, tree=tree), originals
