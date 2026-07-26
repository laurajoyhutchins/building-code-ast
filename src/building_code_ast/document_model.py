"""Versioned publication-structure AST model.

This layer records how a source document is organized before any provision is
interpreted as a requirement, prohibition, permission, condition, or action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any, Mapping, Sequence

from .model import Diagnostic, SourceSpan


DOCUMENT_AST_VERSION = "0.1.0"


class DocumentNodeType(StrEnum):
    DOCUMENT = "document"
    CHAPTER = "chapter"
    SECTION = "section"
    SUBSECTION = "subsection"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    DEFINITION_ENTRY = "definition_entry"
    TABLE = "table"
    TABLE_HEADING = "table_heading"
    TABLE_COLUMN = "table_column"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    HEADING = "heading"
    NOTE = "note"
    FOOTNOTE = "footnote"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class DocumentSourceArtifact:
    artifact_id: str
    edition_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "artifact_id": self.artifact_id,
            "edition_id": self.edition_id,
        }


@dataclass(frozen=True, slots=True)
class DocumentNode:
    node_id: str
    node_type: DocumentNodeType
    locator: str
    span: SourceSpan
    label: str | None = None
    attributes: tuple[tuple[str, str], ...] = ()
    children: tuple["DocumentNode", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "type": self.node_type.value,
            "locator": self.locator,
            "span": self.span.to_dict(),
            "label": self.label,
            "attributes": dict(self.attributes),
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True, slots=True)
class DocumentAst:
    source_text: str
    source_artifact: DocumentSourceArtifact
    root: DocumentNode
    diagnostics: tuple[Diagnostic, ...] = ()
    ast_version: str = field(default=DOCUMENT_AST_VERSION, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ast_version": self.ast_version,
            "type": "document_tree",
            "source_text": self.source_text,
            "source_artifact": self.source_artifact.to_dict(),
            "root": self.root.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def document_node_id(
    *,
    artifact_id: str,
    edition_id: str,
    node_type: DocumentNodeType | str,
    locator: str,
) -> str:
    """Return the deterministic identity for one structural node.

    The canonical input deliberately excludes source text and character offsets.
    A node remains stable when the same edition is reparsed, while an edition
    change produces a different identity even when the locator is unchanged.
    """

    if not artifact_id.strip():
        raise ValueError("artifact_id must not be empty")
    if not edition_id.strip():
        raise ValueError("edition_id must not be empty")
    if not locator.strip():
        raise ValueError("locator must not be empty")

    normalized_type = DocumentNodeType(node_type).value
    canonical = json.dumps(
        {
            "artifact_id": artifact_id,
            "edition_id": edition_id,
            "locator": locator,
            "node_type": normalized_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"docnode:{digest}"


def make_document_node(
    *,
    source_artifact: DocumentSourceArtifact,
    node_type: DocumentNodeType | str,
    locator: str,
    span: SourceSpan,
    label: str | None = None,
    attributes: Mapping[str, str] | None = None,
    children: Sequence[DocumentNode] = (),
) -> DocumentNode:
    """Construct a node with canonicalized attributes and deterministic identity."""

    normalized_type = DocumentNodeType(node_type)
    normalized_attributes = tuple(sorted((attributes or {}).items()))
    return DocumentNode(
        node_id=document_node_id(
            artifact_id=source_artifact.artifact_id,
            edition_id=source_artifact.edition_id,
            node_type=normalized_type,
            locator=locator,
        ),
        node_type=normalized_type,
        locator=locator,
        span=span,
        label=label,
        attributes=normalized_attributes,
        children=tuple(children),
    )
