"""Sample actual table extraction on layout candidates, retaining diagnostics only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

import pdfplumber

from ds_pilot.pdf_sources import safe_grid

from .pdf_policy import pdf_tool


def inspect_tables(file, numbers):
    observations = []
    with pdfplumber.open(file) as pdf:
        for number in numbers:
            page = pdf.pages[number - 1]
            tables = page.extract_tables()
            observations.append(dict(page=number, tables=len(tables),
                                     structurally_complete=sum(safe_grid(table) for table in tables)))
            page.close()
    return observations


def report(case, directory):
    if case["state"] != "downloaded":
        return {"status": "unavailable"}
    candidates = case["layout_candidate_pages"]
    if not candidates:
        return {"status": "no_tabular_layout_signal", "pages": []}
    numbers = sorted({candidates[0], candidates[len(candidates) // 2], candidates[-1]})
    try:
        output = pdf_tool(sys.executable, "-m", "ds_dc.pdf_tables", "--sample",
                          directory / (case["sha256"] + ".pdf"), *numbers)
        stats = json.loads(output)
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"status": "table_parser_failed", "pages": numbers, "docling_review": True}
    found = sum(row["tables"] for row in stats)
    complete = sum(row["structurally_complete"] for row in stats)
    status = "grid_detected" if found and complete == found else "table_layout_review"
    return dict(status=status, pages=stats, docling_review=status != "grid_detected")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--sample", nargs="+")
    args = parser.parse_args()
    if args.sample:
        print(json.dumps(inspect_tables(args.sample[0], [int(x) for x in args.sample[1:]])))
        return
    source = args.cache / "audit.json"
    audit = json.loads(source.read_text())
    unique = {case["sha256"]: case for case in audit.values()
              if case["state"] == "downloaded" and "table_sample" not in case}
    with ThreadPoolExecutor(max_workers=6) as pool:
        stats = dict(zip(unique, pool.map(lambda case: report(case, args.cache), unique.values())))
    for case in audit.values():
        if case["kind"] == "pdf":
            case.setdefault("table_sample", stats.get(case.get("sha256"), {"status": "unavailable"}))
    pending = source.with_suffix(".pending")
    pending.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    pending.replace(source)


if __name__ == "__main__":
    main()
