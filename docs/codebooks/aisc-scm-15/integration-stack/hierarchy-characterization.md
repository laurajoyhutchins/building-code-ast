# ANSI/AISC 360-16 hierarchy characterization

This layer measures the retained ANSI/AISC 360-16 derivative without committing protected source text. It is intentionally a characterization gate, not a parser implementation.

The exact 64,464,266-byte derivative has 674 pages: 561 with embedded text and 113 without it. Embedded text exposes the repeated A–N chapter sequence across the specification and commentary, plus a partial set of appendix markers. The committed receipt records only page coordinates and structural identifiers.

Visual inspection of representative image-only pages 243 and 285 establishes that raster-only pages can contain hierarchy-bearing numbered headings, not just figures or decorative material. Therefore an embedded-text-only hierarchy replay would make an unsupported completeness claim.

The smallest next parser boundary is raster text recovery for image-only pages, followed by hierarchy parsing over the combined page stream. This characterization does not itself perform OCR and does not retain source prose.
