"""Bounded, provenance-preserving 2018 IBC PDF ingestion."""

from .models import (
    CHAPTER_SPECS, EXTRACTOR_ID, EXTRACTOR_VERSION, LAYOUT_ANALYSIS_VERSION, SEED_VERSION,
    ChapterLayout, ChapterLayoutAnalysis, ChapterSeed, ChapterSpec, IbcLayoutDocument, LogicalBlock, SourceManifest, SourceMapEntry,
)
from .pipeline import coalesce_visual_lines, extract_ibc2018_layout
from .projection import build_chapter_seed
from .text import merge_visual_fragments, order_page_lines, parse_chapter_numbers, reconstruct_glyph_line
from ..layout_analysis import SourceFragment, VisualLine

__all__ = [
    "CHAPTER_SPECS", "EXTRACTOR_ID", "EXTRACTOR_VERSION", "LAYOUT_ANALYSIS_VERSION", "SEED_VERSION",
    "ChapterLayout", "ChapterLayoutAnalysis", "ChapterSeed", "ChapterSpec", "IbcLayoutDocument", "LogicalBlock",
    "SourceFragment", "SourceManifest", "SourceMapEntry", "VisualLine", "build_chapter_seed", "coalesce_visual_lines",
    "extract_ibc2018_layout", "merge_visual_fragments", "order_page_lines", "parse_chapter_numbers", "reconstruct_glyph_line",
]
