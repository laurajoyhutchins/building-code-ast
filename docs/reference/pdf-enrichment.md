# PDF enrichment derivatives

PDF enrichment is an optional source-preserving projection for retained PDF artifacts that lack useful reader-facing affordances. It is not source-object hydration, PDF repair, a generic PDF-to-text facility, or an accessibility claim.

## Authority boundary

The exact retained PDF remains the source artifact. Its source ID, SHA-256, byte length, media type, and page count are verified before any mutation is attempted. Enrichment always writes a separate derivative with its own digest. The derivative never inherits source authority merely because it is easier to search or navigate.

The v1 plan permits four additive operation families:

- invisible searchable text on pages proven to lack usable text;
- outlines derived from explicit structural evidence;
- page-label ranges derived from reviewed printed-page observations;
- descriptive metadata limited to `title`, `author`, `subject`, `keywords`, and `creator`.

Every operation names its evidence origin. Existing features are preserved. Conflicting text, outlines, page labels, or metadata fail closed instead of being replaced.

## Plan and receipt

`schemas/pdf-enrichment-plan.schema.json` defines the closed `pdf_enrichment_plan` v1 contract. Plans may contain source expression and therefore follow the handling boundary of the source evidence used to construct them.

`schemas/pdf-enrichment-receipt.schema.json` defines the source-safe `pdf_enrichment_receipt` v1 contract. Receipts record source and derivative identity, the canonical plan digest, tool versions, mutation summaries, and verification evidence. Searchable text, outline titles, and metadata values are represented in receipts by SHA-256 rather than copied expression.

Recovered raster/OCR expression may enter a searchable-text operation only through the [`recovery-observation-v1`](recovery-observation.md) boundary. A `digest_only` recovery observation proves a text digest but cannot authorize enrichment. A `private_retrievable` observation may be used only after the supplied private payload matches the durable recovered-text digest and carries an explicit PDF-point region. This binding does not promote recovered text to native PDF text or change source authority.

## Materialization

Install the optional runtime:

```bash
python -m pip install -e '.[pdf-enrichment]'
```

Then run:

```bash
PYTHONPATH=src python tools/enrich_pdf.py \
  source.pdf \
  enrichment-plan.json \
  source.enriched.pdf \
  enrichment-receipt.json
```

The v1 runtime uses PyMuPDF to materialize PDF objects and pypdf as an independent structural reader. It does not invoke an OCR engine. Searchable-text entries must already be evidence-backed observations, so OCR acquisition and source-role classification remain upstream concerns.

## Verification

The derivative is placed at the requested output path only after all verification succeeds:

- source digest, byte length, media type, and page count agree with the plan;
- source and output paths are distinct and the source is not rewritten;
- encrypted, repaired, or digitally signed PDFs fail closed in v1;
- pypdf reopens the derivative and validates positive page geometry;
- page count, MediaBox, CropBox, dimensions, and rotation remain unchanged;
- source and derivative rasterize identically page by page under one pinned PyMuPDF render recipe;
- searchable-text target pages gain text while native text on unselected pages is unchanged;
- requested outline, page labels, and metadata match the plan;
- a source `StructTreeRoot` remains present in the derivative.

A failed check removes the temporary derivative before it can be atomically placed at the final output path.

## Explicit non-goals

v1 does not deskew, rotate, crop, recolor, recompress intentionally, force-rasterize, replace existing OCR, repair malformed PDFs, alter signed PDFs, infer publication state, or claim PDF/UA conformance. OCR text remains derived evidence, not native embedded text.