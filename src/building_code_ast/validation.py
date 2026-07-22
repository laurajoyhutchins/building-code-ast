"""Structural invariants for AST values.

This module provides dependency-free runtime validation. The JSON Schema in
``schemas/`` is the external contract for other implementations.
"""

from __future__ import annotations

from .model import ProvisionAst, SourceSpan


def _validate_span(source: str, span: SourceSpan, label: str) -> None:
    if span.start < 0 or span.end < span.start or span.end > len(source):
        raise ValueError(f"{label} span is outside the source text")
    if source[span.start : span.end] != span.text:
        raise ValueError(f"{label} span text does not match the source text")


def validate_ast(ast: ProvisionAst) -> None:
    """Raise ``ValueError`` when core provenance invariants are broken."""

    _validate_span(ast.source_text, ast.source_span, "provision")
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
