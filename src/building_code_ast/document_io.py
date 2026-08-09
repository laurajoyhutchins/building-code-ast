"""Strict JSON-compatible input handling for document AST values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .document_model import (
    DOCUMENT_AST_VERSION,
    DocumentAst,
    DocumentNode,
    DocumentNodeType,
    DocumentSourceArtifact,
)
from .document_validation import validate_document_ast
from .model import Diagnostic, DiagnosticSeverity, SourceSpan


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    required: set[str],
    label: str,
) -> None:
    actual = set(value)
    missing = required - actual
    extra = actual - required
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{label} has unsupported fields: {sorted(extra)}")


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _span(value: Any, label: str) -> SourceSpan:
    obj = _object(value, label)
    _exact_keys(obj, {"start", "end", "text"}, label)
    start = obj["start"]
    end = obj["end"]
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError(f"{label}.start must be an integer")
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError(f"{label}.end must be an integer")
    return SourceSpan(
        start=start,
        end=end,
        text=_string(obj["text"], f"{label}.text"),
    )


def _diagnostic(value: Any, index: int) -> Diagnostic:
    label = f"diagnostics[{index}]"
    obj = _object(value, label)
    _exact_keys(obj, {"code", "severity", "message", "span"}, label)
    try:
        severity = DiagnosticSeverity(_string(obj["severity"], f"{label}.severity"))
    except ValueError as exc:
        raise ValueError(f"{label}.severity is unsupported") from exc
    return Diagnostic(
        code=_string(obj["code"], f"{label}.code"),
        severity=severity,
        message=_string(obj["message"], f"{label}.message"),
        span=None if obj["span"] is None else _span(obj["span"], f"{label}.span"),
    )


def _node(value: Any, path: str) -> DocumentNode:
    obj = _object(value, path)
    _exact_keys(
        obj,
        {"node_id", "type", "locator", "span", "label", "attributes", "children"},
        path,
    )
    try:
        node_type = DocumentNodeType(_string(obj["type"], f"{path}.type"))
    except ValueError as exc:
        raise ValueError(f"{path}.type is unsupported") from exc

    attributes_obj = _object(obj["attributes"], f"{path}.attributes")
    attributes: list[tuple[str, str]] = []
    for name in sorted(attributes_obj):
        if not isinstance(name, str):
            raise ValueError(f"{path}.attributes keys must be strings")
        attributes.append(
            (name, _string(attributes_obj[name], f"{path}.attributes[{name!r}]"))
        )

    children_value = obj["children"]
    if not isinstance(children_value, list):
        raise ValueError(f"{path}.children must be an array")
    children = tuple(
        _node(child, f"{path}.children[{index}]")
        for index, child in enumerate(children_value)
    )

    return DocumentNode(
        node_id=_string(obj["node_id"], f"{path}.node_id"),
        node_type=node_type,
        locator=_string(obj["locator"], f"{path}.locator"),
        span=_span(obj["span"], f"{path}.span"),
        label=_optional_string(obj["label"], f"{path}.label"),
        attributes=tuple(attributes),
        children=children,
    )


def document_ast_from_dict(value: Mapping[str, Any]) -> DocumentAst:
    """Read and validate a JSON-compatible document AST mapping."""

    obj = _object(value, "document AST")
    _exact_keys(
        obj,
        {
            "ast_version",
            "type",
            "source_text",
            "source_artifact",
            "root",
            "diagnostics",
        },
        "document AST",
    )
    if obj["ast_version"] != DOCUMENT_AST_VERSION:
        raise ValueError(f"document AST ast_version must be {DOCUMENT_AST_VERSION}")
    if obj["type"] != "document_tree":
        raise ValueError("document AST type must be 'document_tree'")

    artifact_obj = _object(obj["source_artifact"], "source_artifact")
    required_artifact_keys = {"artifact_id", "edition_id"}
    actual_artifact_keys = set(artifact_obj)
    missing = required_artifact_keys - actual_artifact_keys
    extra = actual_artifact_keys - required_artifact_keys - {"publication_component_id"}
    if missing:
        raise ValueError(f"source_artifact is missing required fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"source_artifact has unsupported fields: {sorted(extra)}")

    source_artifact = DocumentSourceArtifact(
        artifact_id=_string(artifact_obj["artifact_id"], "source_artifact.artifact_id"),
        edition_id=_string(artifact_obj["edition_id"], "source_artifact.edition_id"),
        publication_component_id=(
            _string(
                artifact_obj["publication_component_id"],
                "source_artifact.publication_component_id",
            )
            if "publication_component_id" in artifact_obj
            else None
        ),
    )

    diagnostics_value = obj["diagnostics"]
    if not isinstance(diagnostics_value, list):
        raise ValueError("document AST diagnostics must be an array")

    ast = DocumentAst(
        source_text=_string(obj["source_text"], "document AST source_text"),
        source_artifact=source_artifact,
        root=_node(obj["root"], "root"),
        diagnostics=tuple(
            _diagnostic(diagnostic, index)
            for index, diagnostic in enumerate(diagnostics_value)
        ),
    )
    validate_document_ast(ast)
    return ast
