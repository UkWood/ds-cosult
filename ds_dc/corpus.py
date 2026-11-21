"""Build immutable source inventory and preflight approved documents outside turns."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit

from ds_pilot.discovery import COMMIT, ROOTS, SITE, front, git, pins

from .pdf_policy import (MAX_PAGES, MAX_SIZE, OWNER_EXCLUDED, dossier_availability, inspect_pdf)

PREVIEW = "https://ukwood.github.io/Saturn-Main-Site"
PREFIX = dict(products="products/", systems="systems/", groups="catalog/",
              articles="articles/", news="news/", pages="")
BKD = "saturn:device:bkd-pk-rf-2"
SLD = "saturn:system:sldks-1"
PIN = {
    BKD: ("030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a", 65),
    SLD: ("f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f", 83),
}
REVISION = {
    "030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a": "ЕСАН.426469.012РЭ, 203-01",
    "f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f": "ЕСАН.484457.001РЭ, 26.05.11",
}
# Applicability reviewed against the first-page text of these exact bytes.
BKD_SUPPLEMENTS = {
    "bf07da30d1221f61a3ecdde5b40f542b90ca2a646c5dc6019997326a2c570148": (2, "БКД-ПК-RF.2, быстрый старт"),
    "496ddc2786b8fb2cdfd8970947fadde6b7a045e7d86e20737f2ef694425d5890": (8, "БКД-ПК-RF.2, обзор изменений"),
    "959f515c588ea8758cae0ccfdd17efaf396b31c84c4315e1b195c745d59db5db": (5, "БКД-ПК-RF.2, OPC UA, ПО 1.5, Информационные каналы"),
}
MD_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\(<?([^\s<>]+?\.pdf(?:[?#][^\s<>)]*)?)>?\)", re.I)
ROUTE_LINK = re.compile(r"(?<!!)\[[^\]\n]*\]\((/[\w/-]+/)\)")
RELATIONS = dict(group="groups", systems="systems", system="systems", products="products",
                 software="products", related="products", variant_of="products",
                 articles="articles", solutions="pages")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def inventory(site):
    if git(site, "rev-parse", "HEAD").decode().strip() != COMMIT:
        raise ValueError("wrong_site_commit")
    snapshot = pins()
    if snapshot["commit"] != COMMIT:
        raise ValueError("wrong_manifest_commit")
    approved_sources = {x["path"]: x for x in snapshot["sources"]}
    entries, excluded = {}, Counter()
    for record in git(site, "ls-tree", "-rz", COMMIT).decode().split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        parts = path.split("/")
        if parts[:2] == ["src", "content"] and len(parts) >= 4:
            collection = parts[2]
            if collection not in PREFIX or not path.endswith(".md"):
                excluded["unsupported_content"] += 1
                continue
        elif path.startswith("src/pages/") and path.endswith(".astro"):
            excluded["astro_route_template"] += 1
            continue
        else:
            excluded["other_repository_file"] += 1
            continue
        raw = git(site, "show", f"{COMMIT}:{path}")
        lines, end, data = front(raw)
        slug = "/".join(parts[3:]).removesuffix(".md")
        route = "/" if collection == "pages" and slug == "home" else f"/{PREFIX[collection]}{slug}/"
        kind = {"products": "device", "systems": data.get("kind", "system"),
                "groups": "group", "articles": "article", "news": "news", "pages": "page"}[collection]
        if collection == "products" and data.get("group") == "programmnoe-obespechenie":
            kind = "software"
        entity = SLD if path == ROOTS["sld"] else f"saturn:{kind}:{slug}"
        body = "\n".join(lines[end + 1:])
        relations = []
        for field, target in RELATIONS.items():
            refs = data.get(field, [])
            for ref in refs if isinstance(refs, list) else [refs]:
                if ref:
                    relations.append(dict(route=f"/{PREFIX[target]}{ref}/", field=field))
        relations.extend(dict(route=link, field=f"line:{n}") for n, line in
                         enumerate(lines[end + 1:], end + 2) for link in ROUTE_LINK.findall(line))
        links = [
            dict(item, field=f"{key}[{i}]", url=urljoin(SITE, item["url"]))
            for key in ("documents", "certificates") for i, item in enumerate(data.get(key, []))
            if item.get("url")
        ]
        links += [dict(url=urljoin(SITE, link.replace(r"\(", "(").replace(r"\)", ")")), field=f"line:{n}", title=link)
                  for n, line in enumerate(lines[end + 1:], end + 2) for link in MD_LINK.findall(line)]
        features = {key: data[key] for key in ("name", "summary", "applications", "interfaces",
                    "protocols", "notice", "features", "connectors", "specs") if data.get(key)}
        entries[entity] = dict(id=entity, kind=kind, route=route, canonical=PREVIEW + route,
                               production_url=SITE + route, path=path, blob=meta.split()[-1], sha256=digest(raw), commit=COMMIT,
                               variant=approved_sources.get(path, {}).get("variant"),
                               title=data["title"], draft=bool(data.get("draft")), state="not_ready",
                               features=features, relations=relations, links=links, body=body,
                               raw=raw.decode())
    return entries, excluded


def allowed_pdf(url, allowed):
    target = urlsplit(url)
    return (url not in OWNER_EXCLUDED and url in allowed and target.scheme == "https" and
            target.netloc in {"www.mnppsaturn.ru", "mnppsaturn.ru"} and
            target.path.lower().endswith(".pdf") and not target.fragment and not target.query)


def preflight(url, allowed, cache, pin=None, *, max_size=MAX_SIZE, max_pages=MAX_PAGES):
    result = dict(url=url, final_url=None, time_utc=datetime.now(timezone.utc).isoformat(),
                  state="unavailable", requests=0)
    if url in OWNER_EXCLUDED:
        return dict(result, state="EXCLUDED_BY_OWNER")
    with tempfile.TemporaryDirectory(dir=cache) as directory:
        path = Path(directory) / "original.pdf"
        for _ in range(4):
            if url in OWNER_EXCLUDED:
                return dict(result, state="EXCLUDED_BY_OWNER", rejected_url=url)
            if not allowed_pdf(url, allowed):
                return dict(result, state="url_not_approved", rejected_url=url)
            result.update(final_url=url, requests=result["requests"] + 1)
            try:
                fetch = subprocess.run(
                    ["curl", "--disable", "--silent", "--show-error", "--proto", "=https",
                     "--connect-timeout", "8", "--max-time", "25", "--max-filesize", str(max_size),
                     "--output", str(path), "--write-out",
                     "%{http_code}\n%{http_connect}\n%{redirect_url}\n%{content_type}", url],
                    capture_output=True, text=True, timeout=28)
            except subprocess.TimeoutExpired:
                return dict(result, state="timeout")
            status, proxy, redirect, mime = (fetch.stdout.split("\n") + [""] * 4)[:4]
            result.update(http=status, proxy_connect=proxy, mime=mime, curl_exit=fetch.returncode)
            if fetch.returncode:
                return dict(result, state="proxy_connect_failure" if proxy not in
                            ("", "000", "200") else "transfer_failure")
            if status in {"301", "302", "303", "307", "308"}:
                url = redirect
                continue
            if status != "200":
                return dict(result, state="origin_http_error")
            raw = path.read_bytes()
            result.update(bytes=len(raw), sha256=digest(raw))
            if mime.split(";")[0].lower() not in {"application/pdf", "application/octet-stream"}:
                return dict(result, state="invalid_pdf")
            check = inspect_pdf(path, max_size=max_size, max_pages=max_pages)
            result.update(check)
            if result["state"] != "extractable":
                return result
            pages = result["pages"]
            if pin and (result["sha256"], pages) != pin:
                return dict(result, state="revision_drift")
            path.replace(cache / (result["sha256"] + ".pdf"))
            return dict(result, state="downloaded")
    return dict(result, state="redirect_limit")


def dossiers(entries, cache, fetch=False, *, audit=None, reference_only=False):
    approved = {(item["path"], item["original_url"]): item for item in pins()["documents"]}
    allowed = {url for path, url in approved if path in {x["path"] for x in entries.values()}}
    routes = {entry["route"]: entry for entry in entries.values() if not entry["draft"]}
    approved_pages = {x["path"] for x in pins()["sources"]}
    if audit:
        for entry in entries.values():
            if entry["path"] not in approved_pages:
                continue
            for link in entry["links"]:
                url = link["url"]
                receipt = audit.get(url, {})
                if receipt.get("trusted") and any(ref.startswith(entry["path"] + ":")
                                                  for ref in receipt.get("provenance", [])):
                    approved.setdefault((entry["path"], url), {})
                    allowed.add(url)
    result, queue = {}, {}
    historical = {x["entity"]: x["original_url"] for x in pins()["cloud_acquisition"]}
    for entity in (BKD, SLD):
        root = entries[entity]
        related = {root["id"]: root}
        for relation in root["relations"]:
            target = routes.get(relation["route"])
            if target and target["path"] in approved_pages and target["kind"] in {"article", "page"}:
                related[target["id"]] = target
        docs = []
        issues = []
        for entry in sorted(related.values(), key=lambda x: x["id"]):
            for link in entry["links"]:
                url = link["url"]
                if url in OWNER_EXCLUDED:
                    issues.append(dict(url=url, path=entry["path"], field=link["field"],
                                       state="EXCLUDED_BY_OWNER"))
                    continue
                if not urlsplit(url).path.lower().endswith(".pdf"):
                    issues.append(dict(url=url, path=entry["path"], state="unsupported_format"))
                    continue
                item = approved.get((entry["path"], url))
                doc = dict(id=digest(url.encode()), url=url, path=entry["path"], field=link["field"],
                           title=link["title"], scope=entity, state="not_approved", revision=None)
                if item is not None and allowed_pdf(url, allowed):
                    doc["state"] = "pending"
                    doc["revision"] = item.get("revision")
                    # The historical manifest binds both originals by entity and exact URL.
                    queue[url] = PIN[entity] if historical[entity] == url else queue.get(url)
                docs.append(doc)
        if historical[entity] not in {doc["url"] for doc in docs}:
            issues.append(dict(url=historical[entity], state="pinned_original_missing"))
        component_relations = [
            dict(target=routes[relation["route"]]["id"], path=root["path"], field=relation["field"])
            for relation in root["relations"] if relation["route"] in routes
            and routes[relation["route"]]["kind"] in {"device", "software"}
        ]
        result[entity] = dict(pages=sorted(related), docs=docs, issues=issues,
                              scope="pinned_reference_and_root" if reference_only else "full_available",
                              components=component_relations)
    if len(queue) > 24:
        raise ValueError("document_count_limit")
    receipts = cache / "preflight.json"
    if fetch:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {url: pool.submit(preflight, url, allowed, cache, pin) for url, pin in queue.items()}
            observed = {url: task.result() for url, task in futures.items()}
        receipts.write_text(json.dumps(observed, ensure_ascii=False, indent=2))
    else:
        observed = json.loads(receipts.read_text()) if receipts.exists() else {}
    if audit is not None:
        observed = {**observed, **audit}
    for entity, dossier in result.items():
        for doc in dossier["docs"]:
            obs = observed.get(doc["url"], {}) if doc["state"] == "pending" else {}
            for field in ("final_url", "time_utc", "http", "proxy_connect", "mime", "curl_exit",
                          "bytes", "sha256", "pages", "structure", "requests", "rejected_url",
                          "pages_processed", "quality"):
                if field in obs:
                    doc[field] = obs[field]
            if obs:
                doc["state"] = obs.get("state", "invalid_receipt")
                if doc["state"] == "ready":
                    doc["state"] = "invalid_receipt"
            if doc["state"] != "downloaded":
                continue
            if (not re.fullmatch(r"[0-9a-f]{64}", str(doc.get("sha256", "")))
                    or type(doc.get("pages")) is not int or not 0 < doc["pages"] <= MAX_PAGES
                    or not allowed_pdf(doc.get("final_url") or "", allowed)
                    or doc.get("structure") != "passive_poppler_all_pages"
                    or doc.get("pages_processed") != doc["pages"]):
                doc["state"] = "invalid_receipt"
                continue
            file = cache / (doc["sha256"] + ".pdf")
            if not file.is_file() or file.stat().st_size > MAX_SIZE or digest(file.read_bytes()) != doc["sha256"]:
                doc["state"] = "cache_integrity_error"
            elif queue[doc["url"]] and (doc["sha256"], doc["pages"]) != queue[doc["url"]]:
                doc["state"] = "revision_drift"
            elif queue[doc["url"]]:
                doc.update(state="ready", revision=REVISION[doc["sha256"]])
            elif entity == BKD and doc["sha256"] in BKD_SUPPLEMENTS:
                pages, scope = BKD_SUPPLEMENTS[doc["sha256"]]
                doc.update(state="ready" if pages == doc["pages"] else "revision_drift",
                           applicability=scope, applicability_source="physical page 1")
            elif entity == BKD:
                doc["state"] = "revision_drift"
            else:
                doc.update(state="ready", applicability="Связь из закреплённого источника",
                           applicability_source=doc["path"] + ":" + doc["field"])
        _, dossier["corpus_completeness"] = dossier_availability(
            [item["state"] for item in dossier["docs"] + dossier["issues"]], has_pages=bool(dossier["pages"]))
        if reference_only:
            dossier["pages"] = [entity]
            for doc in dossier["docs"]:
                if doc["state"] == "ready" and doc["url"] != historical[entity]:
                    doc["state"] = "outside_explicit_scope"
        dossier["composition"] = [dict(path=entries[p]["path"], sha256=entries[p]["sha256"],
                                       blob=entries[p]["blob"]) for p in dossier["pages"]]
        scope_items = ([item for item in dossier["docs"] + dossier["issues"]
                        if item["url"] == historical[entity]] if reference_only else dossier["docs"] + dossier["issues"])
        dossier["state"], dossier["completeness"] = dossier_availability(
            [item["state"] for item in scope_items], has_pages=bool(dossier["pages"]))
        dossier["included_docs"] = [doc for doc in dossier["docs"] if doc["state"] == "ready"]
        dossier["id"] = digest(encoded([entity, dossier["scope"], [(p, entries[p]["sha256"]) for p in dossier["pages"]],
                                      [(d["url"], d.get("sha256"), d["revision"], d["scope"])
                                       for d in dossier["included_docs"]]]).encode())
        entries[entity]["state"] = dossier["state"]
    return result
