"""Conservative Article 100 definition extraction from private ArticleSeed JSON."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .model import (
    DefinitionEntry,
    DefinitionFragment,
    DefinitionFragmentKind,
    DefinitionIndex,
    DefinitionQualifier,
    DefinitionQualifierKind,
    definition_entry_id,
)
from .references import extract_code_references
from .seed import ArticleSeedView, SeedNode, article_seed_view
from .validation import validate_definition_index


_GROUP_RE = re.compile(r"\((?P<paren>[^()]*)\)|\[(?P<bracket>[^\[\]]*)\]")
_PANEL_RE = re.compile(r"\(CMP-\d+\)")
def _span(source: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start, end, source[start:end])


def _is_definition_start(node: SeedNode) -> bool:
    if node.node_type != "definition_entry":
        return False
    if node.label is None or not node.label.strip():
        return False
    prefix = node.label + "."
    if not node.span.text.startswith(prefix):
        return True
    tail = node.span.text[len(prefix) :]
    tail = re.sub(r"(?:\s*\(CMP-\d+\)\s*)+$", "", tail)
    return bool(tail.strip())


def _heading_parts(
    source: str,
    node: SeedNode,
) -> tuple[str, SourceSpan, tuple[SourceSpan, ...], tuple[DefinitionQualifier, ...]]:
    if node.label is None or not node.label.strip():
        raise ValueError(f"definition node {node.locator!r} has no label")
    display = node.label
    node_text = node.span.text
    if not node_text.startswith(display + "."):
        raise ValueError(f"definition node {node.locator!r} does not begin with its label")

    term_span = _span(source, node.span.start, node.span.start + len(display))
    alternates: list[SourceSpan] = []
    qualifiers: list[DefinitionQualifier] = []
    for match in _GROUP_RE.finditer(display):
        content = match.group("paren") if match.group("paren") is not None else match.group("bracket")
        assert content is not None
        content_start = node.span.start + match.start() + 1
        content_end = content_start + len(content)
        content_span = _span(source, content_start, content_end)
        normalized = content.strip()
        lowered = normalized.casefold()
        if lowered.startswith("as applied to "):
            qualifiers.append(
                DefinitionQualifier(
                    kind=DefinitionQualifierKind.APPLICABILITY,
                    text=normalized[len("as applied to ") :].strip(),
                    span=content_span,
                )
            )
        elif any(character.isdigit() for character in normalized):
            qualifiers.append(
                DefinitionQualifier(
                    kind=DefinitionQualifierKind.SCOPE,
                    text=normalized,
                    span=content_span,
                )
            )
        else:
            alternates.append(content_span)

    canonical = _GROUP_RE.sub("", display)
    canonical = " ".join(canonical.split())
    if not canonical:
        raise ValueError(f"definition node {node.locator!r} has no canonical term")
    return canonical, term_span, tuple(alternates), tuple(qualifiers)


def _panels(source: str, span: SourceSpan) -> tuple[SourceSpan, ...]:
    return tuple(
        _span(source, span.start + match.start(), span.start + match.end())
        for match in _PANEL_RE.finditer(span.text)
    )


def _trim_trailing_panels(source: str, span: SourceSpan) -> SourceSpan | None:
    text = span.text
    end = len(text)
    while True:
        match = re.search(r"\s*\(CMP-\d+\)\s*$", text[:end])
        if match is None:
            break
        end = match.start()
    while end > 0 and text[end - 1].isspace():
        end -= 1
    if end <= 0:
        return None
    return _span(source, span.start, span.start + end)


def _fragment_kind(node: SeedNode, *, initial: bool) -> DefinitionFragmentKind:
    if initial:
        return DefinitionFragmentKind.BODY
    if node.node_type == "list_item":
        return DefinitionFragmentKind.LIST_ITEM
    return DefinitionFragmentKind.CONTINUATION


def _entry(
    view: ArticleSeedView,
    nodes: tuple[SeedNode, ...],
) -> DefinitionEntry:
    first = nodes[0]
    canonical, term_span, alternates, qualifiers = _heading_parts(view.source_text, first)
    diagnostics: list[Diagnostic] = []
    panels: list[SourceSpan] = []
    body_fragments: list[DefinitionFragment] = []
    notes: list[DefinitionFragment] = []

    for index, node in enumerate(nodes):
        if node.node_type == "note" and (node.label or "").startswith("Informational Note"):
            notes.append(
                DefinitionFragment(
                    kind=DefinitionFragmentKind.NOTE,
                    node_locator=node.locator,
                    node_type=node.node_type,
                    span=node.span,
                )
            )
            continue

        fragment_span = node.span
        if index == 0:
            body_start = node.span.start + len(first.label or "") + 1
            while body_start < node.span.end and view.source_text[body_start].isspace():
                body_start += 1
            fragment_span = _span(view.source_text, body_start, node.span.end)

        panels.extend(_panels(view.source_text, fragment_span))
        trimmed = _trim_trailing_panels(view.source_text, fragment_span)
        if trimmed is not None:
            body_fragments.append(
                DefinitionFragment(
                    kind=_fragment_kind(node, initial=index == 0),
                    node_locator=node.locator,
                    node_type=node.node_type,
                    span=trimmed,
                )
            )
        if node.node_type not in {
            "definition_entry",
            "paragraph",
            "list_item",
            "subsection",
        }:
            diagnostics.append(
                Diagnostic(
                    code="unclassified-definition-fragment",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "The source fragment was preserved as a continuation, but its "
                        "structural role was not recognized as ordinary definition prose."
                    ),
                    span=node.span,
                )
            )

    if not body_fragments:
        diagnostics.append(
            Diagnostic(
                code="definition-body-empty",
                severity=DiagnosticSeverity.WARNING,
                message="No non-note definition body fragment was identified.",
                span=first.span,
            )
        )

    source_span = _span(view.source_text, first.span.start, nodes[-1].span.end)
    evidence_spans = [item.span for item in body_fragments]
    evidence_spans.extend(item.span for item in notes)
    references = extract_code_references(view.source_text, evidence_spans)
    return DefinitionEntry(
        definition_id=definition_entry_id(view.source_artifact, first.locator),
        source_locator=first.locator,
        display_term=first.label or "",
        canonical_term=canonical,
        term_span=term_span,
        alternate_terms=alternates,
        qualifiers=qualifiers,
        body_fragments=tuple(body_fragments),
        notes=tuple(notes),
        code_making_panels=tuple(sorted(panels, key=lambda item: item.start)),
        references=references,
        source_span=source_span,
        diagnostics=tuple(diagnostics),
    )


def build_definition_index(article_seed: Mapping[str, Any]) -> DefinitionIndex:
    """Build a validated structured definition index for Article 100."""

    view = article_seed_view(article_seed, expected_article="100")
    entries: list[DefinitionEntry] = []
    index = 0
    while index < len(view.nodes):
        node = view.nodes[index]
        if not _is_definition_start(node):
            index += 1
            continue
        end = index + 1
        while end < len(view.nodes):
            candidate = view.nodes[end]
            if candidate.node_type in {"heading", "section"} or _is_definition_start(candidate):
                break
            end += 1
        entries.append(_entry(view, view.nodes[index:end]))
        index = end

    if not entries:
        raise ValueError("Article 100 contains no definition_entry nodes")
    result = DefinitionIndex(
        source_text=view.source_text,
        source_artifact=view.source_artifact,
        article_locator=view.article_locator,
        entries=tuple(entries),
    )
    validate_definition_index(result)
    return result
