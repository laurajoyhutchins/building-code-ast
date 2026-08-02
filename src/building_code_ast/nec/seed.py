"""Strict enough ArticleSeed projections for NEC semantic processing."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any, Iterable

from ..document_model import DocumentSourceArtifact
from ..model import SourceSpan


@dataclass(frozen=True, slots=True)
class SeedNode:
    node_type: str
    locator: str
    label: str | None
    span: SourceSpan
    attributes: tuple[tuple[str, str], ...]
    children: tuple["SeedNode", ...]


@dataclass(frozen=True, slots=True)
class ArticleSeedView:
    source_text: str
    source_artifact: DocumentSourceArtifact
    article_number: str
    article_title: str
    article_locator: str
    nodes: tuple[SeedNode, ...]


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _span(value: Any, source: str, label: str) -> SourceSpan:
    obj = _mapping(value, label)
    start = obj.get("start")
    end = obj.get("end")
    text = obj.get("text")
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError(f"{label}.start must be an integer")
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError(f"{label}.end must be an integer")
    if not isinstance(text, str):
        raise ValueError(f"{label}.text must be a string")
    span = SourceSpan(start, end, text)
    if start < 0 or end < start or end > len(source):
        raise ValueError(f"{label} is outside source_text")
    if source[start:end] != text:
        raise ValueError(f"{label} does not round-trip to source_text")
    return span


def _semantic_projection_span(
    full_span: SourceSpan,
    children: tuple[SeedNode, ...],
    *,
    source: str,
    node_type: str,
    locator: str,
) -> SourceSpan:
    """Return the node's own source block instead of its expanded tree span.

    Publication AST parents intentionally cover descendants. Semantic consumers
    need the original non-overlapping source blocks, so nested parents stop at
    the first child's source start. Document and Article wrappers keep their
    exact full-source spans for validation.
    """

    preserve_full = node_type == "document" or re.fullmatch(r"article:\d{2,3}", locator)
    if preserve_full or not children:
        return full_span

    end = min(child.span.start for child in children)
    while end > full_span.start and source[end - 1].isspace():
        end -= 1
    if end < full_span.start:
        raise ValueError(f"{locator} has a child before its own source span")
    return SourceSpan(full_span.start, end, source[full_span.start:end])


def _node(value: Any, source: str, label: str) -> SeedNode:
    obj = _mapping(value, label)
    node_type = _string(obj.get("type"), f"{label}.type")
    locator = _string(obj.get("locator"), f"{label}.locator")
    raw_label = obj.get("label")
    if raw_label is not None and not isinstance(raw_label, str):
        raise ValueError(f"{label}.label must be a string or null")
    attributes_obj = _mapping(obj.get("attributes"), f"{label}.attributes")
    attributes: list[tuple[str, str]] = []
    for name in sorted(attributes_obj):
        if not isinstance(name, str) or not isinstance(attributes_obj[name], str):
            raise ValueError(f"{label}.attributes must contain string keys and values")
        attributes.append((name, attributes_obj[name]))
    children_obj = obj.get("children")
    if not isinstance(children_obj, list):
        raise ValueError(f"{label}.children must be an array")
    children = tuple(
        _node(child, source, f"{label}.children[{index}]")
        for index, child in enumerate(children_obj)
    )
    full_span = _span(obj.get("span"), source, f"{label}.span")
    return SeedNode(
        node_type=node_type,
        locator=locator,
        label=raw_label,
        span=_semantic_projection_span(
            full_span,
            children,
            source=source,
            node_type=node_type,
            locator=locator,
        ),
        attributes=tuple(attributes),
        children=children,
    )


def _preorder(nodes: Iterable[SeedNode]) -> Iterable[SeedNode]:
    for node in nodes:
        yield node
        yield from _preorder(node.children)


def article_seed_view(
    value: Mapping[str, Any],
    *,
    expected_article: str | None = None,
) -> ArticleSeedView:
    seed = _mapping(value, "ArticleSeed")
    article = _mapping(seed.get("article"), "ArticleSeed.article")
    article_number = _string(article.get("number"), "ArticleSeed.article.number")
    article_title = _string(article.get("title"), "ArticleSeed.article.title")
    if expected_article is not None and article_number != expected_article:
        raise ValueError(f"expected Article {expected_article}, found Article {article_number}")

    document = _mapping(seed.get("document_ast"), "ArticleSeed.document_ast")
    source = _string(document.get("source_text"), "document_ast.source_text")
    if not source:
        raise ValueError("document_ast.source_text must not be empty")
    artifact_obj = _mapping(document.get("source_artifact"), "document_ast.source_artifact")
    artifact = DocumentSourceArtifact(
        artifact_id=_string(artifact_obj.get("artifact_id"), "source_artifact.artifact_id"),
        edition_id=_string(artifact_obj.get("edition_id"), "source_artifact.edition_id"),
    )
    if not artifact.artifact_id.strip() or not artifact.edition_id.strip():
        raise ValueError("source artifact identity must not be empty")

    root = _node(document.get("root"), source, "document_ast.root")
    if root.node_type != "document":
        raise ValueError("document_ast.root must have type 'document'")
    if root.span.start != 0 or root.span.end != len(source):
        raise ValueError("document_ast.root must cover the exact source_text")
    if len(root.children) != 1:
        raise ValueError("ArticleSeed document root must contain exactly one article node")
    article_node = root.children[0]
    expected_locator = f"article:{article_number}"
    if article_node.locator != expected_locator:
        raise ValueError(f"article node locator must be {expected_locator!r}")
    if article_node.span.start != 0 or article_node.span.end != len(source):
        raise ValueError("article node must cover the exact source_text")

    manifest = seed.get("source_manifest")
    if manifest is not None:
        manifest_obj = _mapping(manifest, "ArticleSeed.source_manifest")
        if manifest_obj.get("artifact_id") != artifact.artifact_id:
            raise ValueError("source_manifest artifact_id does not match document_ast")
        if manifest_obj.get("edition_id") != artifact.edition_id:
            raise ValueError("source_manifest edition_id does not match document_ast")

    return ArticleSeedView(
        source_text=source,
        source_artifact=artifact,
        article_number=article_number,
        article_title=article_title,
        article_locator=article_node.locator,
        nodes=tuple(_preorder(article_node.children)),
    )
