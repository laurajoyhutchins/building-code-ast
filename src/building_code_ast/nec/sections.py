"""Conservative section-level semantic review for NEC ArticleSeed values."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any, Iterable

from ..model import Diagnostic, DiagnosticSeverity, SourceSpan
from .model import (
    DefinitionIndex,
    LanguageCategory,
    LanguageEvidence,
    NecLanguageProfile,
    ReviewedClause,
    ReviewedException,
    ReviewedModality,
    ReviewedNote,
    SectionReview,
    SourceNodeProjection,
    reviewed_clause_id,
    reviewed_exception_id,
    reviewed_note_id,
)
from .references import extract_code_references
from .seed import ArticleSeedView, SeedNode, article_seed_view
from .validation import validate_definition_index, validate_section_review


_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+(?=(?:[A-Z]|\([A-Z0-9]+\)))")
_LEADING_CONDITION_RE = re.compile(r"^\s*(?:if|when|where|unless)\b[^,]*,", re.IGNORECASE)
_TRAILING_CONDITION_RE = re.compile(r"\b(?:if|when|where|unless)\b.*", re.IGNORECASE)
_MODAL_PATTERNS: tuple[tuple[re.Pattern[str], ReviewedModality], ...] = (
    (re.compile(r"\bshall\s+not\s+be\s+required\b", re.IGNORECASE), ReviewedModality.NONREQUIREMENT),
    (re.compile(r"\bshall\s+be\s+permitted\b", re.IGNORECASE), ReviewedModality.PERMISSION),
    (re.compile(r"\bshall\s+not\b", re.IGNORECASE), ReviewedModality.PROHIBITION),
    (re.compile(r"\bshall\b", re.IGNORECASE), ReviewedModality.REQUIREMENT),
    (re.compile(r"\bmay\b", re.IGNORECASE), ReviewedModality.PERMISSION),
)

_TAG_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("authority_approval", re.compile(r"\b(?:approved|acceptable|authority having jurisdiction)\b", re.IGNORECASE)),
    ("examination", re.compile(r"\b(?:examin\w*|judging)\b", re.IGNORECASE)),
    ("identification", re.compile(r"\bidentif\w*\b", re.IGNORECASE)),
    ("installation", re.compile(r"\binstall\w*\b", re.IGNORECASE)),
    ("listing", re.compile(r"\b(?:listed|listing|labeled equipment)\b", re.IGNORECASE)),
    ("connections", re.compile(r"\b(?:connection\w*|connector\w*|terminal\w*|splic\w*)\b", re.IGNORECASE)),
    ("warning", re.compile(r"\b(?:warning|arc[- ]flash)\b", re.IGNORECASE)),
    ("marking", re.compile(r"\b(?:mark\w*|label\w*)\b", re.IGNORECASE)),
    ("working_space", re.compile(r"\bworking\s+space\b", re.IGNORECASE)),
    ("access", re.compile(r"\b(?:access\w*|entrance|egress)\b", re.IGNORECASE)),
    ("guarding", re.compile(r"\bguard\w*\b", re.IGNORECASE)),
    ("illumination", re.compile(r"\b(?:illumination|lighting)\b", re.IGNORECASE)),
)


def _span(source: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start, end, source[start:end])


def _trim(source: str, start: int, end: int, *, punctuation: str = "") -> tuple[int, int]:
    while start < end and source[start].isspace():
        start += 1
    while end > start and (source[end - 1].isspace() or source[end - 1] in punctuation):
        end -= 1
    return start, end


def _section_nodes(view: ArticleSeedView, section_locator: str) -> tuple[SeedNode, ...]:
    start: int | None = None
    for index, node in enumerate(view.nodes):
        label = node.label or ""
        if node.node_type == "section" and (
            label == section_locator or label.startswith(section_locator + " ")
        ):
            start = index
            break
    if start is None:
        raise ValueError(f"section {section_locator} was not found in Article {view.article_number}")

    end = start + 1
    while end < len(view.nodes):
        candidate = view.nodes[end]
        if candidate.node_type in {"section", "heading"}:
            break
        end += 1
    return view.nodes[start:end]


def _project_nodes(
    nodes: tuple[SeedNode, ...],
    source: str,
    article_start: int,
) -> tuple[SourceNodeProjection, ...]:
    projected: list[SourceNodeProjection] = []
    for node in nodes:
        start = node.span.start - article_start
        end = node.span.end - article_start
        projected.append(
            SourceNodeProjection(
                locator=node.locator,
                node_type=node.node_type,
                label=node.label,
                span=_span(source, start, end),
                attributes=node.attributes,
            )
        )
    return tuple(projected)


def _content_bounds(
    node: SeedNode,
    local_source: str,
    article_start: int,
) -> tuple[int, int]:
    start = node.span.start - article_start
    end = node.span.end - article_start
    text = local_source[start:end]
    prefix = node.label or ""
    if node.node_type == "section" and prefix and text.startswith(prefix):
        start += len(prefix)
    elif node.node_type in {"subsection", "list_item"} and prefix and text.startswith(prefix):
        start += len(prefix)
    return _trim(local_source, start, end)


def _sentence_spans(source: str, start: int, end: int) -> tuple[SourceSpan, ...]:
    if start >= end:
        return ()
    text = source[start:end]
    boundaries = [0]
    boundaries.extend(match.end() for match in _SENTENCE_BREAK_RE.finditer(text))
    boundaries.append(len(text))
    spans: list[SourceSpan] = []
    for left, right in zip(boundaries, boundaries[1:]):
        item_start, item_end = _trim(source, start + left, start + right)
        if item_start < item_end:
            spans.append(_span(source, item_start, item_end))
    return tuple(spans)


def _modal(source: str, span: SourceSpan) -> tuple[ReviewedModality, SourceSpan | None]:
    for pattern, modality in _MODAL_PATTERNS:
        match = pattern.search(span.text)
        if match is not None:
            return (
                modality,
                _span(source, span.start + match.start(), span.start + match.end()),
            )
    return ReviewedModality.UNKNOWN, None


def _is_meta_modal(source: str, clause: SourceSpan, modal: SourceSpan) -> bool:
    prefix = source[clause.start : modal.start].casefold()
    return "term" in prefix[-60:] and "use" in prefix[-80:]


def _condition_and_subject(
    source: str,
    clause: SourceSpan,
    modal: SourceSpan,
) -> tuple[SourceSpan | None, SourceSpan | None]:
    prefix_text = source[clause.start : modal.start]
    leading = _LEADING_CONDITION_RE.match(prefix_text)
    subject_start = clause.start
    condition: SourceSpan | None = None
    if leading is not None:
        condition_start = clause.start + leading.start()
        condition_end = clause.start + leading.end() - 1
        condition = _span(source, condition_start, condition_end)
        subject_start = clause.start + leading.end()
    subject_start, subject_end = _trim(source, subject_start, modal.start, punctuation=",")
    subject = _span(source, subject_start, subject_end) if subject_start < subject_end else None
    return condition, subject


def _trailing_condition(source: str, clause: SourceSpan, modal: SourceSpan | None) -> SourceSpan | None:
    search_start = modal.end if modal is not None else clause.start
    match = _TRAILING_CONDITION_RE.search(source[search_start : clause.end])
    if match is None:
        return None
    start = search_start + match.start()
    end = search_start + match.end()
    start, end = _trim(source, start, end, punctuation=".")
    return _span(source, start, end) if start < end else None


def _semantic_tags(text: str) -> tuple[str, ...]:
    return tuple(tag for tag, pattern in _TAG_PATTERNS if pattern.search(text))


def _definition_candidates(definitions: DefinitionIndex | None) -> tuple[tuple[str, str], ...]:
    if definitions is None:
        return ()
    validate_definition_index(definitions)
    candidates: list[tuple[str, str]] = []
    for entry in definitions.entries:
        terms = {entry.canonical_term, entry.display_term}
        terms.update(item.text for item in entry.alternate_terms)
        for term in terms:
            normalized = term.strip()
            if len(normalized) >= 3:
                candidates.append((normalized, entry.definition_id))
    candidates.sort(key=lambda item: (-len(item[0]), item[0].casefold(), item[1]))
    return tuple(candidates)


def _definition_links(clause: SourceSpan, candidates: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for term, definition_id in candidates:
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.IGNORECASE)
        match = pattern.search(clause.text)
        if match is not None:
            matches.append((match.start(), definition_id))
    matches.sort()
    return tuple(dict.fromkeys(definition_id for _, definition_id in matches))


def _clause(
    source: str,
    span: SourceSpan,
    *,
    artifact,
    section_locator: str,
    definition_candidates: tuple[tuple[str, str], ...],
) -> ReviewedClause | None:
    modality, modal_span = _modal(source, span)
    if modal_span is None:
        return None
    if _is_meta_modal(source, span, modal_span):
        return None
    condition, subject = _condition_and_subject(source, span, modal_span)
    predicate_start, predicate_end = _trim(source, modal_span.end, span.end)
    predicate = (
        _span(source, predicate_start, predicate_end)
        if predicate_start < predicate_end
        else None
    )
    return ReviewedClause(
        clause_id=reviewed_clause_id(artifact, section_locator, span.start, span.end),
        modality=modality,
        span=span,
        modal_span=modal_span,
        subject_span=subject,
        predicate_span=predicate,
        condition_span=condition,
        semantic_tags=_semantic_tags(span.text),
        definition_ids=_definition_links(span, definition_candidates),
        references=extract_code_references(source, (span,)),
    )


def _exception(
    source: str,
    span: SourceSpan,
    *,
    artifact,
    section_locator: str,
) -> ReviewedException:
    modality, modal_span = _modal(source, span)
    condition = None
    if modal_span is not None:
        leading, _ = _condition_and_subject(source, span, modal_span)
        condition = leading or _trailing_condition(source, span, modal_span)
    return ReviewedException(
        exception_id=reviewed_exception_id(artifact, section_locator, span.start, span.end),
        span=span,
        modality=modality,
        modal_span=modal_span,
        condition_span=condition,
        references=extract_code_references(source, (span,)),
    )


def build_section_review(
    article_seed: Mapping[str, Any],
    section_locator: str,
    *,
    definitions: DefinitionIndex | None = None,
) -> SectionReview:
    """Build one validated, section-local semantic review."""

    view = article_seed_view(article_seed)
    nodes = _section_nodes(view, section_locator)
    article_start = nodes[0].span.start
    article_end = nodes[-1].span.end
    source = view.source_text[article_start:article_end]
    projected = _project_nodes(nodes, source, article_start)

    label = nodes[0].label or ""
    if not label.startswith(section_locator):
        raise ValueError(f"section {section_locator} label is malformed")
    raw_title = label[len(section_locator) :].strip()
    title = raw_title[:-1] if raw_title.endswith(".") else raw_title
    if not title:
        raise ValueError(f"section {section_locator} has no title")
    title_global = nodes[0].span.text.find(title)
    if title_global < 0:
        raise ValueError(f"section {section_locator} title does not round-trip")
    title_span = _span(source, title_global, title_global + len(title))

    diagnostics: list[Diagnostic] = []
    clauses: list[ReviewedClause] = []
    exceptions: list[ReviewedException] = []
    notes: list[ReviewedNote] = []
    candidates = _definition_candidates(definitions)

    for node, projection in zip(nodes, projected, strict=True):
        if node.node_type == "note":
            if (node.label or "").startswith("Exception") or dict(node.attributes).get("kind") == "exception":
                exceptions.append(
                    _exception(
                        source,
                        projection.span,
                        artifact=view.source_artifact,
                        section_locator=section_locator,
                    )
                )
            else:
                notes.append(
                    ReviewedNote(
                        note_id=reviewed_note_id(
                            view.source_artifact,
                            section_locator,
                            projection.span.start,
                            projection.span.end,
                        ),
                        label=node.label or "Informational Note",
                        span=projection.span,
                        references=extract_code_references(source, (projection.span,)),
                    )
                )
            continue

        if node.node_type == "unsupported":
            diagnostics.append(
                Diagnostic(
                    code="unsupported-section-structure",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "The source node was preserved, but its visual structure was not "
                        "converted into semantic clauses."
                    ),
                    span=projection.span,
                )
            )
            continue

        if len(re.findall(r"\(\d+\)", projection.span.text)) > 1:
            diagnostics.append(
                Diagnostic(
                    code="collapsed-list-items",
                    severity=DiagnosticSeverity.WARNING,
                    message=(
                        "Multiple list markers occur in one source node; clause review "
                        "preserves the block without claiming item-level boundaries."
                    ),
                    span=projection.span,
                )
            )

        content_start, content_end = _content_bounds(node, source, article_start)
        for sentence in _sentence_spans(source, content_start, content_end):
            reviewed = _clause(
                source,
                sentence,
                artifact=view.source_artifact,
                section_locator=section_locator,
                definition_candidates=candidates,
            )
            if reviewed is not None:
                clauses.append(reviewed)

    if not clauses and section_locator != "90.5":
        diagnostics.append(
            Diagnostic(
                code="no-reviewed-normative-clause",
                severity=DiagnosticSeverity.INFO,
                message="No supported normative modal clause was identified in the section.",
                span=_span(source, 0, len(source)),
            )
        )

    review = SectionReview(
        source_text=source,
        source_artifact=view.source_artifact,
        article_locator=view.article_locator,
        article_start=article_start,
        article_end=article_end,
        section_locator=section_locator,
        title=title,
        title_span=title_span,
        source_nodes=projected,
        clauses=tuple(clauses),
        exceptions=tuple(exceptions),
        notes=tuple(notes),
        references=extract_code_references(source, (_span(source, 0, len(source)),)),
        diagnostics=tuple(diagnostics),
    )
    validate_section_review(review)
    return review


def _language_evidence(
    review: SectionReview,
    phrase: str,
    category: LanguageCategory,
) -> LanguageEvidence:
    match = re.search(re.escape(phrase), review.source_text, re.IGNORECASE)
    if match is None:
        raise ValueError(
            f"section {review.section_locator} does not contain required language evidence {phrase!r}"
        )
    return LanguageEvidence(
        category=category,
        phrase=review.source_text[match.start() : match.end()],
        span=_span(review.source_text, match.start(), match.end()),
    )


def derive_language_profile(review: SectionReview) -> NecLanguageProfile:
    """Derive the first NEC modal-language profile from reviewed Section 90.5."""

    if review.section_locator != "90.5":
        raise ValueError("NEC language profile must be derived from section 90.5")
    evidence = (
        _language_evidence(review, "shall or shall not", LanguageCategory.MANDATORY),
        _language_evidence(review, "shall be permitted", LanguageCategory.PERMISSIVE),
        _language_evidence(review, "shall not be required", LanguageCategory.PERMISSIVE),
        _language_evidence(review, "informational notes", LanguageCategory.EXPLANATORY),
        _language_evidence(review, "nonmandatory", LanguageCategory.NONMANDATORY),
    )
    return NecLanguageProfile(
        source_locator=review.section_locator,
        mandatory_phrases=("shall", "shall not"),
        permissive_phrases=("shall be permitted", "shall not be required"),
        explanatory_markers=("informational note",),
        nonmandatory_markers=("nonmandatory",),
        evidence=evidence,
    )
