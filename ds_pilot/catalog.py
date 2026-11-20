"""Offline import, typed assertions and candidate retrieval from immutable Git blobs."""
from dataclasses import asdict, dataclass, replace
import hashlib
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .discovery import COMMIT, SITE, discover, pins, front
from .material import LexicalIndex, passages


BUNDLE = "saturn-two-entity-site-084d7594-v1"
REPO = "https://github.com/UkWood/Saturn-Main-Site"
PINS = {
    "bkd": ("saturn:device:bkd-pk-rf-2", "БКД-ПК-RF.2",
            "src/content/products/bkd-pk-rf-2.md",
            "86afcfe8be3be4e5022f0baf43143f64a2a9f7a0"),
    "sld": ("saturn:system:sldks-1", "СЛДКС-1",
            "src/content/systems/sistema-liftovogo-dispetcherskogo-kontrolya-sldks-1.md",
            "42ed9f4a12a78dc4e91db91123c5ae20f9b3dca1"),
}


@dataclass(frozen=True)
class Entity:
    id: str
    name: str
    kind: str
    route: str


@dataclass(frozen=True)
class EvidenceRef:
    path: str
    locator: str
    route: str
    commit: str
    blob: str
    sha256: str
    snippet: str
    url: str
    parser: str = "saturn-site-v1"
    region: dict | None = None


@dataclass(frozen=True)
class Fact:
    id: str
    entity: str
    attribute: str
    value: object
    text: str
    evidence: EvidenceRef


@dataclass(frozen=True)
class Relation(Fact):
    configuration: str = "M2 с АРМ диспетчера"


@dataclass(frozen=True)
class DocumentReference(Fact):
    document_url: str = ""


def load_git(checkout: Path) -> dict[str, bytes]:
    files, inventory = discover(checkout)
    reference = pins()
    if any(value != reference[key] for key, value in inventory.items()):
        raise ValueError("Discovered corpus does not match the pinned inventory")
    return files


def import_checkout(checkout, data):
    files = load_git(checkout)
    catalog = Catalog(files)
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Publish the immutable bundle only after all writes and validation finish.
    target = data / catalog.coverage["bundle"]
    if not target.exists():
        with TemporaryDirectory(dir=data) as temporary:
            staging = Path(temporary) / "bundle"
            staging.mkdir()
            for key, raw in files.items():
                (staging / f"{key}.md").write_bytes(raw)
            (staging / "manifest.json").write_text(json.dumps(pins(), ensure_ascii=False, indent=2))
            try:
                staging.rename(target)
            except OSError:
                if not target.is_dir():
                    raise
    return load_local(data)


EXPANDED = "saturn-dossiers-084d7594-v2"


def load_local(data):
    directory = data / EXPANDED
    if directory.exists():
        return Catalog({s["key"]: (directory / (s["key"]+".md")).read_bytes()
                        for s in pins()["sources"]})
    return Catalog({key: (data / f"{key}.md").read_bytes() for key in PINS})


def typed_spec(name, value):
    """Compare structured/catalog representations, preserving ambiguous or qualified rows."""
    number = r"([+-]?\d+(?:[,.]\d+)?)"

    def numeric(text):
        return float(text.replace(",", "."))

    for label, attr, unit in (("масса","mass","кг"), ("средний срок службы","lifetime","лет")):
        if name == label:
            match = re.fullmatch(number + r"\s*" + unit, value.strip(), re.I)
            return attr, numeric(match[1]) if match else value
    if name == "габаритные размеры":
        match = re.fullmatch(r"\(?\s*" + r"\s*[хx×]\s*".join([number]*3) + r"\s*\)?\s*мм",
                             value.strip(), re.I)
        return "dimensions", [numeric(n) for n in match.groups()] if match else value
    if name.startswith("температура окружающего воздуха"):
        match = re.fullmatch(r"\(?\s*" + number + r"\s*(?:до|\.{2,}|…|–|-)\s*" + number
                             + r"\s*\)?\s*°?\s*[сc]",value.strip(),re.I)
        return "temperature", {"min":numeric(match[1]),"max":numeric(match[2])} if match else value
    if name.startswith("степень защиты оболочки"):
        match = re.match(r"(?:IP)?(\d{2})\b",value.strip(),re.I)
        return "ip", "IP"+match[1] if match else value
    return None


class Catalog:
    def __init__(self, files: dict[str, bytes]):
        self.entities = {}
        self.records = {}
        self.index = LexicalIndex()
        inventory = pins()
        legacy = files.keys() == PINS.keys()
        sources = [s for s in inventory["sources"] if not legacy or s["key"] in PINS]
        if files.keys() != {s["key"] for s in sources}:
            raise ValueError("Incomplete source bundle")
        self.coverage = {"bundle": BUNDLE if legacy else EXPANDED, "commit": COMMIT,
                         "site_files": [], "excluded_channels": [
                             "PDF без локального импорта: только метаданные",
                             "Чертежи, изображения, видео, ZIP и внешние сайты не индексируются"]}
        self.sources = {source["key"]: source for source in sources}
        for source in sources:
            key, path, blob, route = (source[k] for k in ("key","path","blob","route"))
            raw = files[key]
            header = f"blob {len(raw)}\0".encode()
            sha = hashlib.sha256(raw).hexdigest()
            if ((key in PINS and (path, blob) != PINS[key][2:])
                    or hashlib.sha1(header + raw).hexdigest() != blob or sha != source["sha256"]):
                raise ValueError(f"Invalid pinned blob: {path}")
            lines, end, data = front(raw)
            name = PINS[key][1] if key in PINS else source["title"]
            self.entities[key] = Entity(source["entity"], name, source["type"], route)
            self.coverage["site_files"].append({"path": path, "blob": blob, "sha256": sha})
            if key in PINS:
                self.extract(key, lines, end, data, path, route, blob, sha)
            if not legacy:
                units = list(passages(key, lines, end, data))
                for unit in units:
                    self.index.add(unit, name)
                self.expand(source, units, data)
        self.coverage["candidate_units"] = len(self.index.units)
        paths = {source["path"] for source in sources}
        self.coverage["document_metadata_count"] = sum(
            document["path"] in paths for document in inventory["documents"])

    def search(self, question, entity=None, limit=5):
        matches = []
        for unit in self.index.search(question, entity, limit):
            source = self.sources[unit.key]
            url = unit.url or f"{REPO}/blob/{COMMIT}/{source['path']}#L{unit.start}-L{unit.stop}"
            matches.append(dict(entity=unit.key, locator=unit.locator, url=url, heading=unit.heading,
                                excerpt=unit.text[:420], role="retrieval_candidate"))
        return matches

    def public_summary(self):
        return {"sources": len(self.coverage["site_files"]), "candidate_units": len(self.index.units),
                "facts_and_relations": sum(not isinstance(r, DocumentReference) for values in
                self.records.values() for r in values), "documents": self.coverage["document_metadata_count"]}

    def extract(self, key, lines, end, data, path, route, blob, sha):
        entity = self.entities[key]

        def add(attribute, value, text, locator, snippet, line=None, kind=Fact, **extra):
            url = f"{REPO}/blob/{COMMIT}/{path}"
            if line:
                url += f"#L{line}"
            evidence = EvidenceRef(path, locator, route, COMMIT, blob, sha, snippet, url)
            fact_id = f"{entity.id}:{attribute}:{locator}"
            self.records.setdefault((key, attribute), []).append(
                kind(fact_id, entity.id, attribute, value, text, evidence, **extra)
            )

        def paragraph(attribute, line):
            text = lines[line]
            add(attribute, text, text, f"body:L{line + 1}", text, line + 1)

        for i, doc in enumerate(data["documents"]):
            if "Руководство по эксплуатации Контроллер" in doc["title"] or (
                doc["title"].startswith("СЛДКС-1 Руководство по эксплуатации")
            ):
                if not doc["url"].startswith("/") or doc["url"].startswith("//"):
                    raise ValueError("Unexpected document URL")
                add("manual", doc, doc["title"] + " (ссылка из каталога)",
                    f"documents[{i}]", json.dumps(doc, ensure_ascii=False),
                    kind=DocumentReference, document_url=SITE + doc["url"])

        if key == "bkd":
            t = data["temperature_c"]
            fields = (
                ("temperature", "temperature_c", f"Температура эксплуатации: {t['min']}…+{t['max']} °C."),
                ("mass", "mass_kg", f"Масса: {data['mass_kg']} кг."),
                ("dimensions", "dimensions_mm", "Габариты: " + " × ".join(map(str, data["dimensions_mm"])) + " мм."),
                ("interfaces", "interfaces", "Интерфейсы по полю каталога: " + ", ".join(data["interfaces"]) + "."),
            )
            for attribute, field, text in fields:
                add(attribute, data[field], text, field,
                    next(line for line in lines[1:end] if line.startswith(field + ":")))
            names = {
                "ac": "Рабочий диапазон напряжения питания сети переменного тока",
                "dc": "Рабочий диапазон напряжения питания постоянного тока",
                "ethernet": "Интерфейс",
            }
            for attribute, name in names.items():
                i, spec = next((i, spec) for i, spec in enumerate(data["specs"]) if spec["name"] == name)
                add(attribute, spec, f"{name}: {spec['value']}.", f"specs[{i}]",
                    next(line for line in lines[1:end] if name + '"' in line and spec["value"] in line))
            add("feature", data["features"][0], data["features"][0], "features[0]",
                next(line for line in lines[1:end] if data["features"][0] in line))
            paragraph("purpose", next(i for i in range(end + 1, len(lines)) if "предназначен для" in lines[i]))
        else:
            paragraph("purpose", next(i for i in range(end + 1, len(lines)) if "предназначена для" in lines[i]))
            add("application", data["applications"], ", ".join(data["applications"]),
                "applications", next(line for line in lines[1:end] if line.startswith("applications:")))
            headings = [i for i, line in enumerate(lines) if re.match(r"## [123] поколение", line)]
            for i in headings:
                paragraph("generation", i)
            start = headings[-1]
            stop = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
            for i in range(start + 1, stop):
                if lines[i].startswith("-   "):
                    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", lines[i][4:]).rstrip(";.")
                    add("composition", value, "М2 с АРМ диспетчера: " + value,
                        f"body:L{i + 1}", lines[i], i + 1, kind=Relation)

    def expand(self, source, units, data):
        key = source["key"]
        entity_id = source["entity"]
        unit_map = {unit.locator: unit for unit in units}
        # Upgrade the original root assertions to exact source lines without changing their IDs.
        for (subject, _), records in self.records.items():
            if subject != key:
                continue
            for i, record in enumerate(records):
                if record.evidence.path != source["path"]:
                    continue
                field = record.evidence.locator
                unit = unit_map.get(field)
                if unit is None and isinstance(data.get(field), list):
                    unit = self.array_unit(field, unit_map, data)
                if unit is not None:
                    url = f"{REPO}/blob/{COMMIT}/{source['path']}#L{unit.start}-L{unit.stop}"
                    records[i] = replace(record, evidence=replace(record.evidence,
                                         snippet=unit.raw, url=url, parser="saturn-site-v2"))

        def add(attribute, value, text, unit, target=key, kind=Fact, **extra):
            bucket = self.records.setdefault((target, attribute), [])
            if any(record.value == value and
                   (kind is not Relation or record.configuration == extra["configuration"])
                   for record in bucket):
                return
            ev = EvidenceRef(source["path"], unit.locator, source["route"], COMMIT, source["blob"],
                             source["sha256"], unit.raw,
                             f"{REPO}/blob/{COMMIT}/{source['path']}#L{unit.start}-L{unit.stop}",
                             "saturn-site-v2")
            subject = PINS[target][0] if target in PINS else entity_id
            record_id = f"{subject}:{attribute}:{source['blob']}:{unit.locator}"
            bucket.append(kind(record_id, subject, attribute, value, text, ev, **extra))

        if source["type"] == "device":
            for field, attribute, label, suffix in (
                ("mass_kg","mass","Масса","кг"), ("lifetime_years","lifetime","Средний срок службы","лет"),
                ("ip","ip","Степень защиты",""), ("dimensions_mm","dimensions","Габариты","мм"),
                ("temperature_c","temperature","Температура эксплуатации","°C"),
                ("interfaces","interfaces","Интерфейсы каталога",""),
            ):
                if field not in data:
                    continue
                value = data[field]
                if isinstance(value, list):
                    printed = (" × " if attribute == "dimensions" else ", ").join(map(str,value))
                elif isinstance(value, dict):
                    printed = f"{value['min']}…{value['max']}"
                else:
                    printed = str(value)
                add(attribute, value, f"{label}: {printed} {suffix}".strip(), unit_map[field] if field in unit_map
                    else self.array_unit(field, unit_map, data))
            for i, spec in enumerate(data.get("specs", [])):
                name = spec.get("name","").lower()
                value = spec.get("value")
                if not isinstance(value,str):
                    continue
                attribute = next((a for prefix,a in (
                    ("относительная влажность","humidity"), ("время получения первого","cold_start"),
                    ("входное сопротивление","input_resistance"), ("радиоканал","radio"),
                    ("максимальная длина кабеля ипл","ipl_length"),
                ) if name.startswith(prefix)), None)
                if attribute:
                    text = " ".join(filter(None,[spec.get("group"), spec["name"], value]))
                    add(attribute, value, text, unit_map[f"specs[{i}]"])
                typed = typed_spec(name, value)
                if typed is not None:
                    attr, normalized = typed
                    add(attr, normalized, f"{spec['name']}: {value}", unit_map[f"specs[{i}]"])
            for i, feature in enumerate(data.get("features", [])):
                if isinstance(feature,str):
                    add("feature", feature, feature, unit_map[f"features[{i}]"])
        for i, doc in enumerate(data.get("documents", [])):
            url = doc.get("url","")
            if not url.startswith("/") or url.startswith("//"):
                continue
            # Generic document index and the targeted operating-manual answer have different intents.
            if any(r.value == doc for r in self.records.get((key,"manual"),[])):
                continue
            add("document_listing", doc, doc["title"], unit_map[f"documents[{i}]"],
                kind=DocumentReference, document_url=SITE+url)

        generation = {"gen1":"1 поколение, аналоговый звук","gen2":"2 поколение, серия М"}.get(source["variant"])
        for unit in units:
            if not unit.locator.startswith("body:") or not unit.text.startswith("- "):
                continue
            configuration = generation if unit.heading == "Состав системы" else None
            if key == "sld" and "вариант без компьютера" in unit.heading:
                configuration = "М2 без компьютера"
            if configuration:
                value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1",unit.text.lstrip("- ")).rstrip(";.")
                add("composition",value,f"{configuration}: {value}",unit,target="sld",
                    kind=Relation,configuration=configuration)

    @staticmethod
    def array_unit(field, unit_map, data):
        rows = [unit_map[f"{field}[{i}]"] for i in range(len(data[field]))]
        return replace(rows[0], locator=field, stop=rows[-1].stop,
                       raw="\n".join(dict.fromkeys(r.raw for r in rows)))

    def manifest(self):
        return {**self.coverage, "entities": [asdict(entity) for entity in self.entities.values()]}
