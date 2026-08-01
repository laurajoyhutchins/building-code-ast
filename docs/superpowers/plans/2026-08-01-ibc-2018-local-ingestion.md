# IBC 2018 Local Ingestion Implementation Plan

**Goal:** Add a source-free public adapter and generate private validated ChapterSeed files for Chapters 1, 2, and 3 from the supplied 2018 IBC PDF.

**Architecture:** Keep pathological glyph reconstruction inside an IBC-specific optional adapter. Preserve positioned fragments in a separate source map and project logical blocks into the existing Document AST. Publish only code, synthetic tests, and operating documentation.

## Constraints

- The base runtime dependency set remains empty.
- PyMuPDF is isolated in the `ibc-pdf` optional group.
- Public Git contains no IBC text, page images, or generated ChapterSeed files.
- The first production slice is Chapters `1,2,3` only.
- Every normalized AST and source-map span round-trips exactly.
- Publisher user-note commentary is excluded from the regulatory seed.
- Tables remain unsupported with explicit diagnostics.
- Unsupported page ranges and chapters fail closed.

## Tasks

1. Add synthetic tests for positioned-glyph reconstruction and split visual fragments.
2. Implement bounded IBC chapter metadata and page extraction.
3. Implement opening-matter and two-column reading order.
4. Implement commentary trimming, line joining, and conservative logical block classification.
5. Build source manifests, fragment source maps, validated ChapterSeed values, and table diagnostics.
6. Add the local CLI with hashing and safe overwrite behavior.
7. Add the `ibc-pdf` optional dependency and package metadata regression test.
8. Document operation, private-output boundaries, and known limitations.
9. Run the complete source-free unit suite and compile checks.
10. Run a private production smoke test against the exact source artifact and verify generated seed statistics without printing source text.
