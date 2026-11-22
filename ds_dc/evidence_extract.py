"""Literal material and coordinates recovered from immutable local sources."""
from dataclasses import asdict
import hashlib
import re

from ds_pilot.discovery import front

from .corpus import digest
from .evidence_lab import nfc_text
from .structural_pdf import physical_rows, unresolved_table_context
from .technical_verifier import HEADER_ROLES, word

SITE_FIELDS = {"title", "name", "summary", "description", "applications", "features", "notice",
               "interfaces", "protocols", "connectors", "specs"}
FIELD = re.compile(r"([a-z_]+)(?:\[([0-9]{1,3})\])?")
LINES = re.compile(r"line:([1-9][0-9]{0,5})(?:-([1-9][0-9]{0,5}))?")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
MARKUP_BOUNDARY = re.compile(r"^\s*(?:[|<>]|[>]|\x60{3}|~{3}|(?:[-*+] |[0-9]+\. ))")


def site_identity(source, page):
    if not page:
        return False
    raw = page["raw"].encode("utf-8")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()
    return (page["id"], page["canonical"], page["commit"], page["blob"], blob, digest(raw)) == (
        source.doc_id, source.url, source.commit, source.blob, source.blob, source.sha256)


def site_fragment(raw, field, quote):
    lines, end, data = front(raw.encode("utf-8"))
    key = FIELD.fullmatch(field)
    if key and key[1] in SITE_FIELDS:
        value = data.get(key[1])
        if key[2] is not None:
            index = int(key[2])
            if not isinstance(value, list) or index >= len(value):
                return None
            value = value[index]
        if key[1] == "specs" and isinstance(value, dict) and set(value) == {"name", "value"}:
            if not all(isinstance(value[k], str) and value[k].strip() for k in value):
                return None
            value = f'{value["name"]}: {value["value"]}'
        if not isinstance(value, str) or nfc_text(value) != quote:
            return None
        # A sibling limitation is material context even for a scalar summary.
        notice = data.get("notice")
        context = [notice] if isinstance(notice, str) and value != notice else []
        return dict(text=value, context=context, context_limited=value.endswith(("…", "...")),
                    locator={"field": field})
    span = LINES.fullmatch(field)
    if not span:
        return None
    first, last = int(span[1]), int(span[2] or span[1])
    if not end + 2 <= first <= last <= len(lines) or last - first >= 20:
        return None

    def boundary(line):
        return not line.strip() or HEADING.match(line)

    block = lines[first - 1:last]
    if (not all(line.strip() and not HEADING.match(line) and not MARKUP_BOUNDARY.match(line) for line in block)
            or not boundary(lines[first - 2]) and first != end + 2
            or last < len(lines) and not boundary(lines[last])):
        return None
    text = "\n".join(block)
    if nfc_text(text) != quote:
        return None
    heading = next((line for line in reversed(lines[end + 1:first - 1]) if HEADING.match(line)), data["title"])
    notice = data.get("notice")
    before = lines[first - 3] if first - 3 > end and not lines[first - 2].strip() else ""
    after = lines[last + 1] if last + 1 < len(lines) and not lines[last].strip() else ""
    context = [heading, *[line for line in (before, after, notice) if isinstance(line, str) and line.strip()]]
    return dict(text=text, context=context, locator={"field": field, "lines": [first, last]})


def bounds(line):
    return [line[key] for key in ("x0", "top", "x1", "bottom")]


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def pdf_fragment(page, quote, entity):
    rows = []
    table_match = False
    for row in physical_rows(page):
        if not any(cell and nfc_text(cell["text"]) == quote for cell in row.cells):
            continue
        table_match = True
        if not row.boxed or any(cell is None for cell in row.cells):
            return None
        # A vertical merge is represented by the origin and full box in every row.
        fields = [(nfc_text(h[1]), nfc_text(c["text"])) for h, c in zip(row.headers, row.cells, strict=True)]
        variant = [value for heading, value in fields if HEADER_ROLES.get(word(heading)) == "variant" and value]
        unknown = any(value and HEADER_ROLES.get(word(heading)) is None for heading, value in fields)
        rows.append(dict(text="; ".join(f"{label or 'Колонка без заголовка'}: {value}" for label, value in fields),
                         context=[b["text"] for b in row.context],
                         action_present=any(value and HEADER_ROLES.get(word(label)) == "action"
                                            for label, value in fields),
                         context_limited=(unknown or bool(variant and variant != [entity.label])
                                          or unresolved_table_context(row)),
                         locator={"table": row.table, "group_rows": [row.row],
                                  "headers": row.headers, "cells": [row.cells],
                                  "context_boxes": [bounds(b) for b in row.context],
                                  "physical_rows": [asdict(row)]}))
    if table_match:
        # The same literal across unrelated rows is ambiguous. For a shared physical
        # merged cell, include the entire group it actually occupies.
        if not rows:
            return None
        signatures = []
        for row in rows:
            loc = row["locator"]
            signatures.append(tuple((loc["table"], cell["row"], cell["column"])
                                    for cell in loc["cells"][0] if nfc_text(cell["text"]) == quote))
        if any(len(signature) != 1 or signature != signatures[0] for signature in signatures):
            return None
        result = rows[0]
        for row in rows[1:]:
            result["text"] += "\n" + row["text"]
            result["context_limited"] |= row["context_limited"]
            result["action_present"] |= row["action_present"]
            for key in ("group_rows", "cells", "physical_rows"):
                result["locator"][key] += row["locator"][key]
        return result

    # Do not flatten a table or stitch noncontiguous text. Only tightly spaced
    # lines in one lane qualify, with an observable block boundary and punctuation.
    blocks = sorted(page.get("blocks", ()), key=lambda b: (b["top"], b["x0"]))
    matches = []
    for i, start in enumerate(blocks):
        def nearby(a, b):
            return 0 <= b["top"] - a["bottom"] <= 0.8 * (a["bottom"] - a["top"])

        if i == 0 and start["top"] < 24:
            continue
        if i and nearby(blocks[i - 1], start):
            continue
        group = [start]
        for following in blocks[i + 1:]:
            if not nearby(group[-1], following):
                break
            group.append(following)
        if (len(group) > 12 or any(abs(b["x0"] - start["x0"]) > 8 for b in group)
                or group[-1]["bottom"] > page.get("size", (0, float("inf")))[1] - 24
                or any(overlaps(bounds(b), t["bbox"]) for b in group for t in page["tables"])):
            continue
        text = "\n".join(b["text"] for b in group)
        if nfc_text(text) != quote or not text.rstrip().endswith((".", "!", "?")):
            continue
        # Nearby prose on the same physical page can qualify applicability.
        context = [b for b in blocks if not any(b is member for member in group)
                   and b["x0"] < max(member["x1"] for member in group)
                   and b["x1"] > start["x0"]
                   and (0 <= start["top"] - b["bottom"] <= 48
                        or 0 <= b["top"] - group[-1]["bottom"] <= 48)
                   and not any(overlaps(bounds(b), t["bbox"]) for t in page["tables"])]
        matches.append(dict(text=text, context=[b["text"] for b in context], context_limited=bool(context),
                            locator={"boxes": [bounds(b) for b in group],
                                     "context_boxes": [bounds(b) for b in context]}))
    return matches[0] if len(matches) == 1 else None
