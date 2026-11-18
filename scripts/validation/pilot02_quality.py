"""Offline P0 benchmark and read-only comparison of selected owner-operated turns."""
import argparse
from collections import Counter
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile

import yaml

from ds_pilot.catalog import COMMIT, REPO, Catalog, DocumentReference, Relation, load_git
from ds_pilot.engine import Pilot

HERE = Path(__file__).resolve().parents[2] / "docs/implementation/quality"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@lru_cache(maxsize=100)
def source(checkout, path):
    return subprocess.check_output(["git", "-C", checkout, "show", f"{COMMIT}:{path}"])


def verifies(item, records, checkout, data):
    cite = item["citation"]
    if cite["target_id"] != item.get(cite["target_type"]):
        return False
    need_id, _, record_id = cite["target_id"].partition(":")
    if need_id != item["need_id"] or record_id not in records:
        return False
    record, entity_name = records[record_id]
    if not record or not all(cite.get(k) == v for k, v in asdict(record.evidence).items()):
        return False
    expected = f"{entity_name} — {record.text}"
    if cite["target_type"] == "position_id":
        expected = "Источник указывает: " + expected
    if isinstance(record, Relation) and cite["target_type"] == "claim_id":
        if record.configuration != item.get("configuration"):
            return False
    if isinstance(record, DocumentReference) and record.document_url != item.get("document_url"):
        return False
    if item["text"] != expected or cite["commit"] != COMMIT:
        return False
    physical = re.fullmatch(r"PDF physical page (\d+)", cite["locator"])
    if physical:
        from ds_pilot.pdf_sources import extract
        raw = (data / "pdf" / (cite["sha256"] + ".pdf")).read_bytes()
        page = int(physical[1])
        pages = extract(raw)
        return (digest(raw) == cite["sha256"] and 1 <= page <= len(pages)
                and cite["snippet"] == pages[page - 1]["quote"]
                and cite["url"] == f'{cite["path"]}#page={page}')
    raw = source(checkout, cite["path"])
    if digest(raw) != cite["sha256"]:
        return False
    git_url = f'{REPO}/blob/{COMMIT}/{cite["path"]}'
    if cite["url"].split("#")[0] != git_url:
        return False
    lines = raw.decode().splitlines()
    loc = cite["locator"]
    span = re.fullmatch(r"(?:body:)?L(\d+)(?:-L?(\d+))?", loc)
    if span:
        a, b = int(span[1]), int(span[2] or span[1])
        return 1 <= a <= b <= len(lines) and cite["snippet"] in "\n".join(lines[a-1:b])
    front = yaml.safe_load("\n".join(lines[1:lines.index("---", 1)]))
    field = re.fullmatch(r"([\w]+)(?:\[(\d+)\])?", loc)
    if field and field[1] in front:
        value = front[field[1]]
        if field[2] is not None:
            value = value[int(field[2])]
        return (value == record.value or cite["snippet"] in raw.decode()
                and isinstance(value, dict) and str(value.get("value")) in record.text)
    return False


def score(case, answer, records, checkout, data):
    needs = answer.get("question_needs", [])
    objects = []
    for kind in ("verified_claims", "document_references", "conflict_positions"):
        for item in answer.get(kind, []):
            cite = item["citation"]
            objects.append(dict(need=item["need_id"], kind=kind, text=item["text"],
                                path=cite["path"], locator=cite["locator"], url=cite["url"],
                                verified=verifies(item, records, checkout, data)))
            if "document_url" in item:
                objects[-1]["document_url"] = item["document_url"]
    observed = []
    needs_only_abstention = all(n["evidence"] is None for n in case["needs"])
    for gold in case["needs"]:
        ids = {n["id"] for n in needs if (n["entity"], n["attribute"]) ==
               (gold["entity"], gold["attribute"]) and n["variant"] == gold.get("variant")}
        linked = [o for o in objects if o["need"] in ids and o["kind"] != "conflict_positions"]
        grounded = [o["text"] for o in linked if o["verified"]]
        observed.append(dict(entity=gold["entity"], attribute=gold["attribute"], recalled=bool(ids),
                             grounded=all(re.search(p, " ".join(grounded), re.I) for p in gold["evidence"])
                             if gold["evidence"] else None,
                             abstained=not bool(objects if needs_only_abstention else linked)
                             if not gold["evidence"] else None))
    status_ok = answer["status"] in case["status"]
    if needs_only_abstention and objects:
        status_ok = False
    return dict(id=case["id"], question=case["question"], status=answer["status"],
                reason=answer["reason_code"], expected_status=status_ok,
                recognized=[{k:n[k] for k in ("entity","attribute","variant")} for n in needs],
                assessment=observed, objects=objects)


def summary(rows):
    metrics = dict(status=dict(Counter(r["status"] for r in rows)),
                   expected_status=[sum(r["expected_status"] for r in rows), len(rows)])
    for metric in ("recalled", "grounded", "abstained"):
        vals = [n[metric] for r in rows for n in r["assessment"] if n[metric] is not None]
        metrics[metric] = [sum(vals), len(vals)]
    citations = [o["verified"] for r in rows for o in r["objects"]]
    metrics["verified_citations"] = [sum(citations),len(citations)]
    return metrics


def owner_turn(db, request):
    row = db.execute("SELECT admitted,mode,response,dispatch FROM turns WHERE request=?", (request,)).fetchone()
    if not row or not row[2]:
        raise ValueError("Missing completed owner turn")
    return json.loads(row[0]), row[1], json.loads(row[2]), row[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path, help="read-only pinned Saturn Git checkout")
    parser.add_argument("--data", type=Path, help="same imported PDF/data directory used by the owner server")
    parser.add_argument("--owner-db", type=Path)
    parser.add_argument("--requests", type=Path, help='JSON map of selected Qnn IDs to recorded live request IDs')
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.requests and not args.owner_db:
        parser.error("--requests requires --owner-db")
    cases = json.loads((HERE / "questions.json").read_text())
    catalog = Catalog(load_git(args.checkout))
    if args.data:
        from ds_pilot.pdf_sources import load_pdfs
        load_pdfs(catalog, args.data)
    records = {r.id: (r, catalog.entities[entity].name)
               for (entity, _), group in catalog.records.items() for r in group}
    owner_ids = json.loads(args.requests.read_text()) if args.requests else {}
    selected = {c["id"] for c in cases if c.get("owner_route")}
    if len(selected) > 12 or set(owner_ids) - selected or len(set(owner_ids.values())) != len(owner_ids):
        parser.error("Only distinct selected owner turns can be compared")
    owner_db = sqlite3.connect(args.owner_db.resolve().as_uri() + "?mode=ro", uri=True) if args.owner_db else None
    if owner_db and not args.requests:
        for case in cases:
            if not case.get("owner_route"):
                continue
            matches = owner_db.execute(
                """SELECT request FROM turns WHERE mode=? AND response IS NOT NULL
                   AND json_extract(admitted,'$.original_question_exact')=?
                   AND json_extract(admitted,'$.referent') IS NULL""",
                (case["owner_route"], case["question"])).fetchall()
            if len(matches) > 1:
                parser.error(f'{case["id"]} has multiple owner turns: select one with --requests')
            if matches:
                owner_ids[case["id"]] = matches[0][0]
    rows, compared, pairs = [], [], []
    with tempfile.TemporaryDirectory() as temp:
        for case in cases:
            # Separate, fresh sessions, except for explicitly declared context.
            pilot = Pilot(catalog, Path(temp) / (case["id"]+".sqlite"))
            if case.get("context"):
                previous = next(c for c in cases if c["id"] == case["context"])
                pilot.ask(previous["question"], "bench", "context", now=1700000000)
            answer = pilot.ask(case["question"], "bench", case["id"], now=1700000001)
            if answer.get("provider_attempts", 0):
                raise RuntimeError("Unexpected provider attempt during offline replay")
            row = score(case, answer, records, args.checkout, args.data)
            rows.append(row)
            if case["id"] in owner_ids:
                admitted, mode, live, dispatched = owner_turn(owner_db, owner_ids[case["id"]])
                if (admitted["original_question_exact"] != case["question"] or admitted["referent"]
                    or admitted["source"] != catalog.manifest() or mode != case["owner_route"]
                    or not dispatched or live.get("route_used") != mode
                    or live.get("paid_receipt", {}).get("attempts") != 1):
                    raise ValueError(f'{case["id"]}: different question/context/corpus/route or missing dispatch')
                live_row = score(case, live, records, args.checkout, args.data)
                compared.append(live_row)
                pairs.append(dict(id=case["id"], request_id=owner_ids[case["id"]], route=mode,
                                  receipt=live["paid_receipt"], p0=row, assisted=live_row))
    result = dict(source_manifest_sha256=digest(json.dumps(catalog.manifest(),sort_keys=True,
                  ensure_ascii=False).encode()), site_files=len(catalog.coverage["site_files"]),
                  summary=summary(rows), rows=rows, owner_comparisons=pairs)
    if compared:
        result["matched_p0"] = summary([r for r in rows if r["id"] in owner_ids])
        result["matched_assisted"] = summary(compared)
    output = json.dumps(result, ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output,end="")


if __name__ == "__main__":
    main()
