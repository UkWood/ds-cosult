"""Bounded Russian query grammar. Unknown clauses stay visible as needs."""
from dataclasses import dataclass, replace
import re
import unicodedata

from .discovery import pins

# Only pinned product titles are aliases. In particular prefix matches cannot
# turn a different hardware revision into an existing device.
PRODUCT_NAMES = {f"device{i}": (s["key"], s["title"]) for i, s in enumerate(pins()["sources"])
                 if s["type"] == "device" and s["key"] != "bkd"}
product_aliases = "|".join(f"(?P<{group}>{re.escape(name)})"
                           for group, (_, name) in PRODUCT_NAMES.items())
ALIASES = re.compile(
    r"(?<![\w-])(?:(?P<bkd>бкд[ -]*пк[ -]*(?:rf|рф)[ .-]*2|bkd[ -]*pk[ -]*rf[ .-]*2)"
    r"|(?P<sld>слдкс[ -]*1|sldks[ -]*1)|" + product_aliases + r")(?![\w-]|\.\d)", re.I
)
UNSUPPORTED_MODEL = re.compile(r"(?<!\w)(?:бкд[ -]*пк|bkd[ -]*pk|слдкс|sldks)[ -]*[\w.-]+", re.I)
POLICY = "loopback-v1"
DICTIONARY = "russian-dossiers-v2"


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
    ("humidity", r"влажност"),
    ("lifetime", r"срок.{0,18}служб|срок эксплуатации|сколько лет.{0,22}(?:работ|служ)"),
    ("ip", r"степен[ьи] защиты|класс защиты|защита корпуса"),
    ("cold_start", r"холодн.{0,8}старт"),
    ("input_resistance", r"входн.{0,10}сопротивлен|сопротивлен.{0,25}вход"),
    ("ipl_length", r"длин.{0,20}(?:кабел|лини).{0,12}ипл"),
    ("radio", r"радиоканал|сколько sim|сколько сим"),
    ("temperature", r"температур"),
    ("mass", r"\bмасс|\bвес"),
    ("dimensions", r"габарит|размер|сколько (?:места|пространства).{0,12}займ"),
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
    return tuple(dict.fromkeys(PRODUCT_NAMES.get(match.lastgroup, (match.lastgroup,))[0]
                               for match in ALIASES.finditer(text)))


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
        if needs and re.fullmatch(r"(?:поколение|серию|конфигурацию) (?:не знаю|не помню)", clause):
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
        if "composition" in matches:
            matches.discard("generation")
        if "purpose" in matches:
            matches.discard("feature")
        if "ethernet" in matches:
            matches.discard("interfaces")
        attribute = next(iter(matches)) if len(matches) == 1 else "ambiguous" if matches else "unknown"
        if re.search(r"где|да[йи].*ссыл|найти|ссылк", clause) and re.search(r"руководств|документ", clause):
            attribute = "manual"
        elif re.search(r"руководств|pdf|паспорт", clause) and attribute != "terminal":
            attribute = "pdf"
        if re.search(r"блока питания|двигател|хранени|цвет|погрешност|мощност|антенн|парол", clause):
            attribute = "unknown"
        pdf_intents = []
        if re.search(r"(?:sim|сим)[ -]*карт", clause) and re.search(r"одновременн|переключ", clause):
            pdf_intents.append("pdf_sim_operation")
        if re.search(r"4g\s*div", clause) and re.search(r"разъ[её]м|куда |подключ", clause):
            pdf_intents.append("pdf_div_connector")
        if re.search(r"материал\w*.*корпус|из чего.*корпус", clause):
            pdf_intents.append("pdf_housing_material")
        if pdf_intents:
            attribute = pdf_intents[0] if len(pdf_intents) == 1 else "ambiguous"
            # These two named intents belong to the sole cellular controller in scope.
            if not model and not mentions and not explicit and attribute in {
                "pdf_sim_operation", "pdf_div_connector",
            }:
                model = active = "bkd"
        from .pdf_sources import requested_page
        page = requested_page(clause)
        if page and model in {"sld", "bkd"}:
            attribute = page
        variant = None
        if attribute == "composition":
            variants = set()
            if re.search(r"перв.{0,6} поколен|1[- ]*(?:го )?поколен|аналогов.{0,8}звук", clause):
                variants.add("gen1")
            if re.search(r"втор.{0,6} поколен|2[- ]*(?:го )?поколен|сери[ияю].{0,2}[мm]\b", clause):
                variants.add("gen2")
            if re.search(r"[мm]2\b|треть.{0,6} поколен|3[- ]*(?:го )?поколен", clause):
                standalone = re.search(r"без (?:персонального )?(?:компьютер|арм|пк)|автономн", clause)
                variants.add("m2_standalone" if standalone else "m2")
            variant = next(iter(variants)) if len(variants) == 1 else "unresolved"
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
