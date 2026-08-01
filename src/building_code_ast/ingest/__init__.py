"""Local source-ingestion helpers.

The modules in this package preserve source structure and provenance. They do
not decide code applicability or compliance.
"""

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
    "PdfBlock",
    "PdfLayoutDocument",
    "PdfOutlineItem",
    "PdfPage",
    "SourceManifest",
    "SourceMapEntry",
    "build_article_seed",
    "discover_article_ranges",
    "extract_pdf_layout",
    "normalize_block_text",
    "order_content_blocks",
    "select_article_blocks",
]
