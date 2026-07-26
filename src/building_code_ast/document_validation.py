"""Runtime validation for publication-structure AST values."""

from __future__ import annotations

from .document_model import (
    DOCUMENT_AST_VERSION,
    DocumentAst,
    DocumentNode,
    DocumentNodeType,
    document_node_id,
)
from .model import SourceSpan


def _validate_span(source: str, span: SourceSpan, label: str) -> None:
    if span.start < 0 or span.end < span.start or span.end > len(source):
        raise ValueError(f"{label} span is outside the source text")
    if source[span.start : span.end] != span.text:
        raise ValueError(f"{label} span text does not match the source text")


def validate_document_ast(ast: DocumentAst) -> None:
    """Raise ``ValueError`` when document identity or provenance is inconsistent."""

    if ast.ast_version != DOCUMENT_AST_VERSION:
        raise ValueError(f"document AST version must be {DOCUMENT_AST_VERSION}")
    if not ast.source_text:
        raise ValueError("document source_text must not be empty")
    if not ast.source_artifact.artifact_id.strip():
        raise ValueError("document source artifact id must not be empty")
    if not ast.source_artifact.edition_id.strip():
        raise ValueError("document source edition id must not be empty")
    if ast.root.node_type is not DocumentNodeType.DOCUMENT:
        raise ValueError("document root node must have type 'document'")

    _validate_span(ast.source_text, ast.root.span, "document root")
    if ast.root.span.start != 0 or ast.root.span.end != len(ast.source_text):
        raise ValueError("document root span must cover the exact original source text")

    seen_ids: set[str] = set()
    seen_locators: set[str] = set()

    def validate_node(node: DocumentNode, parent: DocumentNode | None) -> None:
        label = f"document node {node.locator!r}"
        if not node.locator.strip():
            raise ValueError("document node locator must not be empty")
        _validate_span(ast.source_text, node.span, label)

        if parent is not None and (
            node.span.start < parent.span.start or node.span.end > parent.span.end
        ):
            raise ValueError(
                f"document node {node.locator!r} span is outside parent {parent.locator!r}"
            )

        expected_id = document_node_id(
            artifact_id=ast.source_artifact.artifact_id,
            edition_id=ast.source_artifact.edition_id,
            node_type=node.node_type,
            locator=node.locator,
        )
        if node.node_id != expected_id:
            raise ValueError(
                f"document node {node.locator!r} does not match its deterministic identity"
            )
        if node.locator in seen_locators:
            raise ValueError(f"duplicate document locator: {node.locator}")
        if node.node_id in seen_ids:
            raise ValueError(f"duplicate document node id: {node.node_id}")
        seen_ids.add(node.node_id)
        seen_locators.add(node.locator)

        attribute_names: set[str] = set()
        for name, value in node.attributes:
            if not name.strip():
                raise ValueError(f"document node {node.locator!r} has an empty attribute name")
            if name in attribute_names:
                raise ValueError(
                    f"document node {node.locator!r} has duplicate attribute {name!r}"
                )
            if not isinstance(value, str):
                raise ValueError(
                    f"document node {node.locator!r} attribute {name!r} must be a string"
                )
            attribute_names.add(name)

        for child in node.children:
            validate_node(child, node)

    validate_node(ast.root, None)

    for index, diagnostic in enumerate(ast.diagnostics):
        if diagnostic.span is not None:
            _validate_span(
                ast.source_text,
                diagnostic.span,
                f"document diagnostic[{index}]",
            )
