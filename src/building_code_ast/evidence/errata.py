"""Printing-sensitive ICC errata records and bounded PDF extraction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
import re
from typing import Any

from ..model import DiagnosticSeverity
from .adapters import AdapterResult, EvidenceDiagnostic, SourceRegion
from .model import EvidenceRole, SourceRegisterEntry


ERRATA_RECORD_VERSION = "0.1.0"
_PUBLICATION_STATE_RE = re.compile(r"^publication:[0-9a-f]{64}$")
_PAGE_HEADER_RE = re.compile(
    r"^Page\s+(?P<page>.+?)[,.]\s+(?P<body>.+)$",
    re.IGNORECASE,
)
_SECTION_TARGET_RE = re.compile(
    r"^Section\s+(?P<locator>(?:\[[A-Z]+\]\s+)?[A-Z]?\d+(?:\.\d+)*)",
    re.IGNORECASE,
)
_DIRECTIVE_MARKERS = (
    " has been relocated ",
    " has been renumbered ",
    " has been deleted",
    " have been added",
    " has been added",
    " are corrected to read",
    " is corrected to read",
    " are revised to read",
    " is revised to read",
    " are deleted",
    " is deleted",
    " are added",
    " is added",
    " now reads",
    " now read",
)


class ErratumOperation(StrEnum):
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"


class TargetKind(StrEnum):
    SECTION = "section"
    TABLE = "table"
    FIGURE = "figure"
    DEFINITION = "definition"
    REFERENCED_STANDARD = "referenced_standard"
    OTHER = "other"


ERRATUM_OPERATION_VALUES = frozenset(item.value for item in ErratumOperation)
TARGET_KIND_VALUES = frozenset(item.value for item in TargetKind)


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _optional_text(value: str | None, label: str) -> None:
    if value is not None:
        _require_text(value, label)


def _strict_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    extra = sorted(actual - expected)
    missing = sorted(expected - actual)
    if extra:
        raise ValueError(f"{label} has unsupported fields: {', '.join(extra)}")
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(missing)}")


def _record_identity(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"erratum:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class ErratumRecord:
    source_id: str
    sequence: int
    base_publication_state_id: str
    correction_set: str
    applies_to_printings: tuple[str, ...]
    target_kind: TargetKind
    target_locator: str
    target_page_label: str
    operation: ErratumOperation
    instruction: str
    replacement_text: str | None
    source_page: int
    source_anchor: str
    record_version: str = field(default=ERRATA_RECORD_VERSION, init=False)

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not isinstance(self.base_publication_state_id, str) or _PUBLICATION_STATE_RE.fullmatch(
            self.base_publication_state_id
        ) is None:
            raise ValueError("base_publication_state_id must be a publication state identifier")
        _require_text(self.correction_set, "correction_set")
        if not isinstance(self.applies_to_printings, tuple) or not self.applies_to_printings:
            raise ValueError("applies_to_printings must be a nonempty tuple")
        for printing in self.applies_to_printings:
            _require_text(printing, "applies_to_printings item")
        if len(set(self.applies_to_printings)) != len(self.applies_to_printings):
            raise ValueError("applies_to_printings must not contain duplicates")
        if not isinstance(self.target_kind, TargetKind):
            raise ValueError("target_kind must be a TargetKind")
        _require_text(self.target_locator, "target_locator")
        _require_text(self.target_page_label, "target_page_label")
        if not isinstance(self.operation, ErratumOperation):
            raise ValueError("operation must be an ErratumOperation")
        _require_text(self.instruction, "instruction")
        _optional_text(self.replacement_text, "replacement_text")
        if self.operation in {ErratumOperation.INSERT, ErratumOperation.REPLACE} and self.replacement_text is None:
            raise ValueError("replacement_text is required for insert and replace operations")
        if self.operation is ErratumOperation.DELETE and self.replacement_text is not None:
            raise ValueError("replacement_text must be null for delete operations")
        if isinstance(self.source_page, bool) or not isinstance(self.source_page, int) or self.source_page < 1:
            raise ValueError("source_page must be a positive integer")
        _require_text(self.source_anchor, "source_anchor")

    @property
    def record_id(self) -> str:
        return _record_identity(self.identity_dict())

    def identity_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "sequence": self.sequence,
            "base_publication_state_id": self.base_publication_state_id,
            "correction_set": self.correction_set,
            "applies_to_printings": list(self.applies_to_printings),
            "target_kind": self.target_kind.value,
            "target_locator": self.target_locator,
            "target_page_label": self.target_page_label,
            "operation": self.operation.value,
            "instruction": self.instruction,
            "replacement_text": self.replacement_text,
            "source_page": self.source_page,
            "source_anchor": self.source_anchor,
        }

    def constructor_dict(self) -> dict[str, Any]:
        return {
            **self.identity_dict(),
            "applies_to_printings": self.applies_to_printings,
            "target_kind": self.target_kind,
            "operation": self.operation,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_version": self.record_version,
            "record_id": self.record_id,
            "type": "erratum_record",
            **self.identity_dict(),
        }


def erratum_record_from_dict(value: Mapping[str, Any]) -> ErratumRecord:
    if not isinstance(value, Mapping):
        raise ValueError("erratum record must be an object")
    expected = {
        "record_version",
        "record_id",
        "type",
        "source_id",
        "sequence",
        "base_publication_state_id",
        "correction_set",
        "applies_to_printings",
        "target_kind",
        "target_locator",
        "target_page_label",
        "operation",
        "instruction",
        "replacement_text",
        "source_page",
        "source_anchor",
    }
    _strict_keys(value, expected, "erratum record")
    if value["record_version"] != ERRATA_RECORD_VERSION:
        raise ValueError("record_version is unsupported")
    if value["type"] != "erratum_record":
        raise ValueError("type must be erratum_record")
    printings = value["applies_to_printings"]
    if not isinstance(printings, list):
        raise ValueError("applies_to_printings must be an array")
    try:
        target_kind = TargetKind(value["target_kind"])
    except (TypeError, ValueError) as exc:
        raise ValueError("target_kind is unsupported") from exc
    try:
        operation = ErratumOperation(value["operation"])
    except (TypeError, ValueError) as exc:
        raise ValueError("operation is unsupported") from exc
    record = ErratumRecord(
        source_id=value["source_id"],
        sequence=value["sequence"],
        base_publication_state_id=value["base_publication_state_id"],
        correction_set=value["correction_set"],
        applies_to_printings=tuple(printings),
        target_kind=target_kind,
        target_locator=value["target_locator"],
        target_page_label=value["target_page_label"],
        operation=operation,
        instruction=value["instruction"],
        replacement_text=value["replacement_text"],
        source_page=value["source_page"],
        source_anchor=value["source_anchor"],
    )
    if value["record_id"] != record.record_id:
        raise ValueError("record_id does not match deterministic identity")
    return record


def _default_pdf_page_text(content: bytes) -> tuple[str, ...]:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for ICC errata PDF extraction; install the evidence-pdf extra"
        ) from exc
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # pragma: no cover - dependency-specific parsing errors
        raise RuntimeError("PyMuPDF could not open the registered ICC errata PDF") from exc
    try:
        return tuple(page.get_text("text") for page in document)
    finally:
        document.close()


def _split_target_and_directive(body: str) -> tuple[str, str] | None:
    if ":" in body:
        target, directive = body.split(":", 1)
        if target.strip() and directive.strip():
            return target.strip(), directive.strip()

    section_match = _SECTION_TARGET_RE.match(body.strip())
    if section_match is not None:
        target = section_match.group(0).strip()
        directive = body.strip()[section_match.end() :].strip()
        if directive:
            return target, directive

    lowered = body.casefold()
    matches = [
        (lowered.find(marker), marker)
        for marker in _DIRECTIVE_MARKERS
        if lowered.find(marker) >= 0
    ]
    if not matches:
        return None
    index, _ = min(matches, key=lambda item: item[0])
    target = body[:index].strip()
    directive = body[index:].strip()
    if not target or not directive:
        return None
    return target, directive


def _operation(directive: str) -> ErratumOperation | None:
    lowered = directive.casefold()
    if "deleted" in lowered or "delete" in lowered:
        return ErratumOperation.DELETE
    if "added" in lowered:
        return ErratumOperation.INSERT
    if any(
        marker in lowered
        for marker in ("read", "revised", "corrected", "renumbered", "relocated")
    ):
        return ErratumOperation.REPLACE
    return None


def _target(target: str) -> tuple[TargetKind, str]:
    normalized = target.strip()
    section_match = _SECTION_TARGET_RE.match(normalized)
    if section_match is not None:
        return TargetKind.SECTION, section_match.group("locator").strip()
    lowered = normalized.casefold()
    prefixes = (
        ("table ", TargetKind.TABLE),
        ("figure ", TargetKind.FIGURE),
        ("definition ", TargetKind.DEFINITION),
        ("referenced standard ", TargetKind.REFERENCED_STANDARD),
    )
    for prefix, kind in prefixes:
        if lowered.startswith(prefix):
            return kind, normalized[len(prefix) :].strip()
    return TargetKind.OTHER, normalized


def _clean_instruction(value: str) -> str:
    cleaned = re.sub(r"(?:\s*\.\s*){3}$", "", value.strip()).strip()
    return cleaned.rstrip(".").strip()


class IccErrataPdfAdapter:
    """Extract a bounded family of ICC-style ``Page ..., target: directive`` entries."""

    adapter_id = "icc-errata-pdf"
    adapter_version = "0.3.0"
    supported_roles = frozenset({EvidenceRole.OFFICIAL_CORRECTION})
    supported_media_types = frozenset({"application/pdf"})

    def __init__(
        self,
        *,
        base_publication_state_id: str,
        applies_to_printings: tuple[str, ...],
        page_text_extractor: Callable[[bytes], tuple[str, ...]] | None = None,
    ) -> None:
        if not isinstance(base_publication_state_id, str) or _PUBLICATION_STATE_RE.fullmatch(
            base_publication_state_id
        ) is None:
            raise ValueError("base_publication_state_id must be a publication state identifier")
        if not isinstance(applies_to_printings, tuple) or not applies_to_printings:
            raise ValueError("applies_to_printings must be a nonempty tuple")
        for printing in applies_to_printings:
            _require_text(printing, "applies_to_printings item")
        if len(set(applies_to_printings)) != len(applies_to_printings):
            raise ValueError("applies_to_printings must not contain duplicates")
        if page_text_extractor is not None and not callable(page_text_extractor):
            raise ValueError("page_text_extractor must be callable")
        self.base_publication_state_id = base_publication_state_id
        self.applies_to_printings = applies_to_printings
        self.page_text_extractor = page_text_extractor or _default_pdf_page_text

    def extract(
        self,
        source: SourceRegisterEntry,
        content: bytes,
    ) -> AdapterResult[ErratumRecord]:
        correction_set = source.publication.correction_set
        if correction_set is None:
            raise ValueError("source publication correction_set is required")
        pages = self.page_text_extractor(content)
        if not isinstance(pages, tuple) or any(not isinstance(page, str) for page in pages):
            raise ValueError("page_text_extractor must return a tuple of strings")

        records: list[ErratumRecord] = []
        diagnostics: list[EvidenceDiagnostic] = []
        unsupported: list[SourceRegion] = []
        candidate_sequence = 0

        for source_page, page_text in enumerate(pages, start=1):
            entries: list[tuple[str, list[str]]] = []
            current_header: str | None = None
            current_lines: list[str] = []
            for raw_line in page_text.splitlines():
                line = raw_line.strip()
                if _PAGE_HEADER_RE.match(line):
                    if current_header is not None:
                        entries.append((current_header, current_lines))
                    current_header = line
                    current_lines = []
                elif current_header is not None and line:
                    current_lines.append(line)
            if current_header is not None:
                entries.append((current_header, current_lines))

            for header, body_lines in entries:
                candidate_sequence += 1
                anchor = f"errata:{candidate_sequence}"
                region = SourceRegion(page=source_page, anchor=anchor)
                header_match = _PAGE_HEADER_RE.fullmatch(header)
                assert header_match is not None
                target_and_directive = _split_target_and_directive(header_match.group("body"))
                if target_and_directive is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unsupported-erratum-header",
                            severity=DiagnosticSeverity.WARNING,
                            message="Erratum header did not expose a bounded target and directive.",
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                target_text, directive = target_and_directive
                operation = _operation(directive)
                if operation is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unsupported-erratum-directive",
                            severity=DiagnosticSeverity.WARNING,
                            message="Erratum directive is outside the bounded operation vocabulary.",
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                target_kind, target_locator = _target(target_text)
                replacement_text = None
                if operation in {ErratumOperation.INSERT, ErratumOperation.REPLACE}:
                    replacement_text = "\n".join(body_lines).strip() or None
                    if replacement_text is None:
                        diagnostics.append(
                            EvidenceDiagnostic(
                                code="missing-erratum-replacement",
                                severity=DiagnosticSeverity.WARNING,
                                message="Erratum requires replacement text but none was extracted.",
                                region=region,
                            )
                        )
                        unsupported.append(region)
                        continue
                records.append(
                    ErratumRecord(
                        source_id=source.source_id,
                        sequence=candidate_sequence,
                        base_publication_state_id=self.base_publication_state_id,
                        correction_set=correction_set,
                        applies_to_printings=self.applies_to_printings,
                        target_kind=target_kind,
                        target_locator=target_locator,
                        target_page_label=header_match.group("page").strip(),
                        operation=operation,
                        instruction=_clean_instruction(directive),
                        replacement_text=replacement_text,
                        source_page=source_page,
                        source_anchor=anchor,
                    )
                )

        return AdapterResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            records=tuple(records),
            diagnostics=tuple(diagnostics),
            unsupported_regions=tuple(unsupported),
        )
