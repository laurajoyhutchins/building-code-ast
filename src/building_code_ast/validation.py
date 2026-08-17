"""Structural invariants for AST values.

This module provides dependency-free runtime validation. The JSON Schema in
``schemas/`` is the external contract for other implementations.
"""

from __future__ import annotations

from .model import (
    ComparisonCondition,
    LogicalCondition,
    LogicalConditionType,
    Modality,
    ProvisionAst,
    SourceSpan,
    SourceTextCondition,
)


def _validate_span(source: str, span: SourceSpan, label: str) -> None:
    if span.start < 0 or span.end < span.start or span.end > len(source):
        raise ValueError(f"{label} span is outside the source text")
    if source[span.start : span.end] != span.text:
        raise ValueError(f"{label} span text does not match the source text")


def _validate_condition(
    source: str,
    condition: ComparisonCondition | SourceTextCondition | LogicalCondition,
    label: str,
    active_path: set[int],
) -> None:
    if isinstance(condition, ComparisonCondition):
        _validate_span(source, condition.span, label)
        if condition.operator not in {">", ">=", "<", "<=", "=="}:
            raise ValueError(f"{label} has an unsupported operator")
        if condition.threshold.original_text != condition.span.text:
            raise ValueError(f"{label} threshold original text must match its span text")
        return

    if isinstance(condition, SourceTextCondition):
        _validate_span(source, condition.span, label)
        if not condition.text:
            raise ValueError(f"{label} source text must not be empty")
        if condition.text != condition.span.text:
            raise ValueError(f"{label} source text must exactly match its span text")
        return

    if not isinstance(condition, LogicalCondition):
        raise ValueError(f"{label} has an unsupported condition expression type")
    if not isinstance(condition.type, LogicalConditionType):
        raise ValueError(f"{label} has an unsupported logical condition type")
    if len(condition.operands) < 2:
        raise ValueError(f"{label} must contain at least two operands")

    identity = id(condition)
    if identity in active_path:
        raise ValueError(f"{label} contains a logical condition cycle")

    _validate_span(source, condition.span, label)
    active_path.add(identity)
    try:
        previous_span: SourceSpan | None = None
        for index, operand in enumerate(condition.operands):
            if not isinstance(operand, (ComparisonCondition, SourceTextCondition, LogicalCondition)):
                raise ValueError(f"{label}.operands[{index}] has an unsupported condition expression type")

            child_span = operand.span
            if child_span.start < condition.span.start or child_span.end > condition.span.end:
                raise ValueError(f"{label}.operands[{index}] span is outside its logical group")
            if previous_span is not None:
                if child_span.start <= previous_span.start:
                    raise ValueError(f"{label} operands are not in strict source order")
                if child_span.start < previous_span.end:
                    raise ValueError(f"{label} operand spans overlap")

            _validate_condition(
                source,
                operand,
                f"{label}.operands[{index}]",
                active_path,
            )
            previous_span = child_span

        first_span = condition.operands[0].span
        last_span = condition.operands[-1].span
        if condition.span.start != first_span.start:
            raise ValueError(f"{label} must start at its first operand")
        if condition.span.end != last_span.end:
            raise ValueError(f"{label} must end at its last operand")
    finally:
        active_path.remove(identity)


def validate_ast(ast: ProvisionAst) -> None:
    """Raise ``ValueError`` when core provenance invariants are broken."""

    if not ast.source_artifact.artifact_id.strip():
        raise ValueError("source artifact id must not be empty")
    if not ast.source_artifact.provision_locator.strip():
        raise ValueError("provision locator must not be empty")

    _validate_span(ast.source_text, ast.source_span, "provision")
    if ast.source_span.start != 0 or ast.source_span.end != len(ast.source_text):
        raise ValueError("provision span must cover the exact original source text")

    if ast.modality is Modality.UNKNOWN:
        if ast.modality_span is not None:
            raise ValueError("unknown modality must not have an evidence span")
    else:
        if ast.modality_span is None:
            raise ValueError("recognized modality must have an evidence span")
        _validate_span(ast.source_text, ast.modality_span, "modality")

    if ast.subject:
        if ast.subject_span is None:
            raise ValueError("non-empty subject must have an evidence span")
        _validate_span(ast.source_text, ast.subject_span, "subject")
        if ast.subject_span.text != ast.subject:
            raise ValueError("subject evidence must exactly match the subject text")
    elif ast.subject_span is not None:
        raise ValueError("empty subject must not have an evidence span")

    if ast.condition is not None:
        _validate_condition(ast.source_text, ast.condition, "condition", set())

    _validate_span(ast.source_text, ast.action.span, "action")

    for index, exception in enumerate(ast.exceptions):
        _validate_span(ast.source_text, exception.span, f"exception[{index}]")

    for index, diagnostic in enumerate(ast.diagnostics):
        if diagnostic.span is not None:
            _validate_span(ast.source_text, diagnostic.span, f"diagnostic[{index}]")
