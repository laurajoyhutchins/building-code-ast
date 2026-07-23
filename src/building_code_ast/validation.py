"""Structural invariants for AST values.

This module provides dependency-free runtime validation. The JSON Schema in
``schemas/`` is the external contract for other implementations.
"""

from __future__ import annotations

from .model import Modality, ProvisionAst, SourceSpan


def _validate_span(source: str, span: SourceSpan, label: str) -> None:
    if span.start < 0 or span.end < span.start or span.end > len(source):
        raise ValueError(f"{label} span is outside the source text")
    if source[span.start : span.end] != span.text:
        raise ValueError(f"{label} span text does not match the source text")


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

    _validate_span(ast.source_text, ast.action.span, "action")

    for index, condition in enumerate(ast.conditions):
        _validate_span(ast.source_text, condition.span, f"condition[{index}]")
        if condition.operator not in {">", ">=", "<", "<=", "=="}:
            raise ValueError(f"condition[{index}] has an unsupported operator")

    for index, exception in enumerate(ast.exceptions):
        _validate_span(ast.source_text, exception.span, f"exception[{index}]")

    for index, diagnostic in enumerate(ast.diagnostics):
        if diagnostic.span is not None:
            _validate_span(ast.source_text, diagnostic.span, f"diagnostic[{index}]")
