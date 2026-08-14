"""Closed contracts for source-preserving PDF enrichment derivatives."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import re
from typing import Any, Mapping


PDF_ENRICHMENT_PLAN_VERSION = "1"
PDF_ENRICHMENT_RECEIPT_VERSION = "1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_METADATA_FIELDS = frozenset({"title", "author", "subject", "keywords", "creator"})
_PAGE_LABEL_STYLES = frozenset({"decimal", "roman_lower", "roman_upper", "alpha_lower", "alpha_upper"})


class EvidenceOrigin(StrEnum):
    NATIVE_PDF = "native_pdf"
    SOURCE_REGISTER = "source_register"
    DOCUMENT_AST = "document_ast"
    REVIEWED_SOURCE_OBSERVATION = "reviewed_source_observation"
    OWNER_SUPPLIED = "owner_supplied"


class TextOrigin(StrEnum):
    OCR = "ocr"
    RASTER_RECOVERY = "raster_recovery"
    DERIVED_TEXT = "derived_text"


class OperationKind(StrEnum):
    SEARCHABLE_TEXT = "searchable_text"
    OUTLINE = "outline"
    PAGE_LABELS = "page_labels"
    DESCRIPTIVE_METADATA = "descriptive_metadata"


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], required: set[str], label: str) -> None:
    actual = set(value)
    missing = required - actual
    extra = actual - required
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")


def _origin(value: Any, label: str) -> EvidenceOrigin:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    try:
        return EvidenceOrigin(value)
    except ValueError as exc:
        raise ValueError(f"{label} is unsupported") from exc


@dataclass(frozen=True, slots=True)
class PdfSourceIdentity:
    source_id: str
    sha256: str
    size: int
    media_type: str
    page_count: int

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_sha256(self.sha256, "sha256")
        _positive_int(self.size, "size")
        if self.media_type != "application/pdf":
            raise ValueError("media_type must be application/pdf")
        _positive_int(self.page_count, "page_count")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "sha256": self.sha256,
            "size": self.size,
            "media_type": self.media_type,
            "page_count": self.page_count,
        }


@dataclass(frozen=True, slots=True)
class SearchableTextEntry:
    page_number: int
    text: str
    bbox: tuple[float, float, float, float]
    text_origin: TextOrigin = TextOrigin.DERIVED_TEXT

    def __post_init__(self) -> None:
        _positive_int(self.page_number, "page_number")
        _require_text(self.text, "text")
        if not isinstance(self.text_origin, TextOrigin):
            raise ValueError("text_origin must be a TextOrigin")
        if not isinstance(self.bbox, tuple) or len(self.bbox) != 4:
            raise ValueError("bbox must contain four PDF-point coordinates")
        x0, y0, x1, y1 = self.bbox
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in self.bbox):
            raise ValueError("bbox values must be numbers")
        if x1 <= x0 or y1 <= y0:
            raise ValueError("bbox must have positive area")

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "bbox": [float(value) for value in self.bbox],
            "text_origin": self.text_origin.value,
        }


@dataclass(frozen=True, slots=True)
class OutlineEntry:
    level: int
    title: str
    page_number: int

    def __post_init__(self) -> None:
        _positive_int(self.level, "level")
        _require_text(self.title, "title")
        _positive_int(self.page_number, "page_number")

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level, "title": self.title, "page_number": self.page_number}


@dataclass(frozen=True, slots=True)
class PageLabelRange:
    start_page_number: int
    style: str
    first_page_number: int = 1
    prefix: str = ""

    def __post_init__(self) -> None:
        _positive_int(self.start_page_number, "start_page_number")
        if self.style not in _PAGE_LABEL_STYLES:
            raise ValueError(f"unsupported page-label style: {self.style}")
        _positive_int(self.first_page_number, "first_page_number")
        if not isinstance(self.prefix, str):
            raise ValueError("prefix must be a string")

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_page_number": self.start_page_number,
            "style": self.style,
            "first_page_number": self.first_page_number,
            "prefix": self.prefix,
        }


@dataclass(frozen=True, slots=True)
class SearchableTextOperation:
    evidence_origin: EvidenceOrigin
    entries: tuple[SearchableTextEntry, ...]
    kind: OperationKind = field(default=OperationKind.SEARCHABLE_TEXT, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_origin, EvidenceOrigin):
            raise ValueError("evidence_origin must be an EvidenceOrigin")
        if not self.entries or not isinstance(self.entries, tuple):
            raise ValueError("searchable-text entries must be a non-empty tuple")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "evidence_origin": self.evidence_origin.value,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class OutlineOperation:
    evidence_origin: EvidenceOrigin
    entries: tuple[OutlineEntry, ...]
    kind: OperationKind = field(default=OperationKind.OUTLINE, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_origin, EvidenceOrigin):
            raise ValueError("evidence_origin must be an EvidenceOrigin")
        if not self.entries or not isinstance(self.entries, tuple):
            raise ValueError("outline entries must be a non-empty tuple")
        previous_level = 0
        for index, entry in enumerate(self.entries):
            if index == 0 and entry.level != 1:
                raise ValueError("outline must begin at level 1")
            if entry.level > previous_level + 1:
                raise ValueError("outline levels must not skip hierarchy levels")
            previous_level = entry.level

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "evidence_origin": self.evidence_origin.value,
            "entries": [entry.to_dict() for entry in self.entries],
        }


@dataclass(frozen=True, slots=True)
class PageLabelsOperation:
    evidence_origin: EvidenceOrigin
    ranges: tuple[PageLabelRange, ...]
    kind: OperationKind = field(default=OperationKind.PAGE_LABELS, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_origin, EvidenceOrigin):
            raise ValueError("evidence_origin must be an EvidenceOrigin")
        if not self.ranges or not isinstance(self.ranges, tuple):
            raise ValueError("page-label ranges must be a non-empty tuple")
        starts = [item.start_page_number for item in self.ranges]
        if starts != sorted(starts) or len(starts) != len(set(starts)):
            raise ValueError("page-label ranges must have unique ascending starts")
        if starts[0] != 1:
            raise ValueError("page-label ranges must begin on physical page 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "evidence_origin": self.evidence_origin.value,
            "ranges": [item.to_dict() for item in self.ranges],
        }


@dataclass(frozen=True, slots=True)
class DescriptiveMetadataOperation:
    evidence_origin: EvidenceOrigin
    values: tuple[tuple[str, str], ...]
    kind: OperationKind = field(default=OperationKind.DESCRIPTIVE_METADATA, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_origin, EvidenceOrigin):
            raise ValueError("evidence_origin must be an EvidenceOrigin")
        if not self.values or not isinstance(self.values, tuple):
            raise ValueError("metadata values must be a non-empty tuple")
        object.__setattr__(self, "values", tuple(sorted(self.values)))
        keys: set[str] = set()
        for key, value in self.values:
            if key not in _ALLOWED_METADATA_FIELDS:
                raise ValueError(f"unsupported descriptive metadata field: {key}")
            _require_text(value, f"metadata.{key}")
            if key in keys:
                raise ValueError(f"duplicate descriptive metadata field: {key}")
            keys.add(key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "evidence_origin": self.evidence_origin.value,
            "values": {key: value for key, value in self.values},
        }


PdfEnrichmentOperation = SearchableTextOperation | OutlineOperation | PageLabelsOperation | DescriptiveMetadataOperation


@dataclass(frozen=True, slots=True)
class PdfEnrichmentPlan:
    source: PdfSourceIdentity
    operations: tuple[PdfEnrichmentOperation, ...]
    visible_content_change: str = "forbidden"
    replace_existing_features: bool = False
    plan_version: str = field(default=PDF_ENRICHMENT_PLAN_VERSION, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source, PdfSourceIdentity):
            raise ValueError("source must be a PdfSourceIdentity")
        if not isinstance(self.operations, tuple) or not self.operations:
            raise ValueError("operations must be a non-empty immutable tuple")
        kinds = [operation.kind for operation in self.operations]
        if len(kinds) != len(set(kinds)):
            raise ValueError("each enrichment operation kind may occur at most once")
        if self.visible_content_change != "forbidden":
            raise ValueError("visible_content_change must be forbidden in v1")
        if self.replace_existing_features is not False:
            raise ValueError("replace_existing_features must be false in v1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": self.plan_version,
            "type": "pdf_enrichment_plan",
            "source": self.source.to_dict(),
            "operations": [operation.to_dict() for operation in self.operations],
            "policy": {
                "visible_content_change": self.visible_content_change,
                "replace_existing_features": self.replace_existing_features,
            },
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PdfVerificationSummary:
    structural_valid: bool
    visual_pages_identical: bool
    tagged_structure_preserved: bool
    independent_backend: str
    page_count: int
    searchable_text_target_pages: tuple[int, ...]
    unchanged_native_text_pages: tuple[int, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "structural_valid": self.structural_valid,
            "visual_pages_identical": self.visual_pages_identical,
            "tagged_structure_preserved": self.tagged_structure_preserved,
            "independent_backend": self.independent_backend,
            "page_count": self.page_count,
            "searchable_text_target_pages": list(self.searchable_text_target_pages),
            "unchanged_native_text_pages": list(self.unchanged_native_text_pages),
        }


@dataclass(frozen=True, slots=True)
class PdfEnrichmentReceipt:
    source: PdfSourceIdentity
    derivative_sha256: str
    derivative_size: int
    plan_sha256: str
    tools: tuple[tuple[str, str], ...]
    operations: tuple[dict[str, Any], ...]
    verification: PdfVerificationSummary
    warnings: tuple[str, ...] = ()
    receipt_version: str = field(default=PDF_ENRICHMENT_RECEIPT_VERSION, init=False)

    def __post_init__(self) -> None:
        _require_sha256(self.derivative_sha256, "derivative_sha256")
        _positive_int(self.derivative_size, "derivative_size")
        _require_sha256(self.plan_sha256, "plan_sha256")

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_version": self.receipt_version,
            "type": "pdf_enrichment_receipt",
            "status": "verified",
            "source": self.source.to_dict(),
            "derivative": {"sha256": self.derivative_sha256, "size": self.derivative_size},
            "plan_sha256": self.plan_sha256,
            "tools": [{"name": name, "version": version} for name, version in self.tools],
            "operations": list(self.operations),
            "verification": self.verification.to_dict(),
            "warnings": list(self.warnings),
        }


def _source_from_dict(value: Any) -> PdfSourceIdentity:
    obj = _mapping(value, "source")
    _exact_keys(obj, {"source_id", "sha256", "size", "media_type", "page_count"}, "source")
    return PdfSourceIdentity(
        source_id=obj["source_id"],
        sha256=obj["sha256"],
        size=_positive_int(obj["size"], "source.size"),
        media_type=obj["media_type"],
        page_count=_positive_int(obj["page_count"], "source.page_count"),
    )


def _entry_bbox(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{label} must be an array of four numbers")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError(f"{label} must contain numbers")
    return tuple(float(item) for item in value)  # type: ignore[return-value]


def _operation_from_dict(value: Any, index: int) -> PdfEnrichmentOperation:
    label = f"operations[{index}]"
    obj = _mapping(value, label)
    kind_value = obj.get("kind")
    try:
        kind = OperationKind(kind_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}.kind is unsupported") from exc

    if kind is OperationKind.SEARCHABLE_TEXT:
        _exact_keys(obj, {"kind", "evidence_origin", "entries"}, label)
        entries_raw = obj["entries"]
        if not isinstance(entries_raw, list):
            raise ValueError(f"{label}.entries must be an array")
        entries: list[SearchableTextEntry] = []
        for entry_index, raw in enumerate(entries_raw):
            entry_label = f"{label}.entries[{entry_index}]"
            entry = _mapping(raw, entry_label)
            _exact_keys(entry, {"page_number", "text", "bbox", "text_origin"}, entry_label)
            entries.append(
                SearchableTextEntry(
                    page_number=_positive_int(entry["page_number"], f"{entry_label}.page_number"),
                    text=entry["text"],
                    bbox=_entry_bbox(entry["bbox"], f"{entry_label}.bbox"),
                    text_origin=TextOrigin(entry["text_origin"]),
                )
            )
        return SearchableTextOperation(_origin(obj["evidence_origin"], f"{label}.evidence_origin"), tuple(entries))

    if kind is OperationKind.OUTLINE:
        _exact_keys(obj, {"kind", "evidence_origin", "entries"}, label)
        entries_raw = obj["entries"]
        if not isinstance(entries_raw, list):
            raise ValueError(f"{label}.entries must be an array")
        entries: list[OutlineEntry] = []
        for entry_index, raw in enumerate(entries_raw):
            entry_label = f"{label}.entries[{entry_index}]"
            entry = _mapping(raw, entry_label)
            _exact_keys(entry, {"level", "title", "page_number"}, entry_label)
            entries.append(
                OutlineEntry(
                    level=_positive_int(entry["level"], f"{entry_label}.level"),
                    title=entry["title"],
                    page_number=_positive_int(entry["page_number"], f"{entry_label}.page_number"),
                )
            )
        return OutlineOperation(_origin(obj["evidence_origin"], f"{label}.evidence_origin"), tuple(entries))

    if kind is OperationKind.PAGE_LABELS:
        _exact_keys(obj, {"kind", "evidence_origin", "ranges"}, label)
        ranges_raw = obj["ranges"]
        if not isinstance(ranges_raw, list):
            raise ValueError(f"{label}.ranges must be an array")
        ranges: list[PageLabelRange] = []
        for range_index, raw in enumerate(ranges_raw):
            range_label = f"{label}.ranges[{range_index}]"
            item = _mapping(raw, range_label)
            _exact_keys(item, {"start_page_number", "style", "first_page_number", "prefix"}, range_label)
            ranges.append(
                PageLabelRange(
                    start_page_number=_positive_int(item["start_page_number"], f"{range_label}.start_page_number"),
                    style=item["style"],
                    first_page_number=_positive_int(item["first_page_number"], f"{range_label}.first_page_number"),
                    prefix=item["prefix"],
                )
            )
        return PageLabelsOperation(_origin(obj["evidence_origin"], f"{label}.evidence_origin"), tuple(ranges))

    _exact_keys(obj, {"kind", "evidence_origin", "values"}, label)
    values_raw = _mapping(obj["values"], f"{label}.values")
    return DescriptiveMetadataOperation(
        _origin(obj["evidence_origin"], f"{label}.evidence_origin"),
        tuple(sorted((str(key), value) for key, value in values_raw.items())),
    )


def plan_from_dict(value: Mapping[str, Any]) -> PdfEnrichmentPlan:
    obj = _mapping(value, "PDF enrichment plan")
    _exact_keys(obj, {"plan_version", "type", "source", "operations", "policy"}, "PDF enrichment plan")
    if obj["plan_version"] != PDF_ENRICHMENT_PLAN_VERSION:
        raise ValueError(f"plan_version must be {PDF_ENRICHMENT_PLAN_VERSION}")
    if obj["type"] != "pdf_enrichment_plan":
        raise ValueError("type must be pdf_enrichment_plan")
    operations_raw = obj["operations"]
    if not isinstance(operations_raw, list):
        raise ValueError("operations must be an array")
    policy = _mapping(obj["policy"], "policy")
    _exact_keys(policy, {"visible_content_change", "replace_existing_features"}, "policy")
    return PdfEnrichmentPlan(
        source=_source_from_dict(obj["source"]),
        operations=tuple(_operation_from_dict(item, index) for index, item in enumerate(operations_raw)),
        visible_content_change=policy["visible_content_change"],
        replace_existing_features=policy["replace_existing_features"],
    )
