"""Restore approved originals and freeze the DC-02 server material."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from .corpus import BKD, SLD, COMMIT, digest, dossiers, encoded, inventory, preflight

R1 = Path(__file__).resolve().parents[1] / "docs/reports/ds-dc-01/dossiers.json"


def restore(cache):
    """Download only the previously audited positive pilot set from the publisher."""
    sources = json.loads(R1.read_text())
    approved = {}
    for entity in (BKD, SLD):
        for doc in sources[entity]["included_docs"]:
            item = approved.setdefault(doc["url"], dict(sha256=doc["sha256"], pages=doc["pages"],
                                                        provenance=[]))
            item["provenance"].append(doc["path"] + ":" + doc["field"])

    def acquire(item):
        url, doc = item
        receipt = preflight(url, set(approved), cache, (doc["sha256"], doc["pages"]))
        return url, receipt | dict(trusted=True, provenance=sorted(set(doc["provenance"])))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(acquire, approved.items()))
    (cache / "audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")


def load(site, cache, *, reference_only=False):
    entries, excluded = inventory(site)
    path = cache / "audit.json"
    receipts = json.loads(path.read_text()) if path.exists() else {}
    historical = json.loads(R1.read_text())
    expected = {}
    for row in historical.values():
        for doc in row["docs"]:
            record = expected.setdefault(doc["url"], dict(sha256=doc.get("sha256"),
                pages=doc.get("pages"), state=doc["state"], provenance=[]))
            record["provenance"].append(doc["path"] + ":" + doc["field"])
    filtered = {}
    for url, row in expected.items():
        receipt = receipts.get(url)
        if row["state"] == "ready":
            if receipt and receipt.get("sha256") and any(
                    receipt.get(k) != row[k] for k in ("sha256", "pages")):
                receipt = {"state": "revision_drift"}
        else:
            receipt = {"state": row["state"]}
        filtered[url] = (receipt or {"state": "cache_missing"}) | {
            "provenance": row["provenance"], "trusted": True}
    registry = dossiers(entries, cache, audit=filtered, reference_only=reference_only)
    return entries, registry, excluded


def freeze(entries, registry):
    files = {}
    scopes = {}
    for entity, dossier in registry.items():
        scopes[entity] = dict(id=dossier["id"], scope=dossier["scope"],
            completeness=dossier["corpus_completeness"],
            component_links=dossier["components"],
            pages=[{k: entries[p][k] for k in ("id", "path", "blob", "commit", "sha256", "production_url")}
                   for p in dossier["pages"]],
            omissions=[{k: d.get(k) for k in ("url", "path", "field", "state")}
                       for d in dossier["issues"] + dossier["docs"] if d["state"] != "ready"])
        for doc in dossier["included_docs"]:
            sha = doc["sha256"]
            item = files.setdefault(sha, dict(sha256=sha, pages=doc["pages"], bytes=doc["bytes"], links=[]))
            if (item["pages"], item["bytes"]) != (doc["pages"], doc["bytes"]):
                raise ValueError("inconsistent_frozen_document")
            item["links"].append({k: doc.get(k) for k in ("id", "scope", "path", "field", "url", "final_url",
                                        "revision", "applicability", "applicability_source")})
    return dict(site_commit=COMMIT, dossiers=scopes, files=[files[h] for h in sorted(files)])


def freeze_digest(manifest):
    return digest(encoded(manifest).encode())
