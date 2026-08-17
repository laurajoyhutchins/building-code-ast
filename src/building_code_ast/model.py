"""Versioned semantic AST model.

The model preserves source evidence and uncertainty. It intentionally does not
encode compliance conclusions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


AST_VERSION = "0.3.0"


class Modality(StrEnum):
    REQUIREMENT = "requirement"
    PROHIBITION = "prohibition"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


class LogicalConditionType(StrEnum):
    ALL_OF = "all_of"
    ANY_OF = "any_of"


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    start: int
    end: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    artifact_id: str
    provision_locator: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: DiagnosticSeverity
    message: str
    span: SourceSpan | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "span": self.span.to_dict() if self.span else None,
        }


@dataclass(frozen=True, slots=True)
class Quantity:
    value: float
    unit: str
    original_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComparisonCondition:
    subject_property: str
    operator: str
    threshold: Quantity
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "comparison",
            "subject_property": self.subject_property,
            "operator": self.operator,
            "threshold": self.threshold.to_dict(),
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SourceTextCondition:
    """Condition evidence whose internal semantics have not been decomposed."""

    text: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "source_text",
            "text": self.text,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class LogicalCondition:
    type: LogicalConditionType
    operands: tuple[ComparisonCondition | SourceTextCondition | LogicalCondition, ...]
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "operands": [operand.to_dict() for operand in self.operands],
            "span": self.span.to_dict(),
        }


ConditionExpression = ComparisonCondition | SourceTextCondition | LogicalCondition


@dataclass(frozen=True, slots=True)
class Action:
    text: str
    normalized_verb: str | None
    object_text: str | None
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SectionReference:
    section: str
    span: SourceSpan

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "section_reference",
            "section": self.section,
            "span": self.span.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ProvisionAst:
    source_text: str
    source_artifact: SourceArtifact
    modality: Modality
    modality_span: SourceSpan | None
    subject: str
    subject_span: SourceSpan | None
    action: Action
    source_span: SourceSpan
    condition: ConditionExpression | None = None
    exceptions: tuple[SectionReference, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    ast_version: str = field(default=AST_VERSION, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ast_version": self.ast_version,
            "type": "provision",
            "source_text": self.source_text,
            "source_artifact": self.source_artifact.to_dict(),
            "source_span": self.source_span.to_dict(),
            "modality": self.modality.value,
            "modality_span": self.modality_span.to_dict() if self.modality_span else None,
            "subject": self.subject,
            "subject_span": self.subject_span.to_dict() if self.subject_span else None,
            "condition": self.condition.to_dict() if self.condition else None,
            "action": self.action.to_dict(),
            "exceptions": [exception.to_dict() for exception in self.exceptions],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }
