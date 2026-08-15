"""Source-safe projection from reviewed NEC clauses into generic provision AST values.

The projection preserves the reviewed clause as the semantic authority. It does
not reparses protected source text or infer relationships that were not already
established by ``SectionReview``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..model import (
    AST_VERSION,
    Action,
    Diagnostic,
    DiagnosticSeverity,
    Modality,
    ProvisionAst,
    SourceArtifact,
    SourceSpan,
)
from ..validation import validate_ast
from .model import CodeReference, ReviewedClause, ReviewedModality, SectionReview
from .validation import validate_section_review


REVIEWED_PROVISION_PROJECTION_VERSION = "0.1.0"


class SemanticProjectionState(StrEnum):
    GENERATED = "generated"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class ReviewedProvisionProjection:
    source_artifact: Any
    section_locator: str
    clause_id: str
    state: SemanticProjectionState
    provision: ProvisionAst
    dependencies: tuple[CodeReference, ...]
    projection_version: str = field(
        default=REVIEWED_PROVISION_PROJECTION_VERSION,
        init=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "projection_version": self.projection_version,
            "type": "nec_reviewed_provision_projection",
            "state": self.state.value,
            "source_artifact": self.source_artifact.to_dict(),
            "section_locator": self.section_locator,
            "clause_id": self.clause_id,
            "provision_ast_version": AST_VERSION,
            "provision": self.provision.to_dict(),
            "dependencies": [item.to_dict() for item in self.dependencies],
        }


def _local_span(source: str, clause: ReviewedClause, span: SourceSpan) -> SourceSpan:
    if span.start < clause.span.start or span.end > clause.span.end:
        raise ValueError("reviewed evidence span is outside the selected clause")
    start = span.start - clause.span.start
    end = span.end - clause.span.start
    local = SourceSpan(start, end, source[start:end])
    if local.text != span.text:
        raise ValueError("reviewed evidence does not round-trip into the selected clause")
    return local


def _modality(clause: ReviewedClause) -> tuple[Modality, SourceSpan | None]:
    mapping = {
        ReviewedModality.REQUIREMENT: Modality.REQUIREMENT,
        ReviewedModality.PROHIBITION: Modality.PROHIBITION,
        ReviewedModality.PERMISSION: Modality.PERMISSION,
    }
    if clause.modality in mapping:
        if clause.modal_span is None:
            raise ValueError("reviewed recognized modality is missing evidence")
        return mapping[clause.modality], clause.modal_span
    if clause.modality is ReviewedModality.UNKNOWN:
        return Modality.UNKNOWN, None
    raise ValueError(
        f"reviewed modality {clause.modality.value!r} has no faithful generic Provision AST mapping"
    )


def project_reviewed_clause(
    review: SectionReview,
    clause_id: str,
) -> ReviewedProvisionProjection:
    """Project one reviewed clause without reinterpreting source expression.

    General section, article, and table references are exposed as dependency
    relationships beside the generic Provision AST. Structured conditions are
    only emitted when the reviewed contract already has an equivalent generic
    representation; otherwise the exact condition evidence remains diagnostic.
    """

    validate_section_review(review)
    clause = next((item for item in review.clauses if item.clause_id == clause_id), None)
    if clause is None:
        raise ValueError(f"reviewed clause {clause_id!r} was not found")
    if clause.predicate_span is None:
        raise ValueError("reviewed clause has no predicate evidence to project as an action")

    source = clause.span.text
    modality, modal_span = _modality(clause)
    local_modal = _local_span(source, clause, modal_span) if modal_span is not None else None
    local_subject = (
        _local_span(source, clause, clause.subject_span)
        if clause.subject_span is not None
        else None
    )
    local_predicate = _local_span(source, clause, clause.predicate_span)

    diagnostics: list[Diagnostic] = []
    if clause.condition_span is not None:
        local_condition = _local_span(source, clause, clause.condition_span)
        diagnostics.append(
            Diagnostic(
                code="reviewed-condition-unprojected",
                severity=DiagnosticSeverity.WARNING,
                message=(
                    "Reviewed condition evidence is preserved, but no equivalent generic "
                    "Provision AST condition expression was established."
                ),
                span=local_condition,
            )
        )

    provision = ProvisionAst(
        source_text=source,
        source_artifact=SourceArtifact(
            artifact_id=review.source_artifact.artifact_id,
            provision_locator=(
                f"{review.source_artifact.edition_id}:{review.section_locator}:{clause.clause_id}"
            ),
        ),
        modality=modality,
        modality_span=local_modal,
        subject=local_subject.text if local_subject is not None else "",
        subject_span=local_subject,
        action=Action(
            text=local_predicate.text,
            normalized_verb=None,
            object_text=None,
            span=local_predicate,
        ),
        source_span=SourceSpan(0, len(source), source),
        condition=None,
        diagnostics=tuple(diagnostics),
    )
    validate_ast(provision)

    dependencies = tuple(
        CodeReference(
            kind=reference.kind,
            target=reference.target,
            span=_local_span(source, clause, reference.span),
        )
        for reference in clause.references
    )

    return ReviewedProvisionProjection(
        source_artifact=review.source_artifact,
        section_locator=review.section_locator,
        clause_id=clause.clause_id,
        state=SemanticProjectionState.REVIEWED,
        provision=provision,
        dependencies=dependencies,
    )
