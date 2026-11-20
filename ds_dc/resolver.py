"""Local entity matching with source-backed signals and conservative ambiguity handling."""
from collections import Counter
from difflib import SequenceMatcher
import math
import re
import unicodedata

from .corpus import SLD

MODEL_CHARS = str.maketrans("abcehkmoptxy", "авсенкмортху")
DASHES = str.maketrans("‐‑‒–—−", "------")
WORDS = re.compile(r"[^\W_]+", re.UNICODE)
CODES = re.compile(r"(?<!\w)[\w]+(?:[-./][\w]+)+(?!\w)")
STOP = set("для или как что это где чем они его меня нужен нужна дайте опишите сколько".split())
FOLLOW = re.compile(r"\b(?:он|она|оно|его|её|этот|него|неё)\b|^(?:а|и|тогда)\s+(?:если|что если)\b", re.I)
VARIANT = re.compile(r"(?:сери[яии]|модификаци[яии]|версии?)\s+[a-zа-я]*\d+|\b[мm]\d+\b", re.I)
FOREIGN_MODEL = re.compile(r"\b[а-яa-z]{2,}\s+\d+\b", re.I)
MULTI = re.compile(r"сравн|различ|отлич|взаимодейств|совместн|сопряж", re.I)


def model(value):
    val = unicodedata.normalize("NFC", value).casefold().translate(DASHES)
    val = re.sub(r"\s*([-./])\s*", r"\1", val)
    # Restrict confusable conversion to tokens containing Cyrillic.
    return re.sub(r"[\w./-]+", lambda m: m[0].translate(MODEL_CHARS)
                  if re.search("[а-яё]", m[0]) else m[0], val)


def tokens(value):
    return {word[:6] for word in WORDS.findall(value.casefold().replace("ё", "е"))
            if len(word) >= 4 and word not in STOP}


class Resolver:
    def __init__(self, entries):
        self.entries = {k: v for k, v in entries.items()
                        if v["kind"] in {"device", "software", "system"} and not v["draft"]}
        self.names = {}
        self.features = {}
        self.frequency = Counter()
        for entity, row in self.entries.items():
            aliases = [(row["title"], "title")]
            if entity == SLD and row["title"].endswith("СЛДКС-1"):
                aliases.append(("СЛДКС-1", "title: designation"))
            if row["features"].get("name"):
                aliases.append((row["features"]["name"], "name"))
            self.names[entity] = [(model(name), source) for name, source in aliases]
            fields = {**row["features"], "body": row["body"], "title": row["title"]}
            self.features[entity] = {key: tokens(str(value)) for key, value in fields.items()}
            self.frequency.update(set().union(*self.features[entity].values()))

    def resolve(self, question, active=(), hint=None):
        text = model(question)
        exact = []
        for entity, aliases in self.names.items():
            for alias, source in aliases:
                if re.search(r"(?<![\w./-])" + re.escape(alias) + r"(?![\w/-]|\.[\w])", text):
                    exact.append(dict(id=entity, score=1.0, signals=[source, alias]))
                    break
        codes = {code for code in CODES.findall(text) if any(char.isdigit() for char in code)}
        # Suffix variants have identity semantics. A misspelt prefix can suggest a
        # candidate only when the entire numeric suffix is still identical.
        known = {part for aliases in self.names.values() for alias, _ in aliases for part in CODES.findall(alias) if any(c.isdigit() for c in part)}
        unknown = codes - known - {"rs-485", "rs-232", "rs-422", "rс-485", "rс-232"}
        fuzzy = []
        for code in sorted(unknown):
            suffix = re.search(r"\d.*", code)[0]
            for entity, aliases in self.names.items():
                for alias, field in aliases:
                    if (alias in known and re.search(r"\d.*", alias)[0] == suffix
                            and SequenceMatcher(None, code, alias).ratio() >= 0.90):
                        fuzzy.append(dict(id=entity, score=0.90, signals=[field, alias, code]))
        if unknown:
            if exact or len(unknown) != 1 or len({x["id"] for x in fuzzy}) != 1:
                return self.result("unknown_or_ambiguous_model", [], exact + fuzzy, sorted(unknown))
            return self.result("fuzzy_model", [fuzzy[0]["id"]], fuzzy)
        if exact:
            if VARIANT.search(question):
                return self.result("variant_requires_clarification", [], exact)
            if MULTI.search(question) and re.search(r"\b(?:его|её|него|неё|этот|этого)\b", question, re.I):
                if not active:
                    return self.result("unbound_comparison", [], exact)
                return self.result("comparison_with_active", [*active, *(item["id"] for item in exact)], exact)
            if len(exact) > 1 and not MULTI.search(question):
                return self.result("ambiguous_models", [], exact)
            return self.result("explicit_models", [item["id"] for item in exact], exact)

        terms = tokens(question)
        ranked = []
        for entity, features in self.features.items():
            matched = {field: sorted(terms & words) for field, words in features.items() if terms & words}
            unique = set().union(*(set(words) for words in matched.values()))
            if len(unique) >= 2:
                score = sum(math.log1p(len(self.entries) / self.frequency[word]) for word in unique)
                score += 1.5 * len(set(matched.get("summary", [])) | set(matched.get("title", [])))
                ranked.append(dict(id=entity, score=round(score, 4), signals=matched))
        ranked.sort(key=lambda item: (-item["score"], item["id"]))
        best = ranked[:5]
        if best and best[0]["score"] >= 7 and (len(best) == 1 or best[0]["score"] >= best[1]["score"] * 1.35):
            return self.result("lexical", [best[0]["id"]], best)
        if len(best) >= 2 and best[0]["score"] >= 7:
            return self.result("ambiguous_function", [], best)
        if active and FOLLOW.search(question) and not best and not FOREIGN_MODEL.search(question):
            return self.result("active", list(active), [])
        hints = [k for k, row in self.entries.items() if hint == row["canonical"]]
        if hints and FOLLOW.search(question) and not best and not active and not FOREIGN_MODEL.search(question):
            return self.result("page_hint", hints, [])
        return self.result("clarification", [], best)

    def result(self, reason, selected, candidates, unknown=()):
        return dict(reason=reason, selected=sorted(set(selected)), unknown=list(unknown),
                    candidates=[dict(item, source=self.entries[item["id"]]["path"])
                                for item in candidates])
