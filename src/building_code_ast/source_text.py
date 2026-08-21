"""Durable publication-neutral canonical source-text intermediate representation.

``source-text/v1`` sits between source extraction/layout reconstruction and the
publication-structure AST.  It preserves exact canonical text and source
provenance, but deliberately carries no provision semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

from .document_model import DocumentAst, DocumentNode, DocumentSourceArtifact


SOURCE_TEXT_VERSION = "source-text/v1"
SOURCE_TEXT_TYPE = "source_text_bundle"
SOURCE_TEXT_ENCODING = "utf-8"
SOURCE_TEXT_COORDINATE_UNIT = "unicode_codepoint"
_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode(SOURCE_TEXT_ENCODING))


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _canonical_json_bytes(value: Any) -> bytes:
    return _canonical_json(value).encode(SOURCE_TEXT_ENCODING)


def _jsonl_bytes(values: Iterable[Mapping[str, Any]]) -> bytes:
    material = list(values)
    if not material:
        return b""
    return ("\n".join(_canonical_json(value) for value in material) + "\n").encode(
        SOURCE_TEXT_ENCODING
    )


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    try:
        value.encode(SOURCE_TEXT_ENCODING, errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{field_name} is not valid UTF-8 text") from error


def _require_sha256(value: str, field_name: str) -> None:
    if _HEX_64_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be 64 lowercase hexadecimal characters")


@dataclass(frozen=True, slots=True)
class SourceTextProvenance:
    """One source observation backing a canonical text fragment."""

    page_number: int
    bbox: tuple[float, float, float, float] | None = None
    observation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"page_number": self.page_number}
        if self.bbox is not None:
            payload["bbox"] = [round(value, 3) for value in self.bbox]
        if self.observation_id is not None:
            payload["observation_id"] = self.observation_id
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextProvenance":
        bbox_value = payload.get("bbox")
        bbox = None if bbox_value is None else tuple(float(item) for item in bbox_value)
        if bbox is not None and len(bbox) != 4:
            raise ValueError("provenance bbox must contain four coordinates")
        observation_id = payload.get("observation_id")
        return cls(
            page_number=int(payload["page_number"]),
            bbox=bbox,  # type: ignore[arg-type]
            observation_id=None if observation_id is None else str(observation_id),
        )


@dataclass(frozen=True, slots=True)
class SourceTextFragment:
    """One ordered canonical range and its exact source observations."""

    start: int
    end: int
    text_sha256: str
    provenance: tuple[SourceTextProvenance, ...]
    fragment_id: str = ""

    def __post_init__(self) -> None:
        if not self.fragment_id:
            object.__setattr__(self, "fragment_id", _expected_fragment_id(self))

    def to_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "start": self.start,
            "end": self.end,
            "text_sha256": self.text_sha256,
            "provenance": [item.to_dict() for item in self.provenance],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextFragment":
        return cls(
            fragment_id=str(payload.get("fragment_id") or ""),
            start=int(payload["start"]),
            end=int(payload["end"]),
            text_sha256=str(payload["text_sha256"]),
            provenance=tuple(
                SourceTextProvenance.from_dict(item)
                for item in payload.get("provenance", ())
            ),
        )


def _expected_fragment_id(fragment: SourceTextFragment) -> str:
    payload = {
        "start": fragment.start,
        "end": fragment.end,
        "text_sha256": fragment.text_sha256,
        "provenance": [item.to_dict() for item in fragment.provenance],
    }
    return "sourcefrag:" + _sha256_bytes(_canonical_json_bytes(payload))


@dataclass(frozen=True, slots=True)
class SourceTextSection:
    """Deterministic structural lookup range projected from a Document AST."""

    locator: str
    node_id: str
    parent_locator: str | None
    start: int
    end: int
    text_sha256: str
    first_page: int
    last_page: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator": self.locator,
            "node_id": self.node_id,
            "parent_locator": self.parent_locator,
            "start": self.start,
            "end": self.end,
            "text_sha256": self.text_sha256,
            "first_page": self.first_page,
            "last_page": self.last_page,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextSection":
        parent = payload.get("parent_locator")
        return cls(
            locator=str(payload["locator"]),
            node_id=str(payload["node_id"]),
            parent_locator=None if parent is None else str(parent),
            start=int(payload["start"]),
            end=int(payload["end"]),
            text_sha256=str(payload["text_sha256"]),
            first_page=int(payload["first_page"]),
            last_page=int(payload["last_page"]),
        )


@dataclass(frozen=True, slots=True)
class SourceTextDiagnostic:
    code: str
    severity: str
    message: str
    start: int | None = None
    end: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.start is not None or self.end is not None:
            payload["span"] = {"start": self.start, "end": self.end}
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceTextDiagnostic":
        span = payload.get("span") or {}
        return cls(
            code=str(payload["code"]),
            severity=str(payload["severity"]),
            message=str(payload["message"]),
            start=None if span.get("start") is None else int(span["start"]),
            end=None if span.get("end") is None else int(span["end"]),
        )


@dataclass(frozen=True, slots=True)
class SourceTextBundle:
    source_artifact: DocumentSourceArtifact
    source_sha256: str
    source_size: int
    extractor_id: str
    extractor_version: str
    projection_id: str
    projection_version: str
    canonical_text: str
    fragments: tuple[SourceTextFragment, ...]
    sections: tuple[SourceTextSection, ...] = ()
    diagnostics: tuple[SourceTextDiagnostic, ...] = ()
    text_sha256: str = ""
    bundle_sha256: str = ""
    version: str = field(default=SOURCE_TEXT_VERSION, init=False)

    def manifest_dict(self, *, include_bundle_sha256: bool = True) -> dict[str, Any]:
        component_bytes = _component_bytes(self)
        payload: dict[str, Any] = {
            "type": SOURCE_TEXT_TYPE,
            "version": self.version,
            "encoding": SOURCE_TEXT_ENCODING,
            "coordinate_unit": SOURCE_TEXT_COORDINATE_UNIT,
            "source_artifact": self.source_artifact.to_dict(),
            "source_sha256": self.source_sha256,
            "source_size": self.source_size,
            "extractor": {"id": self.extractor_id, "version": self.extractor_version},
            "projection": {"id": self.projection_id, "version": self.projection_version},
            "text_sha256": self.text_sha256,
            "components": {
                name: {"sha256": _sha256_bytes(content), "size": len(content)}
                for name, content in component_bytes.items()
            },
        }
        if include_bundle_sha256:
            payload["bundle_sha256"] = self.bundle_sha256
        return payload


@dataclass(frozen=True, slots=True)
class SourceTextLookup:
    section: SourceTextSection
    text: str
    provenance: tuple[SourceTextProvenance, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section.to_dict(),
            "text": self.text,
            "provenance": [item.to_dict() for item in self.provenance],
        }


def _component_bytes(bundle: SourceTextBundle) -> dict[str, bytes]:
    return {
        "document.txt": bundle.canonical_text.encode(SOURCE_TEXT_ENCODING),
        "fragments.jsonl": _jsonl_bytes(item.to_dict() for item in bundle.fragments),
        "sections.jsonl": _jsonl_bytes(item.to_dict() for item in bundle.sections),
        "diagnostics.jsonl": _jsonl_bytes(item.to_dict() for item in bundle.diagnostics),
    }


def _bundle_digest(bundle: SourceTextBundle) -> str:
    return _sha256_bytes(_canonical_json_bytes(bundle.manifest_dict(include_bundle_sha256=False)))


def _validate_provenance(item: SourceTextProvenance) -> None:
    if item.page_number < 1:
        raise ValueError("source-text provenance page_number must be positive")
    if item.observation_id is not None:
        _require_text(item.observation_id, "source-text provenance observation_id")
    if item.bbox is None:
        return
    if len(item.bbox) != 4 or not all(math.isfinite(value) for value in item.bbox):
        raise ValueError("source-text provenance bbox must contain four finite coordinates")
    x0, y0, x1, y1 = item.bbox
    if x1 < x0 or y1 < y0:
        raise ValueError("source-text provenance bbox is inverted")


def _overlapping_fragments(
    fragments: Sequence[SourceTextFragment],
    start: int,
    end: int,
) -> tuple[SourceTextFragment, ...]:
    return tuple(item for item in fragments if item.start < end and item.end > start)


def validate_source_text_bundle(bundle: SourceTextBundle) -> None:
    if bundle.version != SOURCE_TEXT_VERSION:
        raise ValueError(f"unsupported source-text version {bundle.version!r}")
    _require_text(bundle.source_artifact.artifact_id, "source artifact_id")
    _require_text(bundle.source_artifact.edition_id, "source edition_id")
    _require_sha256(bundle.source_sha256, "source_sha256")
    if bundle.source_size <= 0:
        raise ValueError("source_size must be positive")
    _require_text(bundle.extractor_id, "extractor_id")
    _require_text(bundle.extractor_version, "extractor_version")
    _require_text(bundle.projection_id, "projection_id")
    _require_text(bundle.projection_version, "projection_version")
    try:
        bundle.canonical_text.encode(SOURCE_TEXT_ENCODING, errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError("canonical_text is not valid UTF-8 text") from error

    _require_sha256(bundle.text_sha256, "text_sha256")
    if bundle.text_sha256 != _sha256_text(bundle.canonical_text):
        raise ValueError("source-text canonical text hash mismatch")

    previous_end = -1
    previous_key: tuple[int, int, str] | None = None
    fragment_ids: set[str] = set()
    for fragment in bundle.fragments:
        if fragment.start < 0 or fragment.end <= fragment.start or fragment.end > len(bundle.canonical_text):
            raise ValueError("source-text fragment span is outside canonical text")
        key = (fragment.start, fragment.end, fragment.fragment_id)
        if previous_key is not None and key <= previous_key:
            raise ValueError("source-text fragments must be in deterministic source order")
        if fragment.start < previous_end:
            raise ValueError("source-text fragments must not overlap")
        previous_key = key
        previous_end = fragment.end
        if fragment.fragment_id in fragment_ids:
            raise ValueError("source-text fragment IDs must be unique")
        fragment_ids.add(fragment.fragment_id)
        _require_text(fragment.fragment_id, "source-text fragment_id")
        if fragment.fragment_id != _expected_fragment_id(fragment):
            raise ValueError("source-text fragment ID does not match its deterministic payload")
        _require_sha256(fragment.text_sha256, "source-text fragment text_sha256")
        if fragment.text_sha256 != _sha256_text(bundle.canonical_text[fragment.start : fragment.end]):
            raise ValueError("source-text fragment text hash mismatch")
        if not fragment.provenance:
            raise ValueError("source-text fragments must retain source provenance")
        for provenance in fragment.provenance:
            _validate_provenance(provenance)

    locators: set[str] = set()
    node_ids: set[str] = set()
    section_by_locator = {item.locator: item for item in bundle.sections}
    if len(section_by_locator) != len(bundle.sections):
        raise ValueError("source-text section locators must be unique")
    for section in bundle.sections:
        _require_text(section.locator, "source-text section locator")
        _require_text(section.node_id, "source-text section node_id")
        if section.locator in locators or section.node_id in node_ids:
            raise ValueError("source-text section identities must be unique")
        locators.add(section.locator)
        node_ids.add(section.node_id)
        if section.start < 0 or section.end <= section.start or section.end > len(bundle.canonical_text):
            raise ValueError("source-text section span is outside canonical text")
        _require_sha256(section.text_sha256, "source-text section text_sha256")
        if section.text_sha256 != _sha256_text(bundle.canonical_text[section.start : section.end]):
            raise ValueError("source-text section text hash mismatch")
        if section.parent_locator is not None and section.parent_locator not in section_by_locator:
            raise ValueError("source-text section parent locator is not indexed")
        overlapping = _overlapping_fragments(bundle.fragments, section.start, section.end)
        if not overlapping:
            raise ValueError("source-text section has no provenance-bearing fragment")
        pages = sorted(
            {
                provenance.page_number
                for fragment in overlapping
                for provenance in fragment.provenance
            }
        )
        if section.first_page != pages[0] or section.last_page != pages[-1]:
            raise ValueError("source-text section page summary does not match fragment provenance")

    for diagnostic in bundle.diagnostics:
        _require_text(diagnostic.code, "source-text diagnostic code")
        if diagnostic.severity not in {"info", "warning", "error"}:
            raise ValueError("source-text diagnostic severity must be info, warning, or error")
        _require_text(diagnostic.message, "source-text diagnostic message")
        if (diagnostic.start is None) != (diagnostic.end is None):
            raise ValueError("source-text diagnostic span must contain both start and end")
        if diagnostic.start is not None and diagnostic.end is not None:
            if diagnostic.start < 0 or diagnostic.end <= diagnostic.start or diagnostic.end > len(bundle.canonical_text):
                raise ValueError("source-text diagnostic span is outside canonical text")

    _require_sha256(bundle.bundle_sha256, "bundle_sha256")
    if bundle.bundle_sha256 != _bundle_digest(bundle):
        raise ValueError("source-text bundle hash mismatch")


def _pages_for_span(
    fragments: Sequence[SourceTextFragment],
    start: int,
    end: int,
) -> tuple[int, int]:
    pages = sorted(
        {
            provenance.page_number
            for fragment in _overlapping_fragments(fragments, start, end)
            for provenance in fragment.provenance
        }
    )
    if not pages:
        raise ValueError("document node span has no source-text fragment provenance")
    return pages[0], pages[-1]


def build_section_index(
    document_ast: DocumentAst,
    *,
    canonical_text: str,
    fragments: Sequence[SourceTextFragment],
) -> tuple[SourceTextSection, ...]:
    """Project every structural locator into the canonical source-text coordinate space."""

    if document_ast.source_text != canonical_text:
        raise ValueError("Document AST source text does not match canonical source text")

    sections: list[SourceTextSection] = []

    def visit(node: DocumentNode, parent_locator: str | None) -> None:
        if node.span.start < 0 or node.span.end > len(canonical_text):
            raise ValueError("Document AST node span is outside canonical source text")
        if canonical_text[node.span.start : node.span.end] != node.span.text:
            raise ValueError("Document AST node span does not round-trip to canonical source text")
        first_page, last_page = _pages_for_span(fragments, node.span.start, node.span.end)
        sections.append(
            SourceTextSection(
                locator=node.locator,
                node_id=node.node_id,
                parent_locator=parent_locator,
                start=node.span.start,
                end=node.span.end,
                text_sha256=_sha256_text(node.span.text),
                first_page=first_page,
                last_page=last_page,
            )
        )
        for child in node.children:
            visit(child, node.locator)

    visit(document_ast.root, None)
    return tuple(sections)


def make_source_text_bundle(
    *,
    source_artifact: DocumentSourceArtifact,
    source_sha256: str,
    source_size: int,
    extractor_id: str,
    extractor_version: str,
    projection_id: str,
    projection_version: str,
    canonical_text: str,
    fragments: Sequence[SourceTextFragment],
    document_ast: DocumentAst | None = None,
    diagnostics: Sequence[SourceTextDiagnostic] = (),
) -> SourceTextBundle:
    """Construct a validated deterministic source-text bundle."""

    if document_ast is not None and document_ast.source_artifact != source_artifact:
        raise ValueError("Document AST source artifact does not match source-text artifact")
    ordered_fragments = tuple(fragments)
    sections = (
        ()
        if document_ast is None
        else build_section_index(
            document_ast,
            canonical_text=canonical_text,
            fragments=ordered_fragments,
        )
    )
    partial = SourceTextBundle(
        source_artifact=source_artifact,
        source_sha256=source_sha256,
        source_size=source_size,
        extractor_id=extractor_id,
        extractor_version=extractor_version,
        projection_id=projection_id,
        projection_version=projection_version,
        canonical_text=canonical_text,
        fragments=ordered_fragments,
        sections=sections,
        diagnostics=tuple(diagnostics),
        text_sha256=_sha256_text(canonical_text),
        bundle_sha256="0" * 64,
    )
    bundle = replace(partial, bundle_sha256=_bundle_digest(partial))
    validate_source_text_bundle(bundle)
    return bundle


def _parse_artifact(payload: Mapping[str, Any]) -> DocumentSourceArtifact:
    return DocumentSourceArtifact(
        artifact_id=str(payload["artifact_id"]),
        edition_id=str(payload["edition_id"]),
        publication_component_id=(
            None
            if payload.get("publication_component_id") is None
            else str(payload["publication_component_id"])
        ),
        publication_state_id=(
            None
            if payload.get("publication_state_id") is None
            else str(payload["publication_state_id"])
        ),
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"source-text component is missing: {path.name}")
    output: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding=SOURCE_TEXT_ENCODING).splitlines(), start=1):
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON in {path.name}:{line_number}") from error
        if not isinstance(payload, dict):
            raise ValueError(f"{path.name}:{line_number} must contain one JSON object")
        output.append(payload)
    return output


def write_source_text_bundle(directory: str | Path, bundle: SourceTextBundle) -> Path:
    """Persist one immutable private source-text bundle."""

    validate_source_text_bundle(bundle)
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=False)
    components = _component_bytes(bundle)
    for name, content in components.items():
        (target / name).write_bytes(content)
    manifest_bytes = _canonical_json_bytes(bundle.manifest_dict()) + b"\n"
    (target / "manifest.json").write_bytes(manifest_bytes)
    return target


def load_source_text_bundle(
    directory: str | Path,
    *,
    expected_source_sha256: str | None = None,
    expected_source_size: int | None = None,
    expected_artifact_id: str | None = None,
    expected_edition_id: str | None = None,
) -> SourceTextBundle:
    """Load and strictly validate a persisted source-text bundle without PDF access."""

    target = Path(directory)
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("source-text manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding=SOURCE_TEXT_ENCODING))
    except json.JSONDecodeError as error:
        raise ValueError("source-text manifest is invalid JSON") from error
    if not isinstance(manifest, dict):
        raise ValueError("source-text manifest must be a JSON object")
    if manifest.get("type") != SOURCE_TEXT_TYPE or manifest.get("version") != SOURCE_TEXT_VERSION:
        raise ValueError("source-text manifest type/version mismatch")
    if manifest.get("encoding") != SOURCE_TEXT_ENCODING or manifest.get("coordinate_unit") != SOURCE_TEXT_COORDINATE_UNIT:
        raise ValueError("source-text coordinate-space contract mismatch")

    components = manifest.get("components")
    if not isinstance(components, dict):
        raise ValueError("source-text manifest components are missing")
    component_bytes: dict[str, bytes] = {}
    for name in ("document.txt", "fragments.jsonl", "sections.jsonl", "diagnostics.jsonl"):
        path = target / name
        if not path.exists():
            raise ValueError(f"source-text component is missing: {name}")
        content = path.read_bytes()
        component_bytes[name] = content
        expected = components.get(name)
        if not isinstance(expected, dict):
            raise ValueError(f"source-text component receipt is missing: {name}")
        if int(expected.get("size", -1)) != len(content) or str(expected.get("sha256")) != _sha256_bytes(content):
            raise ValueError(f"source-text component hash/size mismatch: {name}")

    try:
        canonical_text = component_bytes["document.txt"].decode(SOURCE_TEXT_ENCODING, errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("source-text document.txt is not valid UTF-8") from error
    extractor = manifest.get("extractor") or {}
    projection = manifest.get("projection") or {}
    bundle = SourceTextBundle(
        source_artifact=_parse_artifact(manifest["source_artifact"]),
        source_sha256=str(manifest["source_sha256"]),
        source_size=int(manifest["source_size"]),
        extractor_id=str(extractor["id"]),
        extractor_version=str(extractor["version"]),
        projection_id=str(projection["id"]),
        projection_version=str(projection["version"]),
        canonical_text=canonical_text,
        fragments=tuple(
            SourceTextFragment.from_dict(item)
            for item in _read_jsonl(target / "fragments.jsonl")
        ),
        sections=tuple(
            SourceTextSection.from_dict(item)
            for item in _read_jsonl(target / "sections.jsonl")
        ),
        diagnostics=tuple(
            SourceTextDiagnostic.from_dict(item)
            for item in _read_jsonl(target / "diagnostics.jsonl")
        ),
        text_sha256=str(manifest["text_sha256"]),
        bundle_sha256=str(manifest["bundle_sha256"]),
    )
    validate_source_text_bundle(bundle)

    if expected_source_sha256 is not None and bundle.source_sha256 != expected_source_sha256:
        raise ValueError("source-text source SHA-256 does not match expected source identity")
    if expected_source_size is not None and bundle.source_size != expected_source_size:
        raise ValueError("source-text source size does not match expected source identity")
    if expected_artifact_id is not None and bundle.source_artifact.artifact_id != expected_artifact_id:
        raise ValueError("source-text artifact_id does not match expected source identity")
    if expected_edition_id is not None and bundle.source_artifact.edition_id != expected_edition_id:
        raise ValueError("source-text edition_id does not match expected source identity")
    return bundle


def lookup_source_text(bundle: SourceTextBundle, locator: str) -> SourceTextLookup:
    """Return exact text and provenance for one indexed structural locator."""

    validate_source_text_bundle(bundle)
    section = next((item for item in bundle.sections if item.locator == locator), None)
    if section is None:
        raise KeyError(locator)
    provenance: list[SourceTextProvenance] = []
    seen: set[str] = set()
    for fragment in _overlapping_fragments(bundle.fragments, section.start, section.end):
        for item in fragment.provenance:
            key = _canonical_json(item.to_dict())
            if key in seen:
                continue
            seen.add(key)
            provenance.append(item)
    return SourceTextLookup(
        section=section,
        text=bundle.canonical_text[section.start : section.end],
        provenance=tuple(provenance),
    )
