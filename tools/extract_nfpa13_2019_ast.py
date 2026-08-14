#!/usr/bin/env python3
"""NFPA 13 (2019) publication adapter over shared repository infrastructure.

Publication-specific AST grammar remains in the preserved legacy compiler while
generic positioned PDF observation, Document AST construction, node identity,
and deterministic bundle serialization are routed through shared Building Code
AST components.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Sequence as _Sequence

import building_code_ast.document_io as _document_io
import building_code_ast.document_model as _document_model
from building_code_ast.model import SourceSpan as _SourceSpan
from building_code_ast.nfpa13_bundle import canonical_json_bytes as _shared_canonical_json_bytes
from building_code_ast.pdf_observation import observe_pymupdf_page


_LEGACY_PATH = Path(__file__).with_name("_extract_nfpa13_2019_ast_legacy.py")
_LEGACY_SPEC = importlib.util.spec_from_file_location(
    "_extract_nfpa13_2019_ast_legacy",
    _LEGACY_PATH,
)
if _LEGACY_SPEC is None or _LEGACY_SPEC.loader is None:
    raise RuntimeError(f"could not load NFPA 13 legacy adapter body from {_LEGACY_PATH.name}")
_legacy = importlib.util.module_from_spec(_LEGACY_SPEC)
sys.modules.setdefault(_LEGACY_SPEC.name, _legacy)
_LEGACY_SPEC.loader.exec_module(_legacy)

# Preserve the existing public and test-facing surface while the compiler body is
# retired incrementally. Dunder module metadata stays owned by this adapter.
for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

# Reassert shared primitives after copying the legacy public surface so the
# adapter cannot accidentally expose a duplicate implementation by name.
canonical_json_bytes = _shared_canonical_json_bytes
_SOURCE_ARTIFACT = _document_model.DocumentSourceArtifact(
    artifact_id=ARTIFACT_ID,
    edition_id=EDITION_ID,
)


def _node_id(locator: str, node_type: str) -> str:
    """Return the shared deterministic Document AST node identity."""

    return _document_model.document_node_id(
        artifact_id=ARTIFACT_ID,
        edition_id=EDITION_ID,
        node_type=node_type,
        locator=locator,
    )


def _node(
    source: str,
    *,
    node_type: str,
    locator: str,
    start: int,
    end: int,
    label: str | None = None,
    attributes: Mapping[str, str] | None = None,
    children: _Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Construct the legacy NFPA dictionary surface through shared Document AST."""

    child_nodes = tuple(_document_io.document_node_from_dict(child) for child in children)
    return _document_model.make_document_node(
        source_artifact=_SOURCE_ARTIFACT,
        node_type=node_type,
        locator=locator,
        span=_SourceSpan(start=start, end=end, text=source[start:end]),
        label=label,
        attributes=attributes,
        children=child_nodes,
    ).to_dict()


def raw_lines_from_document(doc: Any, first_page: int, last_page: int) -> list[RawLine]:
    """Project shared positioned-text observations into NFPA-specific raw lines."""

    lines: list[RawLine] = []
    for pdf_page in range(first_page, last_page + 1):
        page = doc[pdf_page - 1]
        printed_match = PRINTED_PAGE_RE.search(page.get_text("text")[:400])
        printed_page = f"13-{printed_match.group('number')}" if printed_match else None
        observed = observe_pymupdf_page(page, page_number=pdf_page)
        for block in observed.blocks:
            for raw in block.lines:
                spans = [span for span in raw.spans if span.text]
                text = "".join(span.text for span in spans)
                if not text.strip():
                    continue
                bbox = raw.bbox
                lines.append(
                    RawLine(
                        text=text,
                        pdf_page=pdf_page,
                        printed_page=printed_page,
                        column=0 if bbox[0] < 306.0 else 1,
                        bbox=bbox,
                        fonts=tuple(span.font_name for span in spans),
                        sizes=tuple(span.font_size for span in spans),
                    )
                )
    return lines


# Existing build and CLI functions execute in the legacy module's globals. Point
# migrated generic seams back at this adapter/shared infrastructure so every
# legacy call path uses the current repository contracts.
_legacy._node_id = _node_id
_legacy._node = _node
_legacy.canonical_json_bytes = canonical_json_bytes
_legacy.raw_lines_from_document = raw_lines_from_document


if __name__ == "__main__":
    raise SystemExit(_legacy.main())
