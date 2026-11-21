"""Passive PDF checks for approved publisher bytes."""
import re
import subprocess
import tempfile

OWNER_EXCLUDED = {"https://www.mnppsaturn.ru/photos/2278872612744825.pdf"}
MAX_SIZE = 20_000_000
MAX_PAGES = 500


def pdf_tool(program, *args, warnings=None):
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        completed = subprocess.run(
            ["prlimit", "--as=536870912", "--cpu=15", "--fsize=16777216",
             "--", program, *map(str, args)], stdout=output, stderr=errors, timeout=20)
        errors.seek(0)
        stderr = errors.read(4096)
        if completed.returncode or (warnings is None and re.search(rb"syntax error|i/o error", stderr, re.I)):
            raise ValueError(f"{program}: exit={completed.returncode}, parser diagnostics={bool(stderr)}")
        if warnings is not None and stderr:
            warnings.append(program)
        output.seek(0)
        return output.read().decode("utf-8", errors="replace")


def inspect_pdf(path, *, max_size=MAX_SIZE, max_pages=MAX_PAGES):
    if not 0 < path.stat().st_size <= max_size:
        return {"state": "size_limit"}
    with path.open("rb") as stream:
        header = stream.read(8)
        stream.seek(max(0, path.stat().st_size - 1024))
        if not header.startswith(b"%PDF-") or b"%%EOF" not in stream.read():
            return {"state": "invalid_pdf"}
    warnings = []
    try:
        metadata = pdf_tool("pdfinfo", path, warnings=warnings)
        found = re.search(r"^Pages:\s+(\d+)", metadata, re.M)
        pages = int(found[1]) if found else 0
        if not 0 < pages <= max_pages:
            return dict(state="page_limit_or_invalid_count", pages=pages)
        chunks = []
        batches = [(1, pages)] if pages <= MAX_PAGES else [
            (first, min(first + 99, pages)) for first in range(1, pages + 1, 100)]
        for first, last in batches:
            page_range = ["-f", first, "-l", last] if len(batches) > 1 else []
            layout = pdf_tool("pdftotext", *page_range, "-layout", "-enc", "UTF-8", path, "-",
                              warnings=warnings)
            batch = layout.split("\f")
            if batch and not batch[-1].strip():
                batch.pop()
            if len(batch) != last - first + 1:
                return dict(state="page_count_mismatch", pages=pages, pages_processed=len(chunks) + len(batch))
            chunks.extend(batch)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        return dict(state="structure_check_failed", parser_error=type(exc).__name__,
                    pages=locals().get("pages"))
    thin = [i for i, page in enumerate(chunks, 1) if sum(c.isalpha() for c in page) < 20]
    garbled = [i for i, page in enumerate(chunks, 1) if "\ufffd" in page or "(cid:" in page]
    tabular = [i for i, page in enumerate(chunks, 1)
               if sum(bool(re.search(r"\S {3,}\S", row)) for row in page.splitlines()) >= 3]
    quality = "review_parser_warnings" if warnings else "text_sparse" if thin else "text_present"
    table_quality = "layout_review" if tabular else "no_tabular_layout_signal"
    return dict(state="extractable", structure="passive_poppler_all_pages", pages=pages,
                pages_processed=len(chunks), quality=quality, table_quality=table_quality,
                parser_warnings=warnings, sparse_pages=thin,
                encoding_warning_pages=garbled, layout_candidate_pages=tabular,
                ocr_review_pages=sorted(set(thin + garbled)),
                docling_review_pages=tabular)


def dossier_availability(states, *, has_pages):
    active = [state for state in states if state != "EXCLUDED_BY_OWNER"]
    return ("ready" if has_pages or "ready" in active else "not_ready",
            "partial" if any(state != "ready" for state in active) else "complete")
