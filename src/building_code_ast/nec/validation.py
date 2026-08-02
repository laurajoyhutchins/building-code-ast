"""Validation for NEC definition indexes and section reviews."""

from __future__ import annotations

from ..model import SourceSpan
from .model import (
    DEFINITION_INDEX_VERSION,
    SECTION_REVIEW_VERSION,
    DefinitionIndex,
    SectionReview,
    definition_entry_id,
    reviewed_clause_id,
    reviewed_exception_id,
    reviewed_note_id,
)


def _validate_span(source: str, span: SourceSpan, label: str) -> None:
    if span.start < 0 or span.end < span.start or span.end > len(source):
        raise ValueError(f"{label} span is outside the source text")
    if source[span.start : span.end] != span.text:
        raise ValueError(f"{label} span text does not match the source text")


def _contained(parent: SourceSpan, child: SourceSpan, label: str) -> None:
    if child.start < parent.start or child.end > parent.end:
        raise ValueError(f"{label} span is outside its parent evidence")


def validate_definition_index(index: DefinitionIndex) -> None:
    if index.index_version != DEFINITION_INDEX_VERSION:
        raise ValueError(f"definition index version must be {DEFINITION_INDEX_VERSION}")
    if not index.source_text:
        raise ValueError("definition index source_text must not be empty")
    if not index.source_artifact.artifact_id.strip():
        raise ValueError("definition index artifact_id must not be empty")
    if not index.source_artifact.edition_id.strip():
        raise ValueError("definition index edition_id must not be empty")
    if index.article_locator != "article:100":
        raise ValueError("definition index article_locator must be 'article:100'")

    previous_end = -1
    ids: set[str] = set()
    locators: set[str] = set()
    for entry_index, entry in enumerate(index.entries):
        label = f"definition entry[{entry_index}]"
        if not entry.source_locator.strip():
            raise ValueError(f"{label} source_locator must not be empty")
        expected_id = definition_entry_id(index.source_artifact, entry.source_locator)
        if entry.definition_id != expected_id:
            raise ValueError(f"{label} does not match its deterministic identity")
        if entry.definition_id in ids:
            raise ValueError(f"duplicate definition id: {entry.definition_id}")
        if entry.source_locator in locators:
            raise ValueError(f"duplicate definition source locator: {entry.source_locator}")
        ids.add(entry.definition_id)
        locators.add(entry.source_locator)

        _validate_span(index.source_text, entry.source_span, f"{label} source")
        if entry.source_span.start < previous_end:
            raise ValueError("definition entries must be source ordered and non-overlapping")
        previous_end = entry.source_span.end

        _validate_span(index.source_text, entry.term_span, f"{label} term")
        _contained(entry.source_span, entry.term_span, f"{label} term")
        if entry.term_span.text != entry.display_term:
            raise ValueError(f"{label} display_term must equal its exact term span")
        if not entry.canonical_term.strip():
            raise ValueError(f"{label} canonical_term must not be empty")

        for item_index, alternate in enumerate(entry.alternate_terms):
            _validate_span(index.source_text, alternate, f"{label} alternate[{item_index}]")
            _contained(entry.term_span, alternate, f"{label} alternate[{item_index}]")

        for item_index, qualifier in enumerate(entry.qualifiers):
            _validate_span(index.source_text, qualifier.span, f"{label} qualifier[{item_index}]")
            _contained(entry.term_span, qualifier.span, f"{label} qualifier[{item_index}]")
            if not qualifier.text.strip():
                raise ValueError(f"{label} qualifier[{item_index}] text must not be empty")

        for item_index, fragment in enumerate(entry.body_fragments):
            _validate_span(index.source_text, fragment.span, f"{label} body fragment[{item_index}]")
            _contained(entry.source_span, fragment.span, f"{label} body fragment[{item_index}]")
            if not fragment.node_locator.strip() or not fragment.node_type.strip():
                raise ValueError(f"{label} body fragment metadata must not be empty")

        for item_index, note in enumerate(entry.notes):
            _validate_span(index.source_text, note.span, f"{label} note[{item_index}]")
            _contained(entry.source_span, note.span, f"{label} note[{item_index}]")

        for item_index, panel in enumerate(entry.code_making_panels):
            _validate_span(index.source_text, panel, f"{label} panel[{item_index}]")
            _contained(entry.source_span, panel, f"{label} panel[{item_index}]")

        for item_index, reference in enumerate(entry.references):
            _validate_span(index.source_text, reference.span, f"{label} reference[{item_index}]")
            _contained(entry.source_span, reference.span, f"{label} reference[{item_index}]")

        for item_index, diagnostic in enumerate(entry.diagnostics):
            if diagnostic.span is not None:
                _validate_span(
                    index.source_text,
                    diagnostic.span,
                    f"{label} diagnostic[{item_index}]",
                )
                _contained(entry.source_span, diagnostic.span, f"{label} diagnostic[{item_index}]")

    for item_index, diagnostic in enumerate(index.diagnostics):
        if diagnostic.span is not None:
            _validate_span(index.source_text, diagnostic.span, f"index diagnostic[{item_index}]")


def validate_section_review(review: SectionReview) -> None:
    if review.review_version != SECTION_REVIEW_VERSION:
        raise ValueError(f"section review version must be {SECTION_REVIEW_VERSION}")
    if not review.source_text:
        raise ValueError("section review source_text must not be empty")
    if not review.source_artifact.artifact_id.strip():
        raise ValueError("section review artifact_id must not be empty")
    if not review.source_artifact.edition_id.strip():
        raise ValueError("section review edition_id must not be empty")
    if not review.article_locator.strip() or not review.section_locator.strip():
        raise ValueError("section review locators must not be empty")
    if review.article_start < 0 or review.article_end < review.article_start:
        raise ValueError("section review article span is invalid")
    if review.article_end - review.article_start != len(review.source_text):
        raise ValueError("section review article span length must equal source_text length")

    _validate_span(review.source_text, review.title_span, "section title")
    if review.title_span.text != review.title:
        raise ValueError("section title must equal its exact title span")

    if not review.source_nodes:
        raise ValueError("section review must contain at least one source node")
    previous_end = -1
    node_locators: set[str] = set()
    for node_index, node in enumerate(review.source_nodes):
        label = f"source node[{node_index}]"
        if node.locator in node_locators:
            raise ValueError(f"duplicate section source node locator: {node.locator}")
        node_locators.add(node.locator)
        _validate_span(review.source_text, node.span, label)
        if node.span.start < previous_end:
            raise ValueError("section source nodes must be ordered and non-overlapping")
        previous_end = node.span.end
    if review.source_nodes[0].span.start != 0:
        raise ValueError("first section source node must start at zero")
    if review.source_nodes[-1].span.end != len(review.source_text):
        raise ValueError("last section source node must end at source_text length")

    clause_ids: set[str] = set()
    for clause_index, clause in enumerate(review.clauses):
        label = f"clause[{clause_index}]"
        _validate_span(review.source_text, clause.span, label)
        expected_id = reviewed_clause_id(
            review.source_artifact,
            review.section_locator,
            clause.span.start,
            clause.span.end,
        )
        if clause.clause_id != expected_id:
            raise ValueError(f"{label} does not match its deterministic identity")
        if clause.clause_id in clause_ids:
            raise ValueError(f"duplicate clause id: {clause.clause_id}")
        clause_ids.add(clause.clause_id)
        for part_name, part in (
            ("modal", clause.modal_span),
            ("subject", clause.subject_span),
            ("predicate", clause.predicate_span),
            ("condition", clause.condition_span),
        ):
            if part is not None:
                _validate_span(review.source_text, part, f"{label} {part_name}")
                _contained(clause.span, part, f"{label} {part_name}")
        for reference_index, reference in enumerate(clause.references):
            _validate_span(
                review.source_text,
                reference.span,
                f"{label} reference[{reference_index}]",
            )
            _contained(clause.span, reference.span, f"{label} reference[{reference_index}]")

    exception_ids: set[str] = set()
    for exception_index, exception in enumerate(review.exceptions):
        label = f"exception[{exception_index}]"
        _validate_span(review.source_text, exception.span, label)
        expected_id = reviewed_exception_id(
            review.source_artifact,
            review.section_locator,
            exception.span.start,
            exception.span.end,
        )
        if exception.exception_id != expected_id:
            raise ValueError(f"{label} does not match its deterministic identity")
        if exception.exception_id in exception_ids:
            raise ValueError(f"duplicate exception id: {exception.exception_id}")
        exception_ids.add(exception.exception_id)
        for part_name, part in (
            ("modal", exception.modal_span),
            ("condition", exception.condition_span),
        ):
            if part is not None:
                _validate_span(review.source_text, part, f"{label} {part_name}")
                _contained(exception.span, part, f"{label} {part_name}")
        for reference_index, reference in enumerate(exception.references):
            _validate_span(
                review.source_text,
                reference.span,
                f"{label} reference[{reference_index}]",
            )
            _contained(exception.span, reference.span, f"{label} reference[{reference_index}]")

    note_ids: set[str] = set()
    for note_index, note in enumerate(review.notes):
        label = f"note[{note_index}]"
        _validate_span(review.source_text, note.span, label)
        expected_id = reviewed_note_id(
            review.source_artifact,
            review.section_locator,
            note.span.start,
            note.span.end,
        )
        if note.note_id != expected_id:
            raise ValueError(f"{label} does not match its deterministic identity")
        if note.note_id in note_ids:
            raise ValueError(f"duplicate note id: {note.note_id}")
        note_ids.add(note.note_id)
        for reference_index, reference in enumerate(note.references):
            _validate_span(
                review.source_text,
                reference.span,
                f"{label} reference[{reference_index}]",
            )
            _contained(note.span, reference.span, f"{label} reference[{reference_index}]")

    for reference_index, reference in enumerate(review.references):
        _validate_span(review.source_text, reference.span, f"section reference[{reference_index}]")

    for diagnostic_index, diagnostic in enumerate(review.diagnostics):
        if diagnostic.span is not None:
            _validate_span(
                review.source_text,
                diagnostic.span,
                f"section diagnostic[{diagnostic_index}]",
            )
