"""Jurisdictional amendment patches and bounded Washington WAC HTML extraction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from html.parser import HTMLParser
import hashlib
import json
import re
from typing import Any

from ..model import DiagnosticSeverity
from .adapters import AdapterResult, EvidenceDiagnostic, SourceRegion
from .model import EvidenceRole
from .source_packages import BoundArtifact


AMENDMENT_PATCH_VERSION = "0.2.0"
_PUBLICATION_STATE_RE = re.compile(r"^publication:[0-9a-f]{64}$")
_WAC_RE = re.compile(r"^51-50-[0-9]+$")
_NORMALIZED_DIRECTIVE_RE = re.compile(
    r"^Section\s+(?P<locator>\S+)\s+(?P<directive>"
    r"is added|is replaced|is deleted|is reserved|applies only as follows)\.$",
    re.IGNORECASE,
)
_WAC_CITATION_RE = re.compile(
    r"^\s*(?:PDF\s*)?(?:WAC\s*)?(51-50-[0-9]+)\s*$",
    re.IGNORECASE,
)
_CLAUSE_RE = re.compile(
    r"^(?:\[[A-Z]+\]\s*)?"
    r"(?P<locator>[A-Z]?\d{3,}(?:\.\d+)*(?:\([A-Za-z0-9]+\))*)"
    r"(?:\.|\s)\s*(?P<body>.+)$"
)
_HISTORY_PREFIXES = (
    "[statutory authority:",
    "notes of wac",
    "reviser's note:",
)


class AmendmentOperation(StrEnum):
    ADD = "add"
    REPLACE = "replace"
    DELETE = "delete"
    RESERVE = "reserve"
    SCOPE = "scope"


AMENDMENT_OPERATION_VALUES = frozenset(item.value for item in AmendmentOperation)


def _require_text(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must not be empty")


def _optional_text(value: str | None, label: str) -> None:
    if value is not None:
        _require_text(value, label)


def _parse_date(value: str, label: str) -> date:
    _require_text(value, label)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO 8601 date") from exc


def _optional_date(value: str | None, label: str) -> date | None:
    if value is None:
        return None
    return _parse_date(value, label)


def _strict_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    extra = sorted(actual - expected)
    missing = sorted(expected - actual)
    if extra:
        raise ValueError(f"{label} has unsupported fields: {', '.join(extra)}")
    if missing:
        raise ValueError(f"{label} is missing fields: {', '.join(missing)}")


def _identity(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return f"amendment:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class JurisdictionalAmendmentPatch:
    source_id: str
    jurisdiction: str
    authority: str
    base_publication_state_id: str
    wac_citation: str
    locator: str
    operation: AmendmentOperation
    effective_from: str
    effective_to: str | None
    replacement_text: str | None
    scope: str | None
    sequence: int
    source_anchor: str
    patch_version: str = field(default=AMENDMENT_PATCH_VERSION, init=False)

    def __post_init__(self) -> None:
        _require_text(self.source_id, "source_id")
        _require_text(self.jurisdiction, "jurisdiction")
        _require_text(self.authority, "authority")
        if not isinstance(self.base_publication_state_id, str) or _PUBLICATION_STATE_RE.fullmatch(
            self.base_publication_state_id
        ) is None:
            raise ValueError("base_publication_state_id must be a publication state identifier")
        if not isinstance(self.wac_citation, str) or _WAC_RE.fullmatch(self.wac_citation) is None:
            raise ValueError("wac_citation must be a chapter 51-50 WAC citation")
        _require_text(self.locator, "locator")
        if not isinstance(self.operation, AmendmentOperation):
            raise ValueError("operation must be an AmendmentOperation")
        start = _parse_date(self.effective_from, "effective_from")
        end = _optional_date(self.effective_to, "effective_to")
        if end is not None and end <= start:
            raise ValueError("effective_to must be later than effective_from")
        _optional_text(self.replacement_text, "replacement_text")
        _optional_text(self.scope, "scope")
        if self.operation in {AmendmentOperation.ADD, AmendmentOperation.REPLACE}:
            if self.replacement_text is None:
                raise ValueError("replacement_text is required for add and replace operations")
        elif self.operation in {AmendmentOperation.DELETE, AmendmentOperation.RESERVE}:
            if self.replacement_text is not None:
                raise ValueError("replacement_text must be null for delete and reserve operations")
        elif self.operation is AmendmentOperation.SCOPE:
            if self.replacement_text is not None:
                raise ValueError("replacement_text must be null for scope operations")
            if self.scope is None:
                raise ValueError("scope is required for scope operations")
        if self.operation is not AmendmentOperation.SCOPE and self.scope is not None:
            raise ValueError("scope must be null for non-scope operations")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        _require_text(self.source_anchor, "source_anchor")

    @property
    def patch_id(self) -> str:
        return _identity(self.identity_dict())

    def identity_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "jurisdiction": self.jurisdiction,
            "authority": self.authority,
            "base_publication_state_id": self.base_publication_state_id,
            "wac_citation": self.wac_citation,
            "locator": self.locator,
            "operation": self.operation.value,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "replacement_text": self.replacement_text,
            "scope": self.scope,
            "sequence": self.sequence,
            "source_anchor": self.source_anchor,
        }

    def constructor_dict(self) -> dict[str, Any]:
        return {**self.identity_dict(), "operation": self.operation}

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch_version": self.patch_version,
            "patch_id": self.patch_id,
            "type": "jurisdictional_amendment_patch",
            **self.identity_dict(),
        }

    def is_active_on(self, value: str) -> bool:
        target = _parse_date(value, "date")
        start = date.fromisoformat(self.effective_from)
        end = date.fromisoformat(self.effective_to) if self.effective_to else None
        return target >= start and (end is None or target < end)


def amendment_patch_from_dict(value: Mapping[str, Any]) -> JurisdictionalAmendmentPatch:
    if not isinstance(value, Mapping):
        raise ValueError("amendment patch must be an object")
    expected = {
        "patch_version",
        "patch_id",
        "type",
        "source_id",
        "jurisdiction",
        "authority",
        "base_publication_state_id",
        "wac_citation",
        "locator",
        "operation",
        "effective_from",
        "effective_to",
        "replacement_text",
        "scope",
        "sequence",
        "source_anchor",
    }
    _strict_keys(value, expected, "amendment patch")
    if value["patch_version"] != AMENDMENT_PATCH_VERSION:
        raise ValueError("patch_version is unsupported")
    if value["type"] != "jurisdictional_amendment_patch":
        raise ValueError("type must be jurisdictional_amendment_patch")
    try:
        operation = AmendmentOperation(value["operation"])
    except (TypeError, ValueError) as exc:
        raise ValueError("operation is unsupported") from exc
    patch = JurisdictionalAmendmentPatch(
        source_id=value["source_id"],
        jurisdiction=value["jurisdiction"],
        authority=value["authority"],
        base_publication_state_id=value["base_publication_state_id"],
        wac_citation=value["wac_citation"],
        locator=value["locator"],
        operation=operation,
        effective_from=value["effective_from"],
        effective_to=value["effective_to"],
        replacement_text=value["replacement_text"],
        scope=value["scope"],
        sequence=value["sequence"],
        source_anchor=value["source_anchor"],
    )
    if value["patch_id"] != patch.patch_id:
        raise ValueError("patch_id does not match deterministic identity")
    return patch


def _intervals_overlap(
    first: JurisdictionalAmendmentPatch,
    second: JurisdictionalAmendmentPatch,
) -> bool:
    first_start = date.fromisoformat(first.effective_from)
    second_start = date.fromisoformat(second.effective_from)
    first_end = date.fromisoformat(first.effective_to) if first.effective_to else None
    second_end = date.fromisoformat(second.effective_to) if second.effective_to else None
    return (second_end is None or first_start < second_end) and (
        first_end is None or second_start < first_end
    )


def _same_effect(
    first: JurisdictionalAmendmentPatch,
    second: JurisdictionalAmendmentPatch,
) -> bool:
    return (
        first.operation is second.operation
        and first.replacement_text == second.replacement_text
        and first.scope == second.scope
        and first.authority == second.authority
        and first.jurisdiction == second.jurisdiction
        and first.base_publication_state_id == second.base_publication_state_id
    )


@dataclass(frozen=True, slots=True)
class AmendmentSet:
    patches: tuple[JurisdictionalAmendmentPatch, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.patches, tuple) or not self.patches:
            raise ValueError("patches must be a nonempty tuple")
        if any(not isinstance(patch, JurisdictionalAmendmentPatch) for patch in self.patches):
            raise ValueError("patches must contain JurisdictionalAmendmentPatch values")
        if len({patch.patch_id for patch in self.patches}) != len(self.patches):
            raise ValueError("patches must not contain duplicate identities")
        source_sequences = [(patch.source_id, patch.sequence) for patch in self.patches]
        if len(set(source_sequences)) != len(source_sequences):
            raise ValueError("patches must not reuse a source-local sequence")
        base_states = {patch.base_publication_state_id for patch in self.patches}
        if len(base_states) != 1:
            raise ValueError("patches must share one base publication state")
        jurisdictions = {patch.jurisdiction for patch in self.patches}
        if len(jurisdictions) != 1:
            raise ValueError("patches must share one jurisdiction")
        for index, first in enumerate(self.patches):
            for second in self.patches[index + 1 :]:
                if first.locator != second.locator or not _intervals_overlap(first, second):
                    continue
                if _same_effect(first, second):
                    continue
                if {first.operation, second.operation} in (
                    {AmendmentOperation.SCOPE, AmendmentOperation.REPLACE},
                    {AmendmentOperation.SCOPE, AmendmentOperation.ADD},
                ):
                    continue
                raise ValueError(
                    f"overlapping amendment conflict for locator {first.locator}"
                )

    def ordered(self) -> tuple[JurisdictionalAmendmentPatch, ...]:
        return tuple(
            sorted(
                self.patches,
                key=lambda patch: (
                    patch.effective_from,
                    patch.sequence,
                    patch.wac_citation,
                    patch.locator,
                    patch.patch_id,
                ),
            )
        )

    def active_for(
        self,
        locator: str,
        on_date: str,
    ) -> tuple[JurisdictionalAmendmentPatch, ...]:
        _require_text(locator, "locator")
        _parse_date(on_date, "on_date")
        return tuple(
            patch
            for patch in self.ordered()
            if patch.locator == locator and patch.is_active_on(on_date)
        )


def _locator_ancestors(locator: str) -> tuple[str, ...]:
    ancestors: list[str] = []
    current = locator
    while current.endswith(")") and "(" in current:
        current = current[: current.rfind("(")]
        if current:
            ancestors.append(current)
    while "." in current:
        current = current.rsplit(".", 1)[0]
        ancestors.append(current)

    section_match = re.fullmatch(r"(?P<appendix>[A-Z])?(?P<number>\d{3,})", current)
    if section_match is not None:
        appendix = section_match.group("appendix")
        if appendix is not None:
            if appendix not in ancestors:
                ancestors.append(appendix)
        else:
            chapter = str(int(section_match.group("number")) // 100)
            if chapter not in ancestors and chapter != current:
                ancestors.append(chapter)
    return tuple(ancestors)


def _resolve_operation(
    locator: str,
    known_base_locators: frozenset[str] | None,
) -> AmendmentOperation | None:
    if known_base_locators is None:
        return None
    if locator in known_base_locators:
        return AmendmentOperation.REPLACE
    if any(parent in known_base_locators for parent in _locator_ancestors(locator)):
        return AmendmentOperation.ADD
    return None


class _NormalizedWacSectionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[tuple[str, tuple[str, ...]]] = []
        self._in_section = False
        self._capture_tag: str | None = None
        self._buffer: list[str] = []
        self._heading: str | None = None
        self._paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "section":
            self._in_section = True
            self._heading = None
            self._paragraphs = []
        if self._in_section and tag in {"h1", "h2", "h3", "h4", "p", "li"}:
            self._capture_tag = tag
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_tag is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture_tag == tag:
            text = " ".join("".join(self._buffer).split())
            if text:
                if tag.startswith("h") and self._heading is None:
                    self._heading = text
                elif tag in {"p", "li"}:
                    self._paragraphs.append(text)
            self._capture_tag = None
            self._buffer = []
        if tag == "section" and self._in_section:
            if self._heading is not None:
                self.sections.append((self._heading, tuple(self._paragraphs)))
            self._in_section = False


def _parse_normalized_sections(content: bytes) -> tuple[tuple[str, tuple[str, ...]], ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Washington WAC HTML must be UTF-8") from exc
    parser = _NormalizedWacSectionParser()
    parser.feed(text)
    parser.close()
    return tuple(parser.sections)


_NORMALIZED_OPERATION_BY_DIRECTIVE = {
    "is added": AmendmentOperation.ADD,
    "is replaced": AmendmentOperation.REPLACE,
    "is deleted": AmendmentOperation.DELETE,
    "is reserved": AmendmentOperation.RESERVE,
    "applies only as follows": AmendmentOperation.SCOPE,
}


class NormalizedWashingtonWacHtmlAdapter:
    """Extract explicit amendment directives from project-normalized WAC HTML."""

    adapter_id = "washington-wac-normalized-html"
    adapter_version = "0.2.0"
    supported_roles = frozenset({EvidenceRole.JURISDICTIONAL_LAW})
    supported_media_types = frozenset({"text/html"})

    def __init__(
        self,
        *,
        base_publication_state_id: str,
        effective_from: str,
        effective_to: str | None = None,
        known_base_locators: frozenset[str] | None = None,
    ) -> None:
        if not isinstance(base_publication_state_id, str) or _PUBLICATION_STATE_RE.fullmatch(
            base_publication_state_id
        ) is None:
            raise ValueError("base_publication_state_id must be a publication state identifier")
        start = _parse_date(effective_from, "effective_from")
        end = _optional_date(effective_to, "effective_to")
        if end is not None and end <= start:
            raise ValueError("effective_to must be later than effective_from")
        if known_base_locators is not None:
            if not isinstance(known_base_locators, frozenset):
                raise ValueError("known_base_locators must be a frozenset")
            for locator in known_base_locators:
                _require_text(locator, "known base locator")
        self.base_publication_state_id = base_publication_state_id
        self.effective_from = effective_from
        self.effective_to = effective_to
        self.known_base_locators = known_base_locators

    def extract(
        self,
        source: BoundArtifact,
        content: bytes,
    ) -> AdapterResult[JurisdictionalAmendmentPatch]:
        if source.jurisdiction is None:
            raise ValueError("source jurisdiction is required")
        sections = _parse_normalized_sections(content)
        records: list[JurisdictionalAmendmentPatch] = []
        diagnostics: list[EvidenceDiagnostic] = []
        unsupported: list[SourceRegion] = []

        for ordinal, (heading, paragraphs) in enumerate(sections, start=1):
            citation_match = re.search(r"WAC\s+(51-50-[0-9]+)", heading, re.IGNORECASE)
            anchor = f"normalized-wac-section:{ordinal}"
            region = SourceRegion(anchor=anchor)
            if citation_match is None or not paragraphs:
                diagnostics.append(
                    EvidenceDiagnostic(
                        code="unsupported-wac-section",
                        severity=DiagnosticSeverity.WARNING,
                        message="WAC section did not expose a citation and amendment directive.",
                        region=region,
                    )
                )
                unsupported.append(region)
                continue
            wac_citation = citation_match.group(1)
            directive_match = _NORMALIZED_DIRECTIVE_RE.fullmatch(paragraphs[0])
            if directive_match is None:
                diagnostics.append(
                    EvidenceDiagnostic(
                        code="unsupported-amendment-directive",
                        severity=DiagnosticSeverity.WARNING,
                        message="WAC directive is outside the bounded amendment vocabulary.",
                        region=region,
                    )
                )
                unsupported.append(region)
                continue
            locator = directive_match.group("locator").rstrip(".")
            directive = directive_match.group("directive").casefold()
            operation = _NORMALIZED_OPERATION_BY_DIRECTIVE[directive]
            if self.known_base_locators is not None:
                locator_resolves = locator in self.known_base_locators
                if operation is AmendmentOperation.ADD:
                    locator_resolves = locator_resolves or any(
                        parent in self.known_base_locators
                        for parent in _locator_ancestors(locator)
                    )
                if not locator_resolves:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unresolved-base-locator",
                            severity=DiagnosticSeverity.WARNING,
                            message="Amendment locator did not resolve against the supplied base-locator oracle.",
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
            body = "\n".join(paragraphs[1:]).strip() or None
            replacement_text = (
                body
                if operation in {AmendmentOperation.ADD, AmendmentOperation.REPLACE}
                else None
            )
            scope = body if operation is AmendmentOperation.SCOPE else None
            if operation in {
                AmendmentOperation.ADD,
                AmendmentOperation.REPLACE,
                AmendmentOperation.SCOPE,
            } and body is None:
                diagnostics.append(
                    EvidenceDiagnostic(
                        code="missing-amendment-body",
                        severity=DiagnosticSeverity.WARNING,
                        message="Amendment directive requires a body that was not extracted.",
                        region=region,
                    )
                )
                unsupported.append(region)
                continue
            records.append(
                JurisdictionalAmendmentPatch(
                    source_id=source.source_id,
                    jurisdiction=source.jurisdiction,
                    authority=source.issuing_body,
                    base_publication_state_id=self.base_publication_state_id,
                    wac_citation=wac_citation,
                    locator=locator,
                    operation=operation,
                    effective_from=self.effective_from,
                    effective_to=self.effective_to,
                    replacement_text=replacement_text,
                    scope=scope,
                    sequence=ordinal,
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


class _OfficialWacBlockParser(HTMLParser):
    _BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._capture_tag: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._capture_tag is None and tag in self._BLOCK_TAGS:
            self._capture_tag = tag
            self._buffer = []
        elif self._capture_tag is not None and tag == "br":
            self._buffer.append(" ")

    def handle_data(self, data: str) -> None:
        if self._capture_tag is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture_tag == tag:
            text = " ".join("".join(self._buffer).split())
            if text:
                self.blocks.append(text)
            self._capture_tag = None
            self._buffer = []


def _parse_official_blocks(content: bytes) -> tuple[str, ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Washington WAC HTML must be UTF-8") from exc
    parser = _OfficialWacBlockParser()
    parser.feed(text)
    parser.close()
    return tuple(parser.blocks)


def _wac_sections(blocks: tuple[str, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    sections: list[tuple[str, tuple[str, ...]]] = []
    citation: str | None = None
    body: list[str] = []
    for block in blocks:
        match = _WAC_CITATION_RE.search(block)
        if match is not None:
            if citation is not None:
                sections.append((citation, tuple(body)))
            citation = match.group(1)
            body = []
        elif citation is not None:
            body.append(block)
    if citation is not None:
        sections.append((citation, tuple(body)))
    return tuple(sections)


def _is_history_block(text: str) -> bool:
    lowered = text.casefold().lstrip()
    return any(lowered.startswith(prefix) for prefix in _HISTORY_PREFIXES)


def _group_clause_texts(blocks: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
    groups: list[tuple[str, list[str]]] = []
    current_locator: str | None = None
    current_lines: list[str] = []
    for block in blocks:
        if _is_history_block(block):
            break
        if block.casefold().startswith("section "):
            continue
        match = _CLAUSE_RE.fullmatch(block)
        if match is not None:
            if current_locator is not None:
                groups.append((current_locator, current_lines))
            current_locator = match.group("locator")
            current_lines = [block]
        elif current_locator is not None:
            current_lines.append(block)
    if current_locator is not None:
        groups.append((current_locator, current_lines))
    return tuple((locator, "\n".join(lines)) for locator, lines in groups)


def _validated_date_mapping(
    value: Mapping[str, str] | None,
    label: str,
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    result: dict[str, str] = {}
    for citation, date_value in value.items():
        if not isinstance(citation, str) or _WAC_RE.fullmatch(citation) is None:
            raise ValueError(f"{label} keys must be chapter 51-50 WAC citations")
        _parse_date(date_value, f"{label}[{citation}]")
        result[citation] = date_value
    return result


def _validated_locator_mapping(
    value: Mapping[str, str] | None,
    label: str,
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    result: dict[str, str] = {}
    for citation, locator in value.items():
        if not isinstance(citation, str) or _WAC_RE.fullmatch(citation) is None:
            raise ValueError(f"{label} keys must be chapter 51-50 WAC citations")
        _require_text(locator, f"{label}[{citation}]")
        result[citation] = locator
    return result


def _validated_locator_date_mapping(
    value: Mapping[str, str] | None,
    label: str,
) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    result: dict[str, str] = {}
    for locator, date_value in value.items():
        _require_text(locator, f"{label} locator")
        _parse_date(date_value, f"{label}[{locator}]")
        result[locator] = date_value
    return result


class WashingtonWacHtmlAdapter:
    """Extract bounded amendment patches from official-style chapter 51-50 WAC HTML."""

    adapter_id = "washington-wac-html"
    adapter_version = "0.3.0"
    supported_roles = frozenset({EvidenceRole.JURISDICTIONAL_LAW})
    supported_media_types = frozenset({"text/html"})

    def __init__(
        self,
        *,
        base_publication_state_id: str,
        known_base_locators: frozenset[str],
        effective_dates_by_wac: Mapping[str, str] | None = None,
        effective_to_dates_by_wac: Mapping[str, str] | None = None,
        effective_dates_by_locator: Mapping[str, str] | None = None,
        effective_to_dates_by_locator: Mapping[str, str] | None = None,
        reserved_locators_by_wac: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(base_publication_state_id, str) or _PUBLICATION_STATE_RE.fullmatch(
            base_publication_state_id
        ) is None:
            raise ValueError("base_publication_state_id must be a publication state identifier")
        if not isinstance(known_base_locators, frozenset) or not known_base_locators:
            raise ValueError("known_base_locators must be a nonempty frozenset")
        for locator in known_base_locators:
            _require_text(locator, "known base locator")
        self.base_publication_state_id = base_publication_state_id
        self.known_base_locators = known_base_locators
        self.effective_dates_by_wac = _validated_date_mapping(
            effective_dates_by_wac, "effective_dates_by_wac"
        )
        self.effective_to_dates_by_wac = _validated_date_mapping(
            effective_to_dates_by_wac, "effective_to_dates_by_wac"
        )
        self.effective_dates_by_locator = _validated_locator_date_mapping(
            effective_dates_by_locator, "effective_dates_by_locator"
        )
        self.effective_to_dates_by_locator = _validated_locator_date_mapping(
            effective_to_dates_by_locator, "effective_to_dates_by_locator"
        )
        self.reserved_locators_by_wac = _validated_locator_mapping(
            reserved_locators_by_wac, "reserved_locators_by_wac"
        )
        for citation, end_value in self.effective_to_dates_by_wac.items():
            start_value = self.effective_dates_by_wac.get(citation)
            if start_value is not None and date.fromisoformat(end_value) <= date.fromisoformat(start_value):
                raise ValueError(
                    f"effective_to date for {citation} must be later than effective_from"
                )
        for locator, end_value in self.effective_to_dates_by_locator.items():
            start_value = self.effective_dates_by_locator.get(locator)
            if start_value is not None and date.fromisoformat(end_value) <= date.fromisoformat(start_value):
                raise ValueError(
                    f"effective_to date for {locator} must be later than effective_from"
                )

    def _effective_from(
        self,
        citation: str,
        locator: str,
        source: BoundArtifact,
    ) -> str | None:
        return (
            self.effective_dates_by_locator.get(locator)
            or self.effective_dates_by_wac.get(citation)
            or source.publication.effective_on
        )

    def _effective_to(self, citation: str, locator: str) -> str | None:
        return self.effective_to_dates_by_locator.get(
            locator,
            self.effective_to_dates_by_wac.get(citation),
        )

    def extract(
        self,
        source: BoundArtifact,
        content: bytes,
    ) -> AdapterResult[JurisdictionalAmendmentPatch]:
        if source.jurisdiction is None:
            raise ValueError("source jurisdiction is required")
        sections = _wac_sections(_parse_official_blocks(content))
        records: list[JurisdictionalAmendmentPatch] = []
        diagnostics: list[EvidenceDiagnostic] = []
        unsupported: list[SourceRegion] = []
        candidate_sequence = 0

        for citation, blocks in sections:
            candidate_sequence += 1
            section_region = SourceRegion(anchor=f"wac:{citation}")
            if any(block.strip().casefold().rstrip(".") == "reserved" for block in blocks):
                locator = self.reserved_locators_by_wac.get(citation)
                if locator is None or locator not in self.known_base_locators:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unresolved-reserved-locator",
                            severity=DiagnosticSeverity.WARNING,
                            message="Reserved WAC section requires an explicit resolvable base locator.",
                            region=section_region,
                        )
                    )
                    unsupported.append(section_region)
                    continue
                effective_from = self._effective_from(citation, locator, source)
                if effective_from is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="missing-amendment-effective-date",
                            severity=DiagnosticSeverity.WARNING,
                            message="WAC section has no registered effective date.",
                            region=section_region,
                        )
                    )
                    unsupported.append(section_region)
                    continue
                records.append(
                    JurisdictionalAmendmentPatch(
                        source_id=source.source_id,
                        jurisdiction=source.jurisdiction,
                        authority=source.issuing_body,
                        base_publication_state_id=self.base_publication_state_id,
                        wac_citation=citation,
                        locator=locator,
                        operation=AmendmentOperation.RESERVE,
                        effective_from=effective_from,
                        effective_to=self._effective_to(citation, locator),
                        replacement_text=None,
                        scope=None,
                        sequence=candidate_sequence,
                        source_anchor=f"wac:{citation}:{locator}",
                    )
                )
                continue

            clauses = _group_clause_texts(blocks)
            if not clauses:
                diagnostics.append(
                    EvidenceDiagnostic(
                        code="unsupported-wac-section",
                        severity=DiagnosticSeverity.WARNING,
                        message="WAC section did not expose a bounded code locator or reserved marker.",
                        region=section_region,
                    )
                )
                unsupported.append(section_region)
                continue

            for clause_index, (locator, replacement_text) in enumerate(clauses):
                if clause_index:
                    candidate_sequence += 1
                region = SourceRegion(anchor=f"wac:{citation}:{locator}")
                effective_from = self._effective_from(citation, locator, source)
                if effective_from is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="missing-amendment-effective-date",
                            severity=DiagnosticSeverity.WARNING,
                            message="WAC clause has no registered effective date.",
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                operation = _resolve_operation(locator, self.known_base_locators)
                if operation is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unresolved-base-locator",
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                "WAC clause could not be classified as an add or replacement "
                                "against the supplied base-locator oracle."
                            ),
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                records.append(
                    JurisdictionalAmendmentPatch(
                        source_id=source.source_id,
                        jurisdiction=source.jurisdiction,
                        authority=source.issuing_body,
                        base_publication_state_id=self.base_publication_state_id,
                        wac_citation=citation,
                        locator=locator,
                        operation=operation,
                        effective_from=effective_from,
                        effective_to=self._effective_to(citation, locator),
                        replacement_text=replacement_text,
                        scope=None,
                        sequence=candidate_sequence,
                        source_anchor=f"wac:{citation}:{locator}",
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
