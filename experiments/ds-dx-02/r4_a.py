"""Prepare, freeze and run the fixed six-chat owner experiment."""
import argparse
import getpass
import json
import os
import time
from pathlib import Path
from zipfile import ZipFile

from bundle import archive, sums
from compile_d import facts, multipart, payload, response_object, uploaded
from protocol import (PAGE, Ledger, Stop, encode, kernel_release, live_gate, load, locked,
                      money, offline, reply, reserve, runtime_digest, save, sha, transport)
from reconcile import safe_diagnostic, summarize
from sources import verify

RECIPE = Path(__file__).with_name("configs") / "r4-a.json"
R2_FLOOR, R3_FLOOR, R3_HELD = 5_267_700, 156_373_932, 304_915_200
ORIGINAL_COMPILE, ORIGINAL_TOTAL = 2 * 10**9, 5 * 10**9


def plan(root, *, recipe=None):
    recipe = load(RECIPE) if recipe is None else recipe
    snapshot = verify(root, reparse=False)
    website = load(root / "source-manifest.json")
    context = load(root / "plan/context.json")
    imagery = load(root / "plan/images.json")
    a, p, v = (recipe[key] for key in ("astro", "pdf", "visual_source"))
    page = recipe["visual_page"]
    records = website["records"]
    for key, kind in ((a, "astro"), (p, "pdf"), (v, "pdf")):
        if records[key]["kind"] != kind:
            raise Stop("Unexpected sample source kind")
    if (website["commit"] != recipe["astro_commit"] or len(context[a]) != recipe["astro_lines"] or len(context[p]) != recipe["pdf_pages"]
            or records[p]["sha256"] != recipe["pdf_sha256"] or v == p
            or records[v]["sha256"] != recipe["visual_pdf_sha256"] or not 1 <= page <= len(context[v])
            or len(set(recipe["visual_images"])) != len(recipe["visual_images"])
            or not 1 <= len(recipe["visual_images"]) <= 3 or not recipe["visual_review"].strip()):
        raise Stop("R4-A evidence differs from selected source pins")
    images = {}
    for name in recipe["visual_images"]:
        row = imagery[name]
        if row["source"] != v or row["page"] != page or not name.endswith(".png"):
            raise Stop("Visual candidate is outside the selected engineering page")
        images[name] = {key: row[key] for key in ("sha256", "size", "bbox_render_pixels_top_left")}
    families = [("A", a, list(range(1, len(context[a]) + 1)), [], 8192),
                ("P", p, list(range(1, len(context[p]) + 1)), [], 8192),
                ("V", v, [page], recipe["visual_images"], 4096)]
    ordered = []
    for name, source, numbers, names, limit in families:
        for tag, mode in (("D", "disabled"), ("L", "low")):
            ordered.append(dict(id=f"{name}-{tag}", mode=mode, reserve_nd=reserve(limit),
                 task=dict(id=name, kind="vision" if names else "extract", topic="technical-evidence",
                           scope={source: numbers}, images=names, limit=limit, deps=[],
                           instruction="Извлеки существенные сведения, условия и пробелы.")))
    upload = dict(source=p, pages=len(context[p]), sha256=records[p]["sha256"],
                  size=records[p]["size"], reserve_nd=PAGE * len(context[p]), before="P-D")
    return dict(schema=1, snapshot=snapshot, runtime=runtime_digest(), kernel=kernel_release(),
                cases=ordered, upload=upload, planner_calls=0, maximum_chat_calls=6,
                graph_bound_nd=upload["reserve_nd"] + sum(c["reserve_nd"] for c in ordered),
                first_reserve_nd=ordered[0]["reserve_nd"], visual=images,
                visual_review=recipe["visual_review"])


def draft_card(root, experiment):
    context = load(root / "plan/context.json")
    a, = experiment["cases"][0]["task"]["scope"]
    p = experiment["upload"]["source"]
    entries = []
    for n, category in ((17, "mandatory"), (19, "mandatory"), (28, "safety"),
                        (30, "safety"), (33, "safety"), (39, "additional"),
                        (44, "mandatory"), (71, "mandatory")):
        entries.append(dict(sample="A", locator=f"{a}:{n}", category=category,
                            expected=context[a][n - 1].strip(),
                            criterion="Смысл, диапазон, единицы, условия и реквизиты совпадают с оригиналом."))
    anchors = ((2, "Утилита «RASOS» позволяет", "mandatory"),
               (3, "Проверка правильности", "mandatory"),
               (4, "имеется возможность", "additional"),
               (6, "В один момент времени", "safety"),
               (7, "синхронизация времени с", "mandatory"),
               (8, "В обоих случаях файлы обновлений", "safety"))
    for n, anchor, category in anchors:
        lines = [line.strip() for line in context[p][n - 1].splitlines() if line.strip()]
        position = next(i for i, line in enumerate(lines) if anchor.casefold() in line.casefold())
        entries.append(dict(sample="P", locator=f"{p}:{n}", category=category,
                            expected=" ".join(lines[position:position + 3]),
                            criterion="Уточните границы утверждения по странице и сохраните условия применения."))
    for name, meta in experiment["visual"].items():
        entries.append(dict(sample="V", locator="I:" + name, category="mandatory",
                            region=meta["bbox_render_pixels_top_left"], expected="",
                            criterion="После просмотра укажите точную область и читаемые обозначения, связи и номера контактов."))
    for number, item in enumerate(entries, 1):
        item["id"] = f"{item['sample']}-{number:02}"
    return dict(revision="draft-1", snapshot=experiment["snapshot"], entries=entries)


def validate_card(card, experiment):
    if (card["snapshot"] != experiment["snapshot"] or not isinstance(card["revision"], str)
            or not card["revision"].strip() or card["revision"].startswith("draft")):
        raise Stop("Use an engineering-reviewed card with a new revision")
    cases = {case["id"][0]: case["task"] for case in experiment["cases"]}
    ids = set()
    for item in card["entries"]:
        label = item["id"]
        if (not isinstance(label, str) or not label.isascii() or not label.replace("-", "").isalnum()
                or len(label) > 32 or label in ids):
            raise Stop("Engineering card requires unique short item IDs")
        ids.add(label)
        task = cases[item["sample"]]
        loc = item["locator"]
        permitted = {f"{key}:{n}" for key, ns in task["scope"].items() for n in ns}
        allowed = {"I:" + name for name in task["images"]} if item["sample"] == "V" else permitted
        if (loc not in allowed or not item["expected"].strip() or not item["criterion"].strip()
                or item["category"] not in {"mandatory", "additional", "safety"}):
            raise Stop("Incomplete or out-of-scope engineering card")
        if item["sample"] == "V":
            box = item.get("region")
            anchor = experiment["visual"][loc[2:]]["bbox_render_pixels_top_left"]
            if (not isinstance(box, list) or len(box) != 4 or any(type(n) is not int for n in box)
                    or not anchor[0] <= box[0] < box[2] <= anchor[2]
                    or not anchor[1] <= box[1] < box[3] <= anchor[3]):
                raise Stop("Visual criterion needs a region inside the selected image")
    if {item["sample"] for item in card["entries"]} != {"A", "P", "V"}:
        raise Stop("Engineering card must cover A, P and V")


def finances(workspace, *, include_r4_a=False, include_r4_c=False):
    r2 = summarize(workspace / "private-state/ledger.json")
    r3 = summarize(workspace / "private-r3/ledger.json")
    # An independent billing CSV cannot remove the old UNKNOWN hold.
    def compile_exposure(report):
        return report["unmatched_retained_nd"] + sum(
            row["cost_nd"] or row["retained_nd"] for row in report["operations"] if row["stage"] == "compile")

    r2_compile, r3_compile = map(compile_exposure, (r2, r3))
    r2_counted = max(R2_FLOOR, r2["spent_nd"] + r2["retained_nd"])
    r3_counted = max(R3_FLOOR + R3_HELD, r3["spent_nd"] + r3["retained_nd"])
    compile_counted = max(R2_FLOOR, r2_compile) + max(R3_FLOOR + R3_HELD, r3_compile)
    report = dict(r2_sha256=r2["ledger_sha256"], r3_sha256=r3["ledger_sha256"],
                  r2_counted_nd=r2_counted, r3_counted_nd=r3_counted, r3_minimum_hold_nd=R3_HELD,
                  max_compile_nd=ORIGINAL_COMPILE - compile_counted,
                  max_total_nd=ORIGINAL_TOTAL - r2_counted - r3_counted)
    for name, include in (("r4-a", include_r4_a), ("r4-c", include_r4_c)):
        if include:
            r4 = summarize(workspace / f"private-{name}/ledger.json")
            exposure = r4["spent_nd"] + r4["retained_nd"]
            field = name.replace("-", "_")
            report.update({field + "_sha256": r4["ledger_sha256"], field + "_counted_nd": exposure,
                           "max_compile_nd": report["max_compile_nd"] - exposure,
                           "max_total_nd": report["max_total_nd"] - exposure})
    return report


def metrics(result, task, diagnostic):
    issue = {}
    obj = response_object(result)
    try:
        json.loads(result["text"])
        json_valid = True
    except (ValueError, RecursionError):
        json_valid = False
    state, rows = facts(result, task, issue=issue, obj=obj)
    usage = result["usage"]
    tokens, reasoning = usage["completion_tokens"], usage["reasoning_tokens"]
    finish = result["finish_reason"]
    safe_finish = finish if finish in {"stop", "length", "content_filter", "tool_calls", "insufficient_system_resource"} else "other"
    return dict(status=state, finish_reason=safe_finish, valid_json=json_valid,
                accepted=len(rows), rejected=sum(issue.get("rejected_rows", {}).values()), issue=issue,
                scope=task["scope"], images=task["images"], visual_observations=sum(
                    row["kind"] == "visual_observation" and any(loc.startswith("I:") for loc in row["locators"])
                    for row in rows), mode_reported=result.get("reported_mode"), model=result["model"],
                reasoning_fraction=reasoning / tokens if reasoning is not None and tokens else None,
                usage=usage, cache_hit_fraction=usage["prompt_cache_hit_tokens"] / usage["prompt_tokens"]
                if usage["prompt_tokens"] else None, peak_nd=result["cost_nd"],
                elapsed_ms=diagnostic["elapsed_ms"] if diagnostic else None), rows


def run_matrix(root, experiment, journal, post, reports, *, execution="mock", streaming=False, reused_file=None):
    website = load(root / "source-manifest.json")
    context = load(root / "plan/context.json")
    rows, reviewed = {}, {}
    result = dict(execution=execution, status="PARTIAL", cases=rows,
                  graph_bound_nd=experiment["graph_bound_nd"], snapshot=experiment["snapshot"])
    handles = {}
    upload = experiment["upload"]
    if reused_file is not None:
        handles[upload["source"]] = dict(reused_file, first=1, last=upload["pages"])
    name = journal.stage

    def perform(case):
        task = case["task"]
        source, = task["scope"]
        if case["id"] == upload["before"] and reused_file is None:
            raw = (root / "pdf" / (source + ".pdf")).read_bytes()
            if sha(raw) != upload["sha256"]:
                raise Stop("Sample PDF hash changed")
            body, mime = multipart(raw)
            file = journal.execute("pdf-upload", "/files", body, upload["reserve_nd"], post,
                        lambda response: uploaded(response, upload["size"], upload["pages"]), content_type=mime)
            if file["expires_at"] <= time.time():
                raise Stop("Sample provider file expired")
            handles[source] = dict(file, first=1, last=upload["pages"])
        if source in handles and handles[source]["expires_at"] <= time.time():
            raise Stop("Sample provider file expired")
        group = (source, {n: context[source][n - 1] for n in task["scope"][source]})
        body, prefix = payload(root, website, task, handles, {}, group, mode=case["mode"], streaming=streaming)
        response = journal.execute(case["id"], "/chat/completions", body, case["reserve_nd"], post,
                        lambda response: reply(response, task["limit"]), prefix=prefix)
        diag = safe_diagnostic(journal.path.parent / "diagnostics" / name / (case["id"] + ".json"))
        summary, accepted = metrics(response, task, diag)
        rows[case["id"]].update(summary, prefix_sha256=prefix)
        reviewed[case["id"]] = accepted

    for case in experiment["cases"]:
        rows[case["id"]] = dict(mode=case["mode"], status="DEFERRED", reserve_nd=case["reserve_nd"])
    active = None
    try:
        for case in experiment["cases"]:
            active = case["id"]
            perform(case)
        result["status"] = ("COMPLETE_UNREVIEWED" if all(row["status"] == "COMPLETE_UNREVIEWED"
                            for row in rows.values()) else "PARTIAL")
    except Stop as error:
        blocked = next((op for op in journal.data["ops"] if op["status"] in {"PENDING", "UNKNOWN"}), None)
        if blocked:
            rows[active]["status"] = "UNKNOWN"
            result["stop_reason"] = "UNKNOWN"
            result["blocking_operation"] = blocked["id"]
            result["transport"] = safe_diagnostic(journal.path.parent / "diagnostics" / name /
                                                  (blocked["id"] + ".json"))
        elif str(error).startswith("DEFERRED_BUDGET"):
            rows[active]["status"] = "DEFERRED_BUDGET"
            result["stop_reason"] = "DEFERRED_BUDGET"
        else:
            rows[active]["status"] = "FAILED"
            result["stop_reason"] = "LOCAL_INVARIANT"
    ops = journal.data["ops"]
    result["chat_attempts"] = sum(op["endpoint"] == "/chat/completions" for op in ops)
    result["upload_attempts"] = sum(op["endpoint"] == "/files" for op in ops)
    result["settled_peak_nd"] = sum(op["cost_nd"] for op in ops if op["status"] == "SETTLED")
    result["retained_nd"] = sum(op["reserve_nd"] for op in ops if op["status"] != "SETTLED")
    result["next_reserve_nd"] = None
    if result.get("stop_reason") == "DEFERRED_BUDGET":
        result["next_reserve_nd"] = (upload["reserve_nd"] if reused_file is None and active == upload["before"] and not
                                     any(op["id"] == "pdf-upload" for op in ops) else rows[active]["reserve_nd"])
    public = {"summary.json": encode(result)}
    public["SHA256SUMS"] = sums(public)
    archive(reports / f"{name}-summary.zip", public)
    private = journal.path.parent / "engineering"
    save(private / "facts.json", reviewed)
    sheet = {id_: dict(matched_required_ids=[], unsupported_claims=None, critical_omissions=[],
                      preserves_conditions_and_units=None, visual_false_positives=None, actual_billing_nd=None,
                      evidence_notes="") for id_ in reviewed}
    save(private / "review-template.json", sheet)
    md = [f"# {name.upper()} · проверка утверждений", "", "Проверьте каждое утверждение по замороженной карте и оригиналу.", ""]
    for id_, accepted in reviewed.items():
        md.extend([f"## {id_}", ""])
        for row in accepted:
            md.append(f"- {row['text']} · {row['applicability']} · {', '.join(row['locators'])}")
        md.append("")
    owner = {"facts.json": encode(reviewed), "review-template.json": encode(sheet),
             "REVIEW.md": "\n".join(md).encode(), "summary.json": encode(result)}
    owner["SHA256SUMS"] = sums(owner)
    archive(private / f"{name}-engineering.zip", owner)
    return result


def score(card, review, summary):
    available = {id_ for id_, row in summary["cases"].items() if "accepted" in row}
    if set(review) != available:
        raise Stop("Review must cover exactly the cases with inspected results")
    result = {}
    for id_, entry in review.items():
        sample = id_[0]
        required = {item["id"] for item in card["entries"] if item["sample"] == sample
                    and item["category"] in {"mandatory", "safety"}}
        matched, critical = set(entry["matched_required_ids"]), set(entry["critical_omissions"])
        if (not required or not matched <= required or not critical <= required - matched
                or type(entry["unsupported_claims"]) is not int or entry["unsupported_claims"] < 0
                or type(entry["preserves_conditions_and_units"]) is not bool
                or sample == "V" and (type(entry["visual_false_positives"]) is not int
                                       or entry["visual_false_positives"] < 0)
                or entry["actual_billing_nd"] is not None and (type(entry["actual_billing_nd"]) is not int
                                                               or entry["actual_billing_nd"] < 0)):
            raise Stop("Complete the engineering observations and link matched/omitted IDs to the card")
        expected_critical = {item["id"] for item in card["entries"]
                             if item["sample"] == sample and item["category"] == "safety"} - matched
        if not expected_critical <= critical:
            raise Stop("List all missing safety items as critical omissions")
        result[id_] = dict(entry, matched_required_count=len(matched), expected_required_count=len(required),
                           required_fraction=len(matched) / len(required))
    return dict(card_revision=card["revision"], status="ENGINEERING_REVIEW", cases=result)


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "freeze", "live", "score"):
        sub = subs.add_parser(name)
        sub.add_argument("--workspace", required=True, type=Path)
        if name in {"freeze", "live", "score"}:
            sub.add_argument("--card", required=True, type=Path)
        if name == "freeze":
            sub.add_argument("--reviewer", required=True)
        if name == "score":
            sub.add_argument("--review", required=True, type=Path)
        if name == "live":
            sub.add_argument("--owner-go", required=True)
            sub.add_argument("--owner-go-usd", required=True)
            sub.add_argument("--total-go-usd", required=True)
            sub.add_argument("--confirm-provider-contract", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    workspace = args.workspace.resolve(strict=True)
    root = workspace / "source-pilot"
    staging = workspace / "r4-a-plan"
    if args.command == "live":
        live_gate()
    else:
        offline()
    if args.command == "score":
        frozen = load(staging / "manifest-frozen.json")
        raw = args.card.read_bytes()
        if sha(raw) != frozen["card_sha256"]:
            raise Stop("Engineering card differs from the frozen hash")
        output = workspace / "private-r4-a/engineering/score.json"
        if output.exists():
            raise Stop("Engineering score already exists")
        report = workspace / "reports-r4-a/r4-a-summary.zip"
        checksum = report.with_suffix(".zip.sha256").read_text().split()[0]
        if sha(report.read_bytes()) != checksum:
            raise Stop("Summary ZIP differs from its checksum")
        with ZipFile(report) as package:
            result = score(json.loads(raw), load(args.review), json.loads(package.read("summary.json")))
        save(output, result)
        return
    experiment = plan(root)
    reserve_keys = ("maximum_chat_calls", "first_reserve_nd", "graph_bound_nd")
    print(encode(dict({key: experiment[key] for key in reserve_keys}, reserves_nd={
        **{case["id"]: case["reserve_nd"] for case in experiment["cases"]},
        "pdf-upload": experiment["upload"]["reserve_nd"],
    })).decode())
    if args.command == "prepare":
        staging.mkdir(mode=0o700)
        save(staging / "draft-card.json", draft_card(root, experiment))
        save(staging / "manifest-draft.json", experiment)
        return
    card_bytes = args.card.read_bytes()
    validate_card(json.loads(card_bytes), experiment)
    finance = finances(workspace)
    preflight = load(workspace / "preflight-r4/preflight.json")
    if any(preflight.get(key) != value for key, value in dict(snapshot=experiment["snapshot"],
            runtime=experiment["runtime"], kernel=experiment["kernel"], experiment_sha256=sha(encode(experiment)),
            offline="seccomp: socket EPERM", paid_calls=0, package_count=3).items()):
        raise Stop("Run the pinned offline R4 preflight on this WSL host")
    if load(staging / "manifest-draft.json") != experiment:
        raise Stop("Prepared experiment differs from current pins")
    frozen = staging / "manifest-frozen.json"
    expected = dict(experiment=experiment, card_sha256=sha(card_bytes), financial_baseline=finance)
    if args.command == "freeze":
        if frozen.exists() or not args.reviewer.strip():
            raise Stop("Frozen manifest already exists or missing reviewer")
        save(frozen, dict(expected, reviewer=args.reviewer))
        print(encode(finance).decode())
        print("Frozen manifest SHA256 " + sha(frozen.read_bytes()))
        return
    baseline = load(frozen)
    if any(baseline.get(key) != value for key, value in expected.items()):
        raise Stop("Frozen experiment, engineering card or original financial evidence changed")
    cap, total = money(args.owner_go_usd), money(args.total_go_usd)
    if (not args.confirm_provider_contract or not args.owner_go.strip()
            or not cap <= min(total, finance["max_compile_nd"]) or total > finance["max_total_nd"]
            or cap < experiment["first_reserve_nd"]):
        raise Stop("Confirm provider contract and approve caps within the original remaining ceilings")
    state, reports = workspace / "private-r4-a", workspace / "reports-r4-a"
    if state.is_symlink() or reports.is_symlink() or reports.exists():
        raise Stop("Require fresh nonsymlink experiment paths")
    with locked(state):
        if set(p.name for p in state.iterdir()) != {".lock"} or reports.exists():
            raise Stop("R4-A is single-use; inspect the existing experiment offline")
        identity = sha(encode([sha(frozen.read_bytes()), cap, total, args.owner_go]))
        journal = Ledger(state / "ledger.json", "r4-a", cap, total, identity)
        key = getpass.getpass("Ключ DeepSeek: ")
        if not key:
            raise Stop("Empty key")
        save(state / "owner-go.json", dict(owner_go=args.owner_go, identity=identity, cap_nd=cap,
                                          total_nd=total, manifest_sha256=sha(frozen.read_bytes())))
        result = run_matrix(root, experiment, journal, transport(key), reports, execution="live")
        if result["status"] == "PARTIAL":
            raise Stop("R4-A PARTIAL; inspect the generated summary and offline diagnostics")


if __name__ == "__main__":
    try:
        main()
    except (Stop, OSError, ValueError, TypeError, KeyError) as error:
        raise SystemExit(str(error) if isinstance(error, Stop) else type(error).__name__) from None
