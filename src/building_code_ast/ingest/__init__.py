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
from .nec_hierarchy import (
    HIERARCHY_VERSION,
    HierarchyBuildResult,
    HierarchyConformanceReport,
    HierarchyMismatch,
    HierarchyRecord,
    build_nec_hierarchy,
    canonical_nec_locator,
    compare_hierarchy,
    flatten_nec_hierarchy,
    load_clause_oracle,
    nec_locator_depth,
    nec_parent_locator,
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
    "HIERARCHY_VERSION",
    "ArticleRange",
    "ArticleSeed",
    "HierarchyBuildResult",
    "HierarchyConformanceReport",
    "HierarchyMismatch",
    "HierarchyRecord",
    "PdfBlock",
    "PdfLayoutDocument",
    "PdfOutlineItem",
    "PdfPage",
    "SourceManifest",
    "SourceMapEntry",
    "build_article_seed",
    "build_nec_hierarchy",
    "canonical_nec_locator",
    "compare_hierarchy",
    "discover_article_ranges",
    "extract_pdf_layout",
    "flatten_nec_hierarchy",
    "load_clause_oracle",
    "nec_locator_depth",
    "nec_parent_locator",
    "normalize_block_text",
    "order_content_blocks",
    "select_article_blocks",
]
