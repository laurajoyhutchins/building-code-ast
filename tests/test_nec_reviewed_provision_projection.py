from __future__ import annotations

import unittest

from building_code_ast.document_model import DocumentSourceArtifact
from building_code_ast.model import Modality, SourceSpan
from building_code_ast.nec.model import (
    CodeReference,
    CodeReferenceKind,
    ReviewedClause,
    ReviewedModality,
    SectionReview,
    SourceNodeProjection,
    reviewed_clause_id,
)
from building_code_ast.nec.provision_projection import (
    SemanticProjectionState,
    project_reviewed_clause,
)


def _span(source: str, text: str, start: int = 0) -> SourceSpan:
    left = source.index(text, start)
    return SourceSpan(left, left + len(text), text)


def _review() -> SectionReview:
    source = (
        "110.26 Synthetic Working Space. "
        "Equipment shall comply with Table 110.26(A)(1)."
    )
    artifact = DocumentSourceArtifact(
        artifact_id="synthetic-nec",
        edition_id="NFPA-70-synthetic",
    )
    clause_span = _span(source, "Equipment shall comply with Table 110.26(A)(1).")
    modal_span = _span(source, "shall", clause_span.start)
    subject_span = _span(source, "Equipment", clause_span.start)
    predicate_span = _span(source, "comply with Table 110.26(A)(1).", clause_span.start)
    reference_span = _span(source, "110.26(A)(1)", clause_span.start)
    reference = CodeReference(
        CodeReferenceKind.TABLE,
        "110.26(A)(1)",
        reference_span,
    )
    clause = ReviewedClause(
        clause_id=reviewed_clause_id(
            artifact,
            "110.26",
            clause_span.start,
            clause_span.end,
        ),
        modality=ReviewedModality.REQUIREMENT,
        span=clause_span,
        modal_span=modal_span,
        subject_span=subject_span,
        predicate_span=predicate_span,
        condition_span=None,
        semantic_tags=("working_space",),
        definition_ids=(),
        references=(reference,),
    )
    title_span = _span(source, "Synthetic Working Space")
    return SectionReview(
        source_text=source,
        source_artifact=artifact,
        article_locator="110",
        article_start=1000,
        article_end=1000 + len(source),
        section_locator="110.26",
        title="Synthetic Working Space",
        title_span=title_span,
        source_nodes=(
            SourceNodeProjection(
                locator="110.26",
                node_type="section",
                label="110.26 Synthetic Working Space.",
                span=SourceSpan(0, len(source), source),
                attributes=(),
            ),
        ),
        clauses=(clause,),
        exceptions=(),
        notes=(),
        references=(reference,),
    )


class ReviewedProvisionProjectionTests(unittest.TestCase):
    def test_reviewed_table_reference_becomes_inspectable_dependency(self) -> None:
        review = _review()
        projection = project_reviewed_clause(review, review.clauses[0].clause_id)

        self.assertIs(projection.state, SemanticProjectionState.REVIEWED)
        self.assertEqual(projection.provision.modality, Modality.REQUIREMENT)
        self.assertEqual(projection.provision.subject, "Equipment")
        self.assertEqual(projection.provision.action.text, "comply with Table 110.26(A)(1).")
        self.assertEqual(len(projection.dependencies), 1)
        dependency = projection.dependencies[0]
        self.assertIs(dependency.kind, CodeReferenceKind.TABLE)
        self.assertEqual(dependency.target, "110.26(A)(1)")
        self.assertEqual(
            projection.provision.source_text[
                dependency.span.start : dependency.span.end
            ],
            dependency.span.text,
        )
        self.assertEqual(
            projection.source_artifact.to_dict(),
            review.source_artifact.to_dict(),
        )

    def test_reviewed_condition_fails_closed_when_generic_shape_is_unknown(self) -> None:
        review = _review()
        clause = review.clauses[0]
        conditioned = ReviewedClause(
            clause_id=clause.clause_id,
            modality=clause.modality,
            span=clause.span,
            modal_span=clause.modal_span,
            subject_span=clause.subject_span,
            predicate_span=clause.predicate_span,
            condition_span=clause.subject_span,
            semantic_tags=clause.semantic_tags,
            definition_ids=clause.definition_ids,
            references=clause.references,
        )
        review = SectionReview(
            source_text=review.source_text,
            source_artifact=review.source_artifact,
            article_locator=review.article_locator,
            article_start=review.article_start,
            article_end=review.article_end,
            section_locator=review.section_locator,
            title=review.title,
            title_span=review.title_span,
            source_nodes=review.source_nodes,
            clauses=(conditioned,),
            exceptions=review.exceptions,
            notes=review.notes,
            references=review.references,
        )
        projection = project_reviewed_clause(review, conditioned.clause_id)

        self.assertIsNone(projection.provision.condition)
        self.assertEqual(
            [item.code for item in projection.provision.diagnostics],
            ["reviewed-condition-unprojected"],
        )


if __name__ == "__main__":
    unittest.main()
