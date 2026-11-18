"""Offline extraction from exactly two immutable Git blobs."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

COMMIT = "084d759487bfab6e111549c9b5469711ac5fc13e"
BUNDLE = "saturn-two-entity-site-084d7594-v1"
REPO = "https://github.com/UkWood/Saturn-Main-Site"
SITE = "https://www.mnppsaturn.ru"
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
    return {
        key: subprocess.check_output(
            ["git", "-C", str(checkout), "show", f"{COMMIT}:{pin[2]}"]
        )
        for key, pin in PINS.items()
    }


class Catalog:
    def __init__(self, files: dict[str, bytes]):
        self.entities = {}
        self.records = {}
        self.coverage = {"bundle": BUNDLE, "commit": COMMIT, "site_files": [],
                         "excluded_channels": ["PDF: только метаданные ссылок"]}
        if files.keys() != PINS.keys():
            raise ValueError("Incomplete source bundle")
        for key, (entity_id, name, path, blob) in PINS.items():
            raw = files[key]
            header = f"blob {len(raw)}\0".encode()
            if hashlib.sha1(header + raw).hexdigest() != blob:
                raise ValueError(f"Invalid pinned blob: {path}")
            sha = hashlib.sha256(raw).hexdigest()
            lines = raw.decode("utf-8").splitlines()
            end = lines.index("---", 1)
            data = yaml.safe_load("\n".join(lines[1:end]))
            if name not in data["title"]:
                raise ValueError("Entity title mismatch")
            route = "/" + path.removeprefix("src/content/").removesuffix(".md") + "/"
            self.entities[key] = Entity(entity_id, name, entity_id.split(":")[1], route)
            self.coverage["site_files"].append({"path": path, "blob": blob, "sha256": sha})
            self.extract(key, lines, end, data, path, route, blob, sha)

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

    def manifest(self):
        return {**self.coverage, "entities": [asdict(entity) for entity in self.entities.values()]}
