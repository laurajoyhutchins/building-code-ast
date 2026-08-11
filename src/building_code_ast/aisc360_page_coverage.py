"""Conservative whole-component page coverage for ANSI/AISC 360-16.

The first AISC 360 Document AST layer preserves page evidence without claiming
section hierarchy or performing OCR. Every source page is represented as an
``unsupported`` node until stronger source-backed structure is established.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .document_model import (
    DocumentAst,
    DocumentNodeType,
    DocumentSourceArtifact,
    make_document_node,
)
from .document_validation import validate_document_ast
from .model import Diagnostic, DiagnosticSeverity, SourceSpan


_PARENT_ARTIFACT_ID = (
    "sha256:c5fbe648fd81a7ecda10df115393bbb9492924c8ce22167fc6d86c8b87fd8e7f"
)
_EDITION_ID = "aisc-scm-15"
_COMPONENT_ID = "ansi-aisc-360-16"


@dataclass(frozen=True, slots=True)
class Aisc360PageObservation:
    """One component-local page observation.

    ``embedded_text`` is the exact extracted page text when a text layer exists.
    ``None`` means no embedded text was observed. Empty strings are rejected so
    absence is never silently conflated with successful text extraction.
    """

    page_number: int
    embedded_text: str | None

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must be positive")
        if self.embedded_text is not None:
            if not isinstance(self.embedded_text, str):
                raise ValueError("embedded text must be a string or None")
            if not self.embedded_text:
                raise ValueError("embedded text must not be empty")


def build_aisc360_page_coverage_ast(
    observations: Sequence[Aisc360PageObservation],
    *,
    expected_page_count: int = 674,
) -> DocumentAst:
    """Build a source-faithful page-coverage AST without hierarchy claims.

    Text-backed pages own their exact extracted text in one concatenated
    observation stream. Image-only pages receive zero-length spans at their
    source-order insertion points. The page number and source kind remain
    explicit attributes, and all page nodes remain ``unsupported`` until later
    source-backed parsing refines them.
    """

    if expected_page_count < 1:
        raise ValueError("expected_page_count must be positive")

    ordered = tuple(sorted(observations, key=lambda item: item.page_number))
    observed_pages = tuple(item.page_number for item in ordered)
    expected_pages = tuple(range(1, expected_page_count + 1))
    if observed_pages != expected_pages:
        raise ValueError("observations must cover each one-based component page exactly once")

    source_text = "".join(
        item.embedded_text for item in ordered if item.embedded_text is not None
    )
    if not source_text:
        raise ValueError("page coverage requires at least one embedded-text page")

    source_artifact = DocumentSourceArtifact(
        artifact_id=_PARENT_ARTIFACT_ID,
        edition_id=_EDITION_ID,
        publication_component_id=_COMPONENT_ID,
    )

    children = []
    diagnostics = []
    offset = 0
    for item in ordered:
        if item.embedded_text is None:
            span = SourceSpan(start=offset, end=offset, text="")
            source_kind = "image_only"
            diagnostics.append(
                Diagnostic(
                    code="AISC360_IMAGE_ONLY_PAGE",
                    severity=DiagnosticSeverity.WARNING,
                    message=f"component page {item.page_number} is image-only source evidence",
                    span=span,
                )
            )
        else:
            start = offset
            offset += len(item.embedded_text)
            span = SourceSpan(start=start, end=offset, text=item.embedded_text)
            source_kind = "embedded_text"

        children.append(
            make_document_node(
                source_artifact=source_artifact,
                node_type=DocumentNodeType.UNSUPPORTED,
                locator=f"page:{item.page_number}",
                span=span,
                attributes={
                    "pdf_page": str(item.page_number),
                    "source_kind": source_kind,
                    "structural_status": "unparsed",
                },
            )
        )

    root = make_document_node(
        source_artifact=source_artifact,
        node_type=DocumentNodeType.DOCUMENT,
        locator="document",
        span=SourceSpan(start=0, end=len(source_text), text=source_text),
        attributes={"coverage": "component_pages"},
        children=children,
    )
    ast = DocumentAst(
        source_text=source_text,
        source_artifact=source_artifact,
        root=root,
        diagnostics=tuple(diagnostics),
    )
    validate_document_ast(ast)
    return ast
