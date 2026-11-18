"""Bounded Russian query grammar. Unknown clauses stay visible as needs."""
from dataclasses import dataclass, replace
import re
import unicodedata

ALIASES = re.compile(
    r"(?<![\w-])(?:(?P<bkd>бкд[ -]*пк[ -]*(?:rf|рф)[ .-]*2|bkd[ -]*pk[ -]*rf[ .-]*2)"
    r"|(?P<sld>слдкс[ -]*1|sldks[ -]*1))(?![\w-]|\.\d)", re.I
)
UNSUPPORTED_MODEL = re.compile(r"(?<!\w)(?:бкд[ -]*пк|bkd[ -]*pk|слдкс|sldks)[ -]*[\w.-]+", re.I)
POLICY = "loopback-v1"
DICTIONARY = "russian-two-entity-v1"


@dataclass(frozen=True)
class QuestionNeed:
    id: str
    span: tuple[int, int]
    entity: str | None
    attribute: str
    variant: str | None = None


PATTERNS = (
    ("compatibility", r"совместим|подходит|использовать.+(?:в|с)\s|входит ли"),
    ("terminal", r"клемм|распинов|контакт|подключить|схем[ауеы]"),
    ("temperature", r"температур"),
    ("mass", r"масс|вес"),
    ("dimensions", r"габарит|размер"),
    ("ethernet", r"(?:скорост|уровень).*ethernet"),
    ("interfaces", r"интерфейс"),
    ("dc", r"постоянн"),
    ("ac", r"переменн"),
    ("power", r"питан|напряжен"),
    ("composition", r"состав|компонент"),
    ("generation", r"поколен|выпускал|подтверди серию"),
    ("application", r"применя|применени"),
    ("purpose", r"назначен|что такое|для чего|функци[юя]|предназнач"),
    ("feature", r"функци|возможност"),
    ("wifi", r"wi[ -]?fi|вай[ -]?фай"),
)
SPLIT = re.compile(
    r"[?!;\n]|\.(?=\s|$)|,(?!\d)"
    r"|\s+(?:и|а еще|а также|а|или|затем|плюс|а заодно)\s+"
)
RESET = re.compile(r"^забудь предыдущие вопросы[.!?;\s]*", re.I)
OVERRIDE = re.compile(r"игнорируй.{0,25}инструкц|придумай.{0,30}характеристик|"
                      r"(?:^|\s)(?:system|developer|assistant)\s*:|https?://", re.I)


def normalize(text):
    return unicodedata.normalize("NFC", text).lower().translate(
        str.maketrans({"‑": "-", "–": "-", "—": "-", "−": "-", "ё": "е"})
    )


def entities(text):
    return tuple(dict.fromkeys(match.lastgroup for match in ALIASES.finditer(text)))


def spans(question):
    start = RESET.match(question)
    left = start.end() if start else 0
    for sep in SPLIT.finditer(normalize(question), left):
        if question[left:sep.start()].strip(" ,:"):
            yield left, sep.start()
        left = sep.end()
    if question[left:].strip(" ,:"):
        yield left, len(question)


def finalize(question, anchors, referent):
    normalized = normalize(question)
    explicit = entities(normalized)
    active = None if RESET.match(question) else referent
    needs = []
    comparison = bool(re.search(r"сравни|разниц", normalized))
    comparator_needs = None
    if re.search(r"совместим|подходит ли|можно ли использовать|входит ли", normalized):
        if len(explicit) == 2 and len(anchors) == 1 and not any(
            re.search(regex, normalized) for key, regex in PATTERNS if key not in {"compatibility", "purpose"}
        ):
            return [QuestionNeed("n1", (0, len(question)), explicit[0], "compatibility")], None
    for start, end in anchors:
        clause = normalized[start:end].strip()
        mentions = entities(clause)
        if UNSUPPORTED_MODEL.search(ALIASES.sub("", clause)):
            needs.append(QuestionNeed(f"n{len(needs)+1}", (start, end), None, "unknown"))
            continue
        if clause in {"если да", "если это так"} and needs:
            continue
        # Corrections update referent selection without supplying technical facts.
        if mentions and re.fullmatch(r"(?:нет,?\s*)?(?:я )?спрашивал(?:а)? (?:про|о) .+", clause):
            if ALIASES.sub("", clause).strip().endswith(("про", "о")):
                active = mentions[0] if len(mentions) == 1 else None
                continue
        model = mentions[0] if len(mentions) == 1 else active if not mentions else None
        if mentions:
            active = model
        if not model and not mentions and len(explicit) == 1:
            model = explicit[0]
        matches = {key for key, regex in PATTERNS if re.search(regex, clause)}
        if matches & {"dc", "ac"}:
            matches.discard("power")
        if "purpose" in matches:
            matches.discard("feature")
        if "ethernet" in matches:
            matches.discard("interfaces")
        attribute = next(iter(matches)) if len(matches) == 1 else "ambiguous" if matches else "unknown"
        if re.search(r"где|да[йи].*ссыл|найти|ссылк", clause) and re.search(r"руководств|документ", clause):
            attribute = "manual"
        elif re.search(r"руководств|pdf|паспорт", clause) and attribute != "terminal":
            attribute = "pdf"
        if re.search(r"блока питания|двигател|хранени|цвет|влажност|погрешност|мощност|антенн|парол|срок службы", clause):
            attribute = "unknown"
        variant = None
        if attribute == "composition":
            variant = "m2" if re.search(r"[мm]2", clause) and "без компьютер" not in clause else "unresolved"
        elif attribute == "generation" and model == "sld" and re.search(r"[мm]2", clause):
            variant = "m2"
        elif model == "sld" and re.search(r"серии\s+[мm]|поколени[ея]\s*[123]", clause):
            if attribute not in {"generation", "manual"}:
                variant = "unresolved"
        if comparison and len(explicit) == 2 and attribute not in {"unknown", "ambiguous", "compatibility"}:
            for key in explicit:
                needs.append(QuestionNeed(f"n{len(needs)+1}", (start, end), key, attribute, variant))
            comparison = False
            comparator_needs = len(needs) - 2
        elif comparison is False and len(anchors) > 1 and clause and ALIASES.fullmatch(clause):
            if comparator_needs is not None and model == needs[comparator_needs + 1].entity:
                for i in (comparator_needs, comparator_needs + 1):
                    needs[i] = replace(needs[i], span=(needs[i].span[0], end))
                comparator_needs = None
            else:
                needs.append(QuestionNeed(f"n{len(needs)+1}", (start, end), model, "unknown"))
        else:
            needs.append(QuestionNeed(f"n{len(needs)+1}", (start, end), model, attribute, variant))
    if not needs:
        needs.append(QuestionNeed("n1", (0, len(question)), active, "unknown"))
    return needs, active if len(explicit) < 2 else None
