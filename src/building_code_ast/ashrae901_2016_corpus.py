"""Source-safe whole-document measurement for retained ASHRAE 90.1-2016.

This module measures the current ASHRAE 90.1 observation adapter against PDF
layout and outline evidence. It also provides a source-safe materialization
receipt that runs the real publication adapter and generic Document AST
validator without serializing the private AST or source expression.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any, Iterator

from .document_model import DocumentNode
from .document_validation import validate_document_ast
from .ingest.ashrae901_2016 import (
    Ashrae901Observation,
    _APPENDIX_RE,
    _EQUATION_RE,
    _TABLE_RE,
    _automatic_figure_locator,
    _is_content,
    _numeric_heading,
    _observation_key,
    _rotated_annex_figure_content,
    parse_ashrae901_2016_observations,
)
from .ingest.pdf_layout import PdfLayoutDocument, normalize_block_text


MEASUREMENT_VERSION = "0.2.0"
MATERIALIZATION_RECEIPT_VERSION = "0.1.0"
ASHRAE_90_1_2016_SOURCE_SHA256 = (
    "275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162"
)
ASHRAE_90_1_2016_SOURCE_SIZE = 3_475_675
ASHRAE_90_1_2016_PAGE_COUNT = 388

_NUMERIC_OUTLINE_RE = re.compile(r"^(?P<locator>\d+(?:\.\d+)*)\.?(?:\s|$)")
_APPENDIX_NATIVE_OUTLINE_RE = re.compile(
    r"^(?P<locator>[A-H]\d+(?:\.\d+)*)\.?(?:\s|$)"
)


def _verify_exact_source(
    layout: PdfLayoutDocument,
    *,
    source_sha256: str,
    source_size: int,
) -> None:
    if source_sha256 != ASHRAE_90_1_2016_SOURCE_SHA256:
        raise ValueError("source_sha256 must match exact retained ASHRAE 90.1-2016 SHA-256")
    if source_size != ASHRAE_90_1_2016_SOURCE_SIZE:
        raise ValueError("source_size must match exact retained ASHRAE 90.1-2016 size")
    if layout.page_count != ASHRAE_90_1_2016_PAGE_COUNT:
        raise ValueError("layout must contain the exact retained artifact's 388 PDF pages")


def _ordered_observations(layout: PdfLayoutDocument) -> tuple[Ashrae901Observation, ...]:
    observations = (
        Ashrae901Observation(block=block)
        for page in layout.pages
        for block in page.blocks
    )
    return tuple(
        sorted(
            (
                observation
                for observation in observations
                if _is_content(observation) or _rotated_annex_figure_content(observation)
            ),
            key=_observation_key,
        )
    )


def _walk_document(node: DocumentNode) -> Iterator[DocumentNode]:
    yield node
    for child in node.children:
        yield from _walk_document(child)


def materialize_ashrae901_2016_document_receipt(
    layout: PdfLayoutDocument,
    *,
    source_sha256: str,
    source_size: int,
) -> dict[str, Any]:
    """Materialize and validate privately, returning only source-safe aggregates."""

    _verify_exact_source(
        layout,
        source_sha256=source_sha256,
        source_size=source_size,
    )
    observations = _ordered_observations(layout)
    ast = parse_ashrae901_2016_observations(observations)
    validate_document_ast(ast)

    nodes = tuple(_walk_document(ast.root))
    node_type_counts = Counter(node.node_type.value for node in nodes)
    diagnostic_counts = Counter(diagnostic.code for diagnostic in ast.diagnostics)
    return {
        "receipt_version": MATERIALIZATION_RECEIPT_VERSION,
        "status": "validated",
        "source": {
            "file_name": layout.file_name,
            "sha256": source_sha256,
            "size_bytes": source_size,
            "page_count": layout.page_count,
        },
        "source_block_count": len(observations),
        "node_count": len(nodes),
        "node_type_counts": dict(sorted(node_type_counts.items())),
        "diagnostic_counts": dict(sorted(diagnostic_counts.items())),
    }


def _classify(
    observation: Ashrae901Observation,
    *,
    inside_appendix: bool,
) -> tuple[str, str | None]:
    """Mirror current adapter classification without materializing source text."""

    text = normalize_block_text(observation.block.text)
    if match := _APPENDIX_RE.match(text):
        return "appendix", f"appendix:{match.group('letter').upper()}"

    heading = _numeric_heading(
        observation,
        text,
        inside_appendix=inside_appendix,
    )
    if heading is not None:
        locator, _ = heading
        kind = "section" if locator.count(".") == 0 else "subsection"
        return kind, f"section:{locator}"

    if match := _TABLE_RE.match(text):
        return "table", f"table:{match.group('locator')}"
    figure_locator = _automatic_figure_locator(observation, text)
    if figure_locator is not None:
        return "figure", f"figure:{figure_locator}"
    if match := _EQUATION_RE.search(text):
        return "equation", f"equation:{match.group('locator')}"
    return "paragraph", None


def _outline_locators(
    layout: PdfLayoutDocument,
    pattern: re.Pattern[str],
) -> dict[str, int]:
    locators: dict[str, int] = {}
    for item in layout.outline:
        title = normalize_block_text(item.title)
        match = pattern.match(title)
        if match is not None:
            locators.setdefault(match.group("locator"), item.page_number)
    return locators


def measure_ashrae901_2016_corpus(
    layout: PdfLayoutDocument,
    *,
    source_sha256: str,
    source_size: int,
) -> dict[str, Any]:
    """Measure current 90.1 structural recognition without retaining expression."""

    _verify_exact_source(
        layout,
        source_sha256=source_sha256,
        source_size=source_size,
    )

    observations = _ordered_observations(layout)
    classifier_counts: Counter[str] = Counter()
    numeric_pages: dict[str, list[int]] = defaultdict(list)
    numeric_first_seen: dict[str, int] = {}
    numeric_first_duplicate: dict[str, Any] | None = None
    structural_first_seen: dict[str, int] = {}
    structural_first_duplicate: dict[str, Any] | None = None
    recognized_appendices: set[str] = set()
    current_appendix_sublocators: set[str] = set()
    inside_appendix = False

    for observation in observations:
        kind, locator = _classify(
            observation,
            inside_appendix=inside_appendix,
        )
        classifier_counts[kind] += 1
        if kind == "appendix":
            inside_appendix = True
        if locator is None:
            continue

        page_number = observation.block.page_number
        if locator.startswith("section:"):
            native = locator.removeprefix("section:")
            if native and native[0].isdigit():
                numeric_pages[native].append(page_number)
                first_numeric_page = numeric_first_seen.get(locator)
                if first_numeric_page is None:
                    numeric_first_seen[locator] = page_number
                elif numeric_first_duplicate is None:
                    numeric_first_duplicate = {
                        "locator": locator,
                        "first_pdf_page": first_numeric_page,
                        "repeated_pdf_page": page_number,
                    }
            elif _APPENDIX_NATIVE_OUTLINE_RE.match(native):
                current_appendix_sublocators.add(native)
        elif locator.startswith("appendix:"):
            recognized_appendices.add(locator.removeprefix("appendix:"))

        first_page = structural_first_seen.get(locator)
        if first_page is None:
            structural_first_seen[locator] = page_number
        elif structural_first_duplicate is None:
            structural_first_duplicate = {
                "locator": locator,
                "first_pdf_page": first_page,
                "repeated_pdf_page": page_number,
            }

    numeric_outline = _outline_locators(layout, _NUMERIC_OUTLINE_RE)
    appendix_outline = _outline_locators(layout, _APPENDIX_NATIVE_OUTLINE_RE)
    top_level_outline_appendices = {
        match.group("letter").upper()
        for item in layout.outline
        if (
            match := _APPENDIX_RE.match(normalize_block_text(item.title))
        )
    }

    candidate_locators = set(numeric_pages)
    outline_locators = set(numeric_outline)
    matched = candidate_locators & outline_locators
    exact_page_matches = 0
    near_page_matches = 0
    far_only_matches = 0
    for locator in matched:
        outline_page = numeric_outline[locator]
        observed_pages = numeric_pages[locator]
        if outline_page in observed_pages:
            exact_page_matches += 1
        elif any(abs(page - outline_page) <= 1 for page in observed_pages):
            near_page_matches += 1
        else:
            far_only_matches += 1

    candidate_occurrences = sum(len(pages) for pages in numeric_pages.values())
    serialized_counts = {
        kind: classifier_counts.get(kind, 0)
        for kind in (
            "appendix",
            "equation",
            "figure",
            "paragraph",
            "section",
            "subsection",
            "table",
        )
    }

    blocker = (
        None
        if structural_first_duplicate is None
        else "duplicate_document_locator"
    )
    status = {
        "duplicate_locator_free": structural_first_duplicate is None,
        "blocker": blocker,
        "locator": (
            None
            if structural_first_duplicate is None
            else structural_first_duplicate["locator"]
        ),
    }

    return {
        "measurement_version": MEASUREMENT_VERSION,
        "source": {
            "file_name": layout.file_name,
            "sha256": source_sha256,
            "size_bytes": source_size,
            "page_count": layout.page_count,
            "outline_entries": len(layout.outline),
        },
        "source_block_count": len(observations),
        "classifier_counts": serialized_counts,
        "numeric_hierarchy": {
            "outline_unique_locators": len(outline_locators),
            "candidate_occurrences": candidate_occurrences,
            "candidate_unique_locators": len(candidate_locators),
            "duplicate_candidate_occurrences": candidate_occurrences - len(candidate_locators),
            "matched_unique_locators": len(matched),
            "missing_outline_locators": len(outline_locators - candidate_locators),
            "unexpected_candidate_locators": len(candidate_locators - outline_locators),
            "exact_outline_page_matches": exact_page_matches,
            "near_outline_page_matches": near_page_matches,
            "far_only_outline_matches": far_only_matches,
            "first_duplicate": numeric_first_duplicate,
        },
        "appendix_hierarchy": {
            "outline_top_level_appendices": len(top_level_outline_appendices),
            "recognized_top_level_appendices": len(recognized_appendices),
            "outline_native_sublocators": len(appendix_outline),
            "current_appendix_sublocator_candidates": len(current_appendix_sublocators),
        },
        "whole_document_status": status,
        "limitations": [
            "outline locators are used only as a source-safe measurement oracle, not parser input",
            "candidate counts describe current block recognition and do not establish reviewed structural correctness",
            "table, figure, and equation counts are caption or identifier recognition only, not reconstruction or semantics",
            "duplicate_locator_free records only the observed locator-collision gate and does not establish successful whole-document Document AST materialization, validation, or completeness",
        ],
    }
