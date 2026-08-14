# Retained PDF inspection

`building_code_ast.pdf_inspection` is the publication-neutral lower boundary for factual inspection of retained PDF bytes.

It answers physical questions about an exact local PDF without deciding what publication the bytes represent or what any extracted content means.

## What the shared boundary owns

`inspect_retained_pdf(...)` verifies and reports:

- regular-file rather than symlink input;
- expected byte length;
- SHA-256 of the exact bytes actually read;
- stability of file identity, size, and modification time across hashing;
- PDF page count and version;
- encryption/password state and raw permissions;
- source-safe page-label rules;
- outline entry/depth/target counts without retaining titles;
- pages with and without embedded text;
- aggregate page geometry;
- inspection tool identity.

`PageSurfaceObservation` and `summarize_image_only_pages(...)` additionally describe whether component pages have embedded text and whether image-only pages are represented by a single near-full-page raster image.

These records contain no publication title, edition, printing, component meaning, locator grammar, normative/commentary role, or semantic interpretation.

## What stays publication-specific

Publication adapters wrap these facts with publication identity and verified coordinates. For example, `aisc_scm15_source_verification` continues to own the AISC Steel Construction Manual filename, expected artifact size, publication key, and operator-verified component ranges. Its receipt shape remains the publication contract; generic inspection is only the factual lower layer.

Likewise, the compatibility module `aisc360_image_only_measurement` re-exports the shared page-surface types so existing AISC callers retain their import path and measurement shape.

## Optional dependency

Install generic PDF inspection support with:

```bash
python -m pip install -e '.[pdf-inspection]'
```

The older source-family extras remain available for compatibility. Shared PDF-layout code reports the generic `pdf-inspection` capability when PyMuPDF is missing rather than naming a particular publication family.

## Source and privacy boundary

The retained PDF itself remains private when its governing source policy requires that. Shared inspection emits hashes, counts, coordinates, geometry, and tool metadata only. It does not retain source prose, outline titles, page images, provider credentials, or private object-store locators.

Exact-source identity still belongs to the retained object and its publication adapter. A generic inspection receipt is factual evidence about bytes, not proof that those bytes are the intended publication and not authority to redistribute them.
