"""Server identities for the isolated candidate-answer/2 protocol."""
from dataclasses import dataclass
import hashlib
import re
from types import MappingProxyType

from .corpus import encoded

VERSION = "candidate-answer/2"
COVER_REQUIRED = "exact_model_and_edition_cover_required"


def applicability_proved(source, entity, applies):
    if not source.applicability:
        return False
    if applies is not None:
        return bool(applies(source, entity))
    return source.applicability != COVER_REQUIRED


@dataclass(frozen=True)
class Entity:
    canonical_id: str
    label: str
    generation: str


@dataclass(frozen=True)
class Source:
    canonical_entity: str
    generation: str
    kind: str
    sha256: str
    doc_id: str
    revision: str | None
    pages: int
    url: str
    applicability: str | None = None
    commit: str | None = None
    blob: str | None = None


class SourceRegistry:
    def __init__(self, request_id, manifest_sha256, entities, sources, parts):
        from dataclasses import asdict

        if not request_id or not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256):
            raise ValueError("invalid_request_identity")
        if not parts or any(not k or not v for k, v in parts.items()):
            raise ValueError("invalid_parts")
        if len(set(entities)) != len(entities) or len(set(sources)) != len(sources):
            raise ValueError("ambiguous_registry")
        for source in sources:
            if (source.kind not in {"pdf", "site"} or not source.doc_id or not source.url
                    or not re.fullmatch(r"[0-9a-f]{64}", source.sha256)
                    or source.kind == "pdf" and not 1 <= source.pages <= 500
                    or source.kind == "site" and not all(re.fullmatch(r"[0-9a-f]{40}", key or "")
                                                         for key in (source.commit, source.blob))):
                raise ValueError("invalid_source_identity")
        identity = [VERSION, request_id, manifest_sha256, parts, list(map(asdict, entities)), list(map(asdict, sources))]
        self.wire_identity = hashlib.sha256(encoded(identity).encode()).hexdigest()
        self.request_id = request_id
        self.manifest_sha256 = manifest_sha256
        suffix = self.wire_identity[:16]
        self.entities = MappingProxyType({f"E{i}-{suffix}": entity for i, entity in enumerate(entities, 1)})
        self.sources = MappingProxyType({f"S{i}-{suffix}": source for i, source in enumerate(sources, 1)})
        self.parts = MappingProxyType(dict(parts))

    def v1_source(self, loc, label):
        matches = [(key, s) for key, s in self.sources.items() if s.kind == "pdf"
                   and (s.doc_id, s.sha256, s.revision) == (loc["doc_id"], loc["sha256"], loc["revision"])]
        if len(matches) != 1:
            return None
        key, source = matches[0]
        entities = [(ref, entity) for ref, entity in self.entities.items()
                    if label in (entity.label, entity.canonical_id)]
        if len(entities) != 1:
            return None
        entity_id, entity = entities[0]
        if (source.canonical_entity, source.generation) != (entity.canonical_id, entity.generation):
            return None
        return key, entity_id
