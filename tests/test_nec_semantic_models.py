from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentSourceArtifact
from building_code_ast.model import SourceSpan
from building_code_ast.nec.model import (
    CodeReference,
    CodeReferenceKind,
    DefinitionEntry,
    DefinitionFragment,
    DefinitionFragmentKind,
    DefinitionIndex,
    DefinitionQualifier,
    DefinitionQualifierKind,
    ReviewedClause,
    ReviewedException,
    ReviewedModality,
    ReviewedNote,
    SectionReview,
    SourceNodeProjection,
    definition_entry_id,
    reviewed_clause_id,
    reviewed_exception_id,
    reviewed_note_id,
)
from building_code_ast.nec.validation import (
    validate_definition_index,
    validate_section_review,
)


ARTIFACT = DocumentSourceArtifact(
    artifact_id="synthetic:electrical-code",
    edition_id="test-edition",
)


class DefinitionIndexModelTests(unittest.TestCase):
    def test_definition_index_round_trips_exact_spans_and_identity(self) -> None:
        source = (
            "Synthetic Device (SD) (as applied to controls). "
            "A project-authored device definition. (CMP-99)\n\n"
            "Informational Note: This note is synthetic."
        )
        display = "Synthetic Device (SD) (as applied to controls)"
        entry = DefinitionEntry(
            definition_id=definition_entry_id(ARTIFACT, "article:100/block:0001"),
            source_locator="article:100/block:0001",
            display_term=display,
            canonical_term="Synthetic Device",
            term_span=SourceSpan(0, len(display), display),
            alternate_terms=(SourceSpan(18, 20, "SD"),),
            qualifiers=(
                DefinitionQualifier(
                    kind=DefinitionQualifierKind.APPLICABILITY,
                    text="controls",
                    span=SourceSpan(23, 45, "as applied to controls"),
                ),
            ),
            body_fragments=(
                DefinitionFragment(
                    kind=DefinitionFragmentKind.BODY,
                    node_locator="article:100/block:0001",
                    node_type="definition_entry",
                    span=SourceSpan(48, 85, "A project-authored device definition."),
                ),
            ),
            notes=(
                DefinitionFragment(
                    kind=DefinitionFragmentKind.NOTE,
                    node_locator="article:100/block:0002",
                    node_type="note",
                    span=SourceSpan(96, len(source), "Informational Note: This note is synthetic."),
                ),
            ),
            code_making_panels=(SourceSpan(86, 94, "(CMP-99)"),),
            references=(),
            source_span=SourceSpan(0, len(source), source),
        )
        index = DefinitionIndex(
            source_text=source,
            source_artifact=ARTIFACT,
            article_locator="article:100",
            entries=(entry,),
        )

        validate_definition_index(index)
        payload = index.to_dict()

        self.assertEqual(payload["index_version"], "0.1.0")
        self.assertEqual(payload["entries"][0]["definition_id"], entry.definition_id)
        self.assertEqual(payload["entries"][0]["alternate_terms"][0]["text"], "SD")

    def test_definition_validation_rejects_mismatched_source_text(self) -> None:
        source = "Synthetic Term. Body."
        entry = DefinitionEntry(
            definition_id=definition_entry_id(ARTIFACT, "article:100/block:0001"),
            source_locator="article:100/block:0001",
            display_term="Synthetic Term",
            canonical_term="Synthetic Term",
            term_span=SourceSpan(0, 14, "Synthetic Term"),
            alternate_terms=(),
            qualifiers=(),
            body_fragments=(
                DefinitionFragment(
                    kind=DefinitionFragmentKind.BODY,
                    node_locator="article:100/block:0001",
                    node_type="definition_entry",
                    span=SourceSpan(16, 21, "wrong"),
                ),
            ),
            notes=(),
            code_making_panels=(),
            references=(),
            source_span=SourceSpan(0, len(source), source),
        )
        index = DefinitionIndex(source, ARTIFACT, "article:100", (entry,))

        with self.assertRaisesRegex(ValueError, "body fragment"):
            validate_definition_index(index)


class SectionReviewModelTests(unittest.TestCase):
    def test_section_review_uses_local_spans_and_deterministic_ids(self) -> None:
        source = (
            "120.1 Synthetic Rule. Equipment shall be approved.\n\n"
            "Exception: Approval shall not be required for test fixtures.\n\n"
            "Informational Note: The example is project-authored."
        )
        clause_start = source.index("Equipment")
        clause_end = source.index("\n\n")
        modal_start = source.index("shall")
        modal_end = modal_start + len("shall")
        exception_start = source.index("Exception:")
        exception_end = source.index("\n\n", exception_start)
        note_start = source.index("Informational Note:")
        review = SectionReview(
            source_text=source,
            source_artifact=ARTIFACT,
            article_locator="article:120",
            article_start=500,
            article_end=500 + len(source),
            section_locator="120.1",
            title="Synthetic Rule",
            title_span=SourceSpan(6, 20, "Synthetic Rule"),
            source_nodes=(
                SourceNodeProjection(
                    locator="article:120/block:0001",
                    node_type="section",
                    label="120.1 Synthetic Rule.",
                    span=SourceSpan(0, clause_end, source[:clause_end]),
                    attributes=(),
                ),
                SourceNodeProjection(
                    locator="article:120/block:0002",
                    node_type="note",
                    label="Exception",
                    span=SourceSpan(exception_start, exception_end, source[exception_start:exception_end]),
                    attributes=(("kind", "exception"),),
                ),
                SourceNodeProjection(
                    locator="article:120/block:0003",
                    node_type="note",
                    label="Informational Note",
                    span=SourceSpan(note_start, len(source), source[note_start:]),
                    attributes=(),
                ),
            ),
            clauses=(
                ReviewedClause(
                    clause_id=reviewed_clause_id(ARTIFACT, "120.1", clause_start, clause_end),
                    modality=ReviewedModality.REQUIREMENT,
                    span=SourceSpan(clause_start, clause_end, source[clause_start:clause_end]),
                    modal_span=SourceSpan(modal_start, modal_end, "shall"),
                    subject_span=SourceSpan(clause_start, modal_start - 1, "Equipment"),
                    predicate_span=SourceSpan(modal_end + 1, clause_end, "be approved."),
                    condition_span=None,
                    semantic_tags=("authority_approval",),
                    definition_ids=("necdef:synthetic",),
                    references=(),
                ),
            ),
            exceptions=(
                ReviewedException(
                    exception_id=reviewed_exception_id(
                        ARTIFACT, "120.1", exception_start, exception_end
                    ),
                    span=SourceSpan(
                        exception_start,
                        exception_end,
                        source[exception_start:exception_end],
                    ),
                    modality=ReviewedModality.NONREQUIREMENT,
                    modal_span=SourceSpan(
                        source.index("shall not be required"),
                        source.index("shall not be required") + len("shall not be required"),
                        "shall not be required",
                    ),
                    condition_span=None,
                    references=(),
                ),
            ),
            notes=(
                ReviewedNote(
                    note_id=reviewed_note_id(ARTIFACT, "120.1", note_start, len(source)),
                    label="Informational Note",
                    span=SourceSpan(note_start, len(source), source[note_start:]),
                    references=(),
                ),
            ),
            references=(
                CodeReference(
                    kind=CodeReferenceKind.SECTION,
                    target="120.1",
                    span=SourceSpan(0, 5, "120.1"),
                ),
            ),
        )

        validate_section_review(review)
        payload = review.to_dict()

        self.assertEqual(payload["review_version"], "0.1.0")
        self.assertEqual(payload["article_span"], {"start": 500, "end": 500 + len(source)})
        self.assertEqual(payload["clauses"][0]["modality"], "requirement")

    def test_section_validation_rejects_wrong_clause_identity(self) -> None:
        source = "120.1 Synthetic Rule. Equipment shall be approved."
        clause_start = source.index("Equipment")
        review = SectionReview(
            source_text=source,
            source_artifact=ARTIFACT,
            article_locator="article:120",
            article_start=0,
            article_end=len(source),
            section_locator="120.1",
            title="Synthetic Rule",
            title_span=SourceSpan(6, 20, "Synthetic Rule"),
            source_nodes=(
                SourceNodeProjection(
                    locator="article:120/block:0001",
                    node_type="section",
                    label="120.1 Synthetic Rule.",
                    span=SourceSpan(0, len(source), source),
                    attributes=(),
                ),
            ),
            clauses=(
                ReviewedClause(
                    clause_id="clause:wrong",
                    modality=ReviewedModality.REQUIREMENT,
                    span=SourceSpan(clause_start, len(source), source[clause_start:]),
                    modal_span=SourceSpan(source.index("shall"), source.index("shall") + 5, "shall"),
                    subject_span=None,
                    predicate_span=None,
                    condition_span=None,
                    semantic_tags=(),
                    definition_ids=(),
                    references=(),
                ),
            ),
            exceptions=(),
            notes=(),
            references=(),
        )

        with self.assertRaisesRegex(ValueError, "deterministic identity"):
            validate_section_review(review)


if __name__ == "__main__":
    unittest.main()
