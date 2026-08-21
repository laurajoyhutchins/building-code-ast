"""Publication-neutral durable source-text intermediate representation.

The Source Text IR sits between source extraction/layout reconstruction and the
Document AST. It is intentionally source-expression preserving and therefore
private by default: public repositories may contain this contract and synthetic
fixtures, but not generated bundles containing protected source prose.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Protocol

from .document_model import DocumentAst, DocumentNode


SOURCE_TEXT_SCHEMA = "source-text/v1"
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceManifestLike(Protocol):
    artifact_id: str
    edition_id: str
    sha256: str
    size_bytes: int
    extractor_id: str
    extractor_version: str


class SourceMapEntryLike(Protocol):
    normalized_start: int
    normalized_end: int
    normalized_text: str

    def to_dict(self) -> dict[str, Any]: ...


class DocumentSeedLike(Protocol):
    source_manifest: SourceManifestLike
    source_map: tuple[SourceMapEntryLike, ...]
    document_ast: DocumentAst


@dataclass(frozen=True, slots=True)
class SourceTextIdentity:
    artifact_id: str
    edition_id: str
    source_sha256: str
    source_size_bytes: int
    extractor_id: str
    extractor_version: str
    projection_id: str
    projection_version: str

    def validate(self) -> None:
        for name, value in (
            ("artifact_id", self.artifact_id),
            ("edition_id", self.edition_id),
            ("extractor_id", self.extractor_id),
            ("extractor_version", self.extractor_version),
            ("projection_id", self.projection_id),
            ("projection_version", self.projection_version),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if _HEX_64_RE.fullmatch(self.source_sha256) is None:
            raise ValueError("source_sha256 must be 64 lowercase hexadecimal characters")
        if self.source_size_bytes <= 0:
            raise ValueError("source_size_bytes must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "edition_id": self.edition_id,
            "source_sha256": self.source_sha256,
            "source_size_bytes": self.source_size_bytes,
            "extractor_id": self.extractor_id,
            "extractor_version": self.extractor_version,
            "projection_id": self.projection_id,
            "projection_version": self.projection_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextIdentity":
        identity = cls(
            artifact_id=str(payload["artifact_id"]),
            edition_id=str(payload["edition_id"]),
            source_sha256=str(payload["source_sha256"]),
            source_size_bytes=int(payload["source_size_bytes"]),
            extractor_id=str(payload["extractor_id"]),
            extractor_version=str(payload["extractor_version"]),
            projection_id=str(payload["projection_id"]),
            projection_version=str(payload["projection_version"]),
        )
        identity.validate()
        return identity


@dataclass(frozen=True, slots=True)
class SourceTextFragment:
    start: int
    end: int
    text: str
    provenance: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "span": {"start": self.start, "end": self.end},
            "text": self.text,
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextFragment":
        span = payload["span"]
        if not isinstance(span, Mapping):
            raise ValueError("fragment span must be an object")
        provenance = payload.get("provenance", {})
        if not isinstance(provenance, Mapping):
            raise ValueError("fragment provenance must be an object")
        return cls(
            start=int(span["start"]),
            end=int(span["end"]),
            text=str(payload["text"]),
            provenance=dict(provenance),
        )


@dataclass(frozen=True, slots=True)
class SourceTextIndexEntry:
    locator: str
    document_node_id: str
    start: int
    end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator": self.locator,
            "document_node_id": self.document_node_id,
            "span": {"start": self.start, "end": self.end},
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextIndexEntry":
        span = payload["span"]
        if not isinstance(span, Mapping):
            raise ValueError("index span must be an object")
        return cls(
            locator=str(payload["locator"]),
            document_node_id=str(payload["document_node_id"]),
            start=int(span["start"]),
            end=int(span["end"]),
        )


@dataclass(frozen=True, slots=True)
class SourceTextSelection:
    locator: str
    document_node_id: str
    text: str
    start: int
    end: int
    fragments: tuple[SourceTextFragment, ...]


@dataclass(frozen=True, slots=True)
class SourceTextBundle:
    identity: SourceTextIdentity
    canonical_text: str
    fragments: tuple[SourceTextFragment, ...]
    index: tuple[SourceTextIndexEntry, ...]
    diagnostics: tuple[Mapping[str, Any], ...]
    text_sha256: str
    bundle_sha256: str
    schema: str = SOURCE_TEXT_SCHEMA

    def _payload_without_bundle_hash(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "identity": self.identity.to_dict(),
            "canonical_text": self.canonical_text,
            "fragments": [fragment.to_dict() for fragment in self.fragments],
            "index": [entry.to_dict() for entry in self.index],
            "diagnostics": [dict(item) for item in self.diagnostics],
            "text_sha256": self.text_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload_without_bundle_hash()
        payload["bundle_sha256"] = self.bundle_sha256
        return payload

    def validate(self) -> None:
        if self.schema != SOURCE_TEXT_SCHEMA:
            raise ValueError(f"unsupported source text schema: {self.schema}")
        self.identity.validate()
        actual_text_hash = _sha256_text(self.canonical_text)
        if self.text_sha256 != actual_text_hash:
            raise ValueError("canonical text hash mismatch")
        if _HEX_64_RE.fullmatch(self.bundle_sha256) is None:
            raise ValueError("bundle_sha256 must be a lowercase SHA-256 digest")

        previous_end = 0
        for position, fragment in enumerate(self.fragments):
            if fragment.start < 0 or fragment.end <= fragment.start:
                raise ValueError(f"fragment {position} has an invalid span")
            if fragment.end > len(self.canonical_text):
                raise ValueError(f"fragment {position} extends beyond canonical text")
            if fragment.start < previous_end:
                raise ValueError("fragments must be ordered and non-overlapping")
            if self.canonical_text[fragment.start:fragment.end] != fragment.text:
                raise ValueError(f"fragment {position} text does not round-trip")
            previous_end = fragment.end

        locators: set[str] = set()
        node_ids: set[str] = set()
        for entry in self.index:
            if not entry.locator.strip() or not entry.document_node_id.strip():
                raise ValueError("index locator and document_node_id must not be empty")
            if entry.locator in locators:
                raise ValueError(f"duplicate source text locator: {entry.locator}")
            if entry.document_node_id in node_ids:
                raise ValueError(f"duplicate source text document node: {entry.document_node_id}")
            if entry.start < 0 or entry.end < entry.start or entry.end > len(self.canonical_text):
                raise ValueError(f"invalid index span for {entry.locator}")
            locators.add(entry.locator)
            node_ids.add(entry.document_node_id)

        expected_bundle_hash = _sha256_json(self._payload_without_bundle_hash())
        if self.bundle_sha256 != expected_bundle_hash:
            raise ValueError("bundle hash mismatch")

    def get(self, locator: str) -> SourceTextSelection:
        normalized = locator.strip()
        for entry in self.index:
            if entry.locator != normalized:
                continue
            fragments = tuple(
                fragment
                for fragment in self.fragments
                if fragment.start < entry.end and fragment.end > entry.start
            )
            return SourceTextSelection(
                locator=entry.locator,
                document_node_id=entry.document_node_id,
                text=self.canonical_text[entry.start:entry.end],
                start=entry.start,
                end=entry.end,
                fragments=fragments,
            )
        raise KeyError(f"source text locator not found: {normalized}")

    def save(self, path: str | Path) -> None:
        self.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_canonical_json(self.to_dict()) + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextBundle":
        if payload.get("schema") != SOURCE_TEXT_SCHEMA:
            raise ValueError("source text bundle schema mismatch")
        raw_fragments = payload.get("fragments")
        raw_index = payload.get("index")
        raw_diagnostics = payload.get("diagnostics", [])
        if not isinstance(raw_fragments, list) or not isinstance(raw_index, list):
            raise ValueError("source text fragments and index must be arrays")
        if not isinstance(raw_diagnostics, list):
            raise ValueError("source text diagnostics must be an array")
        diagnostics: list[Mapping[str, Any]] = []
        for item in raw_diagnostics:
            if not isinstance(item, Mapping):
                raise ValueError("source text diagnostic must be an object")
            diagnostics.append(dict(item))
        bundle = cls(
            identity=SourceTextIdentity.from_dict(_mapping(payload["identity"], "identity")),
            canonical_text=str(payload["canonical_text"]),
            fragments=tuple(SourceTextFragment.from_dict(_mapping(item, "fragment")) for item in raw_fragments),
            index=tuple(SourceTextIndexEntry.from_dict(_mapping(item, "index entry")) for item in raw_index),
            diagnostics=tuple(diagnostics),
            text_sha256=str(payload["text_sha256"]),
            bundle_sha256=str(payload["bundle_sha256"]),
        )
        bundle.validate()
        return bundle

    @classmethod
    def load(cls, path: str | Path) -> "SourceTextBundle":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("source text bundle must be a JSON object")
        return cls.from_dict(payload)


def build_source_text_bundle(
    *,
    identity: SourceTextIdentity,
    canonical_text: str,
    fragments: Iterable[SourceTextFragment],
    index: Iterable[SourceTextIndexEntry],
    diagnostics: Iterable[Mapping[str, Any]] = (),
) -> SourceTextBundle:
    identity.validate()
    fragment_tuple = tuple(fragments)
    index_tuple = tuple(index)
    diagnostic_tuple = tuple(dict(item) for item in diagnostics)
    text_sha256 = _sha256_text(canonical_text)
    provisional = SourceTextBundle(
        identity=identity,
        canonical_text=canonical_text,
        fragments=fragment_tuple,
        index=index_tuple,
        diagnostics=diagnostic_tuple,
        text_sha256=text_sha256,
        bundle_sha256="0" * 64,
    )
    bundle = SourceTextBundle(
        identity=identity,
        canonical_text=canonical_text,
        fragments=fragment_tuple,
        index=index_tuple,
        diagnostics=diagnostic_tuple,
        text_sha256=text_sha256,
        bundle_sha256=_sha256_json(provisional._payload_without_bundle_hash()),
    )
    bundle.validate()
    return bundle


def bundle_from_document_seed(
    seed: DocumentSeedLike,
    *,
    projection_id: str = "building-code-ast:document-seed-source-text",
    projection_version: str = "1",
) -> SourceTextBundle:
    """Project an existing NEC/IBC-style seed into the generic Source Text IR.

    This adapter deliberately consumes the already-normalized source text and
    source-map records. It does not open a PDF or rerun layout reconstruction.
    """

    manifest = seed.source_manifest
    ast = seed.document_ast
    identity = SourceTextIdentity(
        artifact_id=manifest.artifact_id,
        edition_id=manifest.edition_id,
        source_sha256=manifest.sha256,
        source_size_bytes=manifest.size_bytes,
        extractor_id=manifest.extractor_id,
        extractor_version=manifest.extractor_version,
        projection_id=projection_id,
        projection_version=projection_version,
    )
    fragments = tuple(
        SourceTextFragment(
            start=entry.normalized_start,
            end=entry.normalized_end,
            text=entry.normalized_text,
            provenance=_provenance_from_source_map_entry(entry),
        )
        for entry in seed.source_map
    )
    index = tuple(_document_index(ast.root))
    diagnostics = tuple(diagnostic.to_dict() for diagnostic in ast.diagnostics)
    return build_source_text_bundle(
        identity=identity,
        canonical_text=ast.source_text,
        fragments=fragments,
        index=index,
        diagnostics=diagnostics,
    )


def _document_index(node: DocumentNode) -> Iterable[SourceTextIndexEntry]:
    yield SourceTextIndexEntry(
        locator=node.locator,
        document_node_id=node.node_id,
        start=node.span.start,
        end=node.span.end,
    )
    for child in node.children:
        yield from _document_index(child)


def _provenance_from_source_map_entry(entry: SourceMapEntryLike) -> Mapping[str, Any]:
    payload = dict(entry.to_dict())
    payload.pop("normalized_span", None)
    return payload


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"source text {label} must be an object")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
