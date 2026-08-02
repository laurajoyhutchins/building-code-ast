"""NEC publication hierarchy inference and local conformance reporting.

The hierarchy builder operates only on source-backed nodes produced by local PDF
extraction. The oracle helpers compare parser output with a separately supplied
reference; they never repair or replace parser output.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import csv
import io
import re
from typing import Any, Sequence

from ..document_model import (
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from ..model import Diagnostic, DiagnosticSeverity, SourceSpan


HIERARCHY_VERSION = "0.1.0"

_LOCATOR_RE = re.compile(
    r"^(?P<article>\d{2,3})(?P<section>\.\d+[A-Za-z]?)?"
    r"(?P<markers>(?:\([A-Za-z0-9]+\))*)$"
)
_MARKER_RE = re.compile(r"^\((?P<marker>[A-Za-z0-9]+)\)")
_PART_RE = re.compile(r"^Part\s+(?P<number>[IVXLC]+)\.\s*(?P<title>.*)$")
_SECTION_TEXT_RE = re.compile(
    r"^(?P<locator>\d{2,3}\.\d+[A-Za-z]?)\s+(?P<body>.*)$"
)


@dataclass(frozen=True, slots=True)
class HierarchyBuildResult:
    nodes: tuple[DocumentNode, ...]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class HierarchyRecord:
    locator: str
    title: str
    parent: str | None
    order: int
    depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "locator": self.locator,
            "title": self.title,
            "parent": self.parent,
            "order": self.order,
            "depth": self.depth,
        }


@dataclass(frozen=True, slots=True)
class HierarchyMismatch:
    code: str
    locator: str
    message: str
    expected: str | int | None = None
    actual: str | int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "locator": self.locator,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True, slots=True)
class HierarchyConformanceReport:
    expected_records: int
    actual_records: int
    matches: int
    mismatches: tuple[HierarchyMismatch, ...]
    hierarchy_version: str = HIERARCHY_VERSION

    @property
    def conforms(self) -> bool:
        return not self.mismatches

    def to_dict(self) -> dict[str, Any]:
        counts = Counter(item.code for item in self.mismatches)
        return {
            "hierarchy_version": self.hierarchy_version,
            "conforms": self.conforms,
            "expected_records": self.expected_records,
            "actual_records": self.actual_records,
            "matches": self.matches,
            "mismatch_counts": dict(sorted(counts.items())),
            "mismatches": [item.to_dict() for item in self.mismatches],
        }


def canonical_nec_locator(value: str) -> str:
    """Return one whitespace-free NEC article or clause locator."""

    compact = re.sub(r"\s+", "", value)
    match = _LOCATOR_RE.fullmatch(compact)
    if match is None:
        raise ValueError(f"invalid NEC locator: {value!r}")
    return compact


def nec_parent_locator(value: str) -> str | None:
    """Return the canonical parent implied by one NEC locator."""

    locator = canonical_nec_locator(value)
    marker_starts = [match.start() for match in re.finditer(r"\(", locator)]
    if marker_starts:
        return locator[: marker_starts[-1]]
    if "." in locator:
        return locator.split(".", 1)[0]
    return None


def nec_locator_depth(value: str) -> int:
    """Return Article=0, Section=1, and one additional level per marker."""

    locator = canonical_nec_locator(value)
    return (1 if "." in locator else 0) + locator.count("(")


def _marker_kind(marker: str) -> str:
    if marker.isdigit():
        return "numeric"
    if len(marker) == 1 and marker.isalpha() and marker.isupper():
        return "upper"
    if len(marker) == 1 and marker.isalpha() and marker.islower():
        return "lower"
    return "other"


def _node_text(node: DocumentNode) -> str:
    return node.span.text.strip()


def _section_identity(node: DocumentNode) -> tuple[str, str] | None:
    match = _SECTION_TEXT_RE.match(_node_text(node))
    if match is None:
        return None
    locator = canonical_nec_locator(match.group("locator"))
    body = match.group("body").strip()
    title = body.split(".", 1)[0].strip() if "." in body else ""
    return locator, title


def _marker_identity(node: DocumentNode) -> tuple[str, str] | None:
    text = _node_text(node)
    match = _MARKER_RE.match(text)
    if match is None:
        return None
    marker = match.group("marker")
    body = text[match.end() :].strip()
    title = body.split(".", 1)[0].strip() if "." in body else ""
    return marker, title


def _part_identity(node: DocumentNode) -> tuple[str, str] | None:
    match = _PART_RE.match(_node_text(node))
    if match is None:
        return None
    return match.group("number"), match.group("title").strip()


@dataclass(slots=True)
class _DraftNode:
    original: DocumentNode
    locator: str
    attributes: dict[str, str]
    label: str | None
    children: list["_DraftNode"] = field(default_factory=list)
    marker_kind: str | None = None
    nec_locator: str | None = None

    def freeze(
        self,
        *,
        source_text: str,
        source_artifact: DocumentSourceArtifact,
    ) -> DocumentNode:
        frozen_children = tuple(
            child.freeze(source_text=source_text, source_artifact=source_artifact)
            for child in self.children
        )
        end = max(
            [self.original.span.end, *(child.span.end for child in frozen_children)]
        )
        span = SourceSpan(
            self.original.span.start,
            end,
            source_text[self.original.span.start : end],
        )
        return make_document_node(
            source_artifact=source_artifact,
            node_type=self.original.node_type,
            locator=self.locator,
            span=span,
            label=self.label,
            attributes=self.attributes,
            children=frozen_children,
        )


def _draft_from_original(node: DocumentNode) -> _DraftNode:
    return _DraftNode(
        original=node,
        locator=node.locator,
        attributes=dict(node.attributes),
        label=node.label,
    )


def _diagnostic(code: str, message: str, node: DocumentNode) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DiagnosticSeverity.WARNING,
        message=message,
        span=node.span,
    )


def _marker_parent(
    marker_kind: str,
    section: _DraftNode,
    open_markers: list[_DraftNode],
) -> tuple[_DraftNode, list[_DraftNode], bool]:
    """Return parent, retained stack, and whether the inference is ambiguous."""

    if marker_kind == "upper":
        return section, [], False
    if not open_markers:
        return section, [], True

    top = open_markers[-1]
    if marker_kind == "numeric":
        if top.marker_kind in {"upper", "lower"}:
            return top, open_markers, False
        if top.marker_kind == "numeric":
            parent = open_markers[-2] if len(open_markers) >= 2 else section
            return parent, open_markers[:-1], False
    elif marker_kind == "lower":
        if top.marker_kind in {"upper", "numeric"}:
            return top, open_markers, False
        if top.marker_kind == "lower":
            parent = open_markers[-2] if len(open_markers) >= 2 else section
            return parent, open_markers[:-1], False

    return top, open_markers, True


def build_nec_hierarchy(
    *,
    article_number: str,
    source_text: str,
    source_artifact: DocumentSourceArtifact,
    nodes: Sequence[DocumentNode],
) -> HierarchyBuildResult:
    """Nest classified ArticleSeed nodes by inferred NEC structural ownership."""

    article = canonical_nec_locator(article_number)
    if "." in article:
        raise ValueError("article_number must identify an NEC article")

    roots: list[_DraftNode] = []
    diagnostics: list[Diagnostic] = []
    seen_locators: set[str] = set()
    current_part: _DraftNode | None = None
    current_section: _DraftNode | None = None
    open_markers: list[_DraftNode] = []

    def append_to_current(draft: _DraftNode) -> None:
        if open_markers:
            open_markers[-1].children.append(draft)
        elif current_section is not None:
            current_section.children.append(draft)
        elif current_part is not None:
            current_part.children.append(draft)
        else:
            roots.append(draft)

    for node in nodes:
        part = _part_identity(node)
        if part is not None:
            number, title = part
            attributes = dict(node.attributes)
            attributes.update(
                {
                    "nec_part": number,
                    "nec_structural_role": "part",
                    "nec_title": title,
                }
            )
            draft = _DraftNode(
                original=node,
                locator=f"article:{article}/part:{number}",
                attributes=attributes,
                label=node.label or f"Part {number}. {title}".strip(),
            )
            roots.append(draft)
            current_part = draft
            current_section = None
            open_markers = []
            continue

        section_identity = (
            _section_identity(node) if node.node_type == DocumentNodeType.SECTION else None
        )
        if section_identity is not None:
            locator, title = section_identity
            if not locator.startswith(article + "."):
                diagnostics.append(
                    _diagnostic(
                        "cross-article-section",
                        f"Section {locator} does not belong to Article {article}.",
                        node,
                    )
                )
                append_to_current(_draft_from_original(node))
                continue
            if locator in seen_locators:
                diagnostics.append(
                    _diagnostic(
                        "duplicate-nec-locator",
                        f"The inferred locator {locator} occurs more than once.",
                        node,
                    )
                )
                append_to_current(_draft_from_original(node))
                continue
            seen_locators.add(locator)
            attributes = dict(node.attributes)
            attributes.update(
                {
                    "nec_locator": locator,
                    "nec_parent": article,
                    "nec_depth": str(nec_locator_depth(locator)),
                    "nec_structural_role": "section",
                    "nec_title": title,
                }
            )
            draft = _DraftNode(
                original=node,
                locator=f"nec:{locator}",
                attributes=attributes,
                label=node.label,
                nec_locator=locator,
            )
            if current_part is not None:
                current_part.children.append(draft)
            else:
                roots.append(draft)
            current_section = draft
            open_markers = []
            continue

        marker_identity = (
            _marker_identity(node)
            if node.node_type in {DocumentNodeType.SUBSECTION, DocumentNodeType.LIST_ITEM}
            else None
        )
        if marker_identity is not None:
            marker, title = marker_identity
            if current_section is None or current_section.nec_locator is None:
                diagnostics.append(
                    _diagnostic(
                        "orphan-nec-marker",
                        f"Marker ({marker}) has no open NEC section.",
                        node,
                    )
                )
                append_to_current(_draft_from_original(node))
                continue

            kind = _marker_kind(marker)
            parent, retained, ambiguous = _marker_parent(
                kind,
                current_section,
                open_markers,
            )
            parent_locator = parent.nec_locator or current_section.nec_locator
            locator = canonical_nec_locator(f"{parent_locator}({marker})")
            if ambiguous:
                diagnostics.append(
                    _diagnostic(
                        "ambiguous-nec-marker-depth",
                        (
                            f"Marker ({marker}) was attached beneath {parent_locator}, but "
                            "its depth could not be established from the open marker stack."
                        ),
                        node,
                    )
                )
            if locator in seen_locators:
                diagnostics.append(
                    _diagnostic(
                        "duplicate-nec-locator",
                        f"The inferred locator {locator} occurs more than once.",
                        node,
                    )
                )
                append_to_current(_draft_from_original(node))
                continue
            seen_locators.add(locator)
            attributes = dict(node.attributes)
            attributes.update(
                {
                    "nec_locator": locator,
                    "nec_parent": parent_locator,
                    "nec_depth": str(nec_locator_depth(locator)),
                    "nec_marker": marker,
                    "nec_marker_kind": kind,
                    "nec_structural_role": "clause",
                    "nec_title": title,
                }
            )
            draft = _DraftNode(
                original=node,
                locator=f"nec:{locator}",
                attributes=attributes,
                label=node.label,
                marker_kind=kind,
                nec_locator=locator,
            )
            parent.children.append(draft)
            open_markers = [*retained, draft]
            continue

        append_to_current(_draft_from_original(node))

    frozen = tuple(
        node.freeze(source_text=source_text, source_artifact=source_artifact)
        for node in roots
    )
    return HierarchyBuildResult(nodes=frozen, diagnostics=tuple(diagnostics))


def load_clause_oracle(csv_text: str) -> tuple[HierarchyRecord, ...]:
    """Load the junk-drawer-compatible clause CSV representation from text."""

    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"clause_id", "clause_title", "parent"}
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise ValueError("clause oracle must contain clause_id, clause_title, and parent")

    records: list[HierarchyRecord] = []
    for order, row in enumerate(reader):
        locator = canonical_nec_locator(row["clause_id"])
        raw_parent = row["parent"].strip()
        parent = canonical_nec_locator(raw_parent) if raw_parent else None
        depth = 0 if parent is None else nec_locator_depth(parent) + 1
        records.append(
            HierarchyRecord(
                locator=locator,
                title=row["clause_title"].strip(),
                parent=parent,
                order=order,
                depth=depth,
            )
        )
    return tuple(records)


def flatten_nec_hierarchy(nodes: Sequence[DocumentNode]) -> tuple[HierarchyRecord, ...]:
    """Project inferred structural nodes into oracle-comparable preorder records."""

    records: list[HierarchyRecord] = []

    def visit(items: Sequence[DocumentNode], structural_parent: str | None) -> None:
        for node in items:
            attributes = dict(node.attributes)
            locator = attributes.get("nec_locator")
            next_parent = structural_parent
            if locator is not None:
                locator = canonical_nec_locator(locator)
                title = attributes.get("nec_title", "")
                depth = 0 if structural_parent is None else (
                    next(
                        (
                            record.depth + 1
                            for record in reversed(records)
                            if record.locator == structural_parent
                        ),
                        nec_locator_depth(structural_parent) + 1,
                    )
                )
                if structural_parent is None:
                    depth = nec_locator_depth(locator)
                records.append(
                    HierarchyRecord(
                        locator=locator,
                        title=title,
                        parent=structural_parent or locator.split(".", 1)[0],
                        order=len(records),
                        depth=depth,
                    )
                )
                next_parent = locator
            visit(node.children, next_parent)

    visit(nodes, None)
    return tuple(records)


def _normalized_title(value: str) -> str:
    return " ".join(value.rstrip(".").casefold().split())


def _duplicates(records: Sequence[HierarchyRecord]) -> set[str]:
    counts = Counter(item.locator for item in records)
    return {locator for locator, count in counts.items() if count > 1}


def compare_hierarchy(
    expected: Sequence[HierarchyRecord],
    actual: Sequence[HierarchyRecord],
) -> HierarchyConformanceReport:
    """Compare hierarchy records without altering either sequence."""

    mismatches: list[HierarchyMismatch] = []
    expected_duplicates = _duplicates(expected)
    actual_duplicates = _duplicates(actual)
    for locator in sorted(expected_duplicates):
        mismatches.append(
            HierarchyMismatch(
                code="duplicate-expected-locator",
                locator=locator,
                message="The reference hierarchy contains a duplicate locator.",
            )
        )
    for locator in sorted(actual_duplicates):
        mismatches.append(
            HierarchyMismatch(
                code="duplicate-actual-locator",
                locator=locator,
                message="The inferred hierarchy contains a duplicate locator.",
            )
        )

    expected_map = {item.locator: item for item in expected}
    actual_map = {item.locator: item for item in actual}
    expected_positions = {item.locator: index for index, item in enumerate(expected)}
    actual_positions = {item.locator: index for index, item in enumerate(actual)}

    for locator in sorted(expected_map.keys() - actual_map.keys()):
        mismatches.append(
            HierarchyMismatch(
                code="missing-locator",
                locator=locator,
                message="The expected locator was not inferred.",
                expected=locator,
            )
        )
    for locator in sorted(actual_map.keys() - expected_map.keys()):
        mismatches.append(
            HierarchyMismatch(
                code="unexpected-locator",
                locator=locator,
                message="The parser inferred a locator absent from the reference.",
                actual=locator,
            )
        )

    for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
        if expected_item.locator != actual_item.locator:
            mismatches.append(
                HierarchyMismatch(
                    code="order-mismatch",
                    locator=expected_item.locator,
                    message="The expected and inferred locator sequences diverge.",
                    expected=f"{index}:{expected_item.locator}",
                    actual=f"{index}:{actual_item.locator}",
                )
            )
            break

    clean_matches = 0
    for locator in sorted(expected_map.keys() & actual_map.keys()):
        expected_item = expected_map[locator]
        actual_item = actual_map[locator]
        locator_mismatch_count = len(mismatches)
        if _normalized_title(expected_item.title) != _normalized_title(actual_item.title):
            mismatches.append(
                HierarchyMismatch(
                    code="title-mismatch",
                    locator=locator,
                    message="The inferred title differs from the reference title.",
                    expected=expected_item.title,
                    actual=actual_item.title,
                )
            )
        if expected_item.parent != actual_item.parent:
            mismatches.append(
                HierarchyMismatch(
                    code="parent-mismatch",
                    locator=locator,
                    message="The inferred parent differs from the reference parent.",
                    expected=expected_item.parent,
                    actual=actual_item.parent,
                )
            )
        if expected_item.depth != actual_item.depth:
            mismatches.append(
                HierarchyMismatch(
                    code="depth-mismatch",
                    locator=locator,
                    message="The inferred structural depth differs from the reference depth.",
                    expected=expected_item.depth,
                    actual=actual_item.depth,
                )
            )
        if expected_positions[locator] != actual_positions[locator]:
            mismatches.append(
                HierarchyMismatch(
                    code="order-mismatch",
                    locator=locator,
                    message="The locator occurs at a different source-order position.",
                    expected=expected_positions[locator],
                    actual=actual_positions[locator],
                )
            )
        if len(mismatches) == locator_mismatch_count:
            clean_matches += 1

    return HierarchyConformanceReport(
        expected_records=len(expected),
        actual_records=len(actual),
        matches=clean_matches,
        mismatches=tuple(mismatches),
    )
