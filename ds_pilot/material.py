"""Index source units separately from the typed, claim-eligible ledger."""
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import math
import re

import yaml


@dataclass(frozen=True)
class Passage:
    key: str
    locator: str
    start: int
    stop: int
    heading: str
    text: str
    raw: str
    url: str = ""


def passages(key, lines, end, data):
    node = yaml.compose("\n".join(lines[1:end]), Loader=yaml.SafeLoader)
    for field, val in node.value:
        name = field.value
        if name in {"images","imageDark","oldUrl","legacyId","videos"}:
            continue
        seq = isinstance(val, yaml.SequenceNode)
        items = val.value if seq else [val]
        for idx, item in enumerate(items):
            value = data[name][idx] if seq else data[name]
            start = item.start_mark.line + 2
            stop = max(start, item.end_mark.line + (2 if item.end_mark.column else 1))
            locator = f"{name}[{idx}]" if seq else name
            yield Passage(key, locator, start, stop, name,
                          value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
                          "\n".join(lines[start-1:stop]))
    heading, headers = "", []
    for n, line in enumerate(lines[end+1:], end+2):
        clean = line.strip()
        if not clean or clean.startswith(("![", "<", "[")):
            continue
        if clean.startswith("#"):
            heading = clean.lstrip("# ").strip()
        if clean.startswith("|"):
            cells = [c.strip() for c in clean.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue
            if not headers:
                headers = cells
            elif len(headers) == len(cells):
                clean = ", ".join(f"{c}: {v}" for c,v in zip(headers,cells))
        else:
            headers = []
        yield Passage(key, f"body:L{n}", n, n, heading, clean, line)


def tokens(text):
    return {word[:5] if len(word) > 5 else word for word in
            re.findall(r"[а-яa-z0-9]+", text.lower().replace("ё","е")) if len(word)>1}


class LexicalIndex:
    def __init__(self):
        self.postings = defaultdict(list)
        self.units = []

    def add(self, passage, title):
        i = len(self.units)
        self.units.append(passage)
        for token in tokens(f"{title} {passage.heading} {passage.text}"):
            self.postings[token].append(i)

    def search(self, question, entity, limit):
        scores = Counter()
        for token in tokens(question):
            ids = self.postings.get(token, ())
            weight = math.log(1 + len(self.units)/(1+len(ids)))
            for idx in ids:
                if entity is None or self.units[idx].key == entity:
                    scores[idx] += weight
        return [self.units[i] for i,_ in scores.most_common(max(0,min(limit,20)))]
