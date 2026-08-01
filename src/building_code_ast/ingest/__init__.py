"""Local source-ingestion helpers.

The modules in this package preserve source structure and provenance. They do
not decide code applicability or compliance.
"""

from .ibc2018 import (
    CHAPTER_SPECS,
    ChapterLayout,
    ChapterSeed,
    ChapterSpec,
    IbcLayoutDocument,
    LogicalBlock,
    SourceFragment,
    VisualLine,
    build_chapter_seed,
    coalesce_visual_lines,
    extract_ibc2018_layout,
    merge_visual_fragments,
    order_page_lines,
    parse_chapter_numbers,
    reconstruct_glyph_line,
)
from .nec2017 import (
    ArticleRange,
    ArticleSeed,
    SourceManifest,
    SourceMapEntry,
    build_article_seed,
    discover_article_ranges,
    select_article_blocks,
)
from .pdf_layout import (
    PdfBlock,
    PdfLayoutDocument,
    PdfOutlineItem,
    PdfPage,
    extract_pdf_layout,
    normalize_block_text,
    order_content_blocks,
)

__all__ = [
    "ArticleRange",
    "ArticleSeed",
    "CHAPTER_SPECS",
    "ChapterLayout",
    "ChapterSeed",
    "ChapterSpec",
    "IbcLayoutDocument",
    "LogicalBlock",
    "PdfBlock",
    "PdfLayoutDocument",
    "PdfOutlineItem",
    "PdfPage",
    "SourceFragment",
    "SourceManifest",
    "SourceMapEntry",
    "VisualLine",
    "build_article_seed",
    "build_chapter_seed",
    "coalesce_visual_lines",
    "discover_article_ranges",
    "extract_ibc2018_layout",
    "extract_pdf_layout",
    "merge_visual_fragments",
    "normalize_block_text",
    "order_content_blocks",
    "order_page_lines",
    "parse_chapter_numbers",
    "reconstruct_glyph_line",
    "select_article_blocks",
]
