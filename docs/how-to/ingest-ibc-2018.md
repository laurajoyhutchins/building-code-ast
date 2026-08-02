# Ingest a Local 2018 IBC PDF

## Purpose

This procedure generates private ChapterSeed JSON files from the supported chapters of a locally supplied 2018 International Building Code PDF. Each seed contains a source manifest, normalized chapter text, positioned PDF fragments, layout-analysis evidence, and a validated document AST.

The command does not determine which edition is legally controlling, interpret compliance, resolve cross-references, or publish the source material.

## Install the optional adapter

Use Python 3.12 from the repository root:

```bash
python -m pip install -e '.[ibc-pdf]'
```

The base package has no runtime dependencies. The optional extra installs PyMuPDF only for local PDF layout extraction.

## Run the bounded seed

```bash
python scripts/ingest_ibc_2018.py /path/to/icc-2018.pdf \
  --output-dir generated-private/ibc-2018
```

The bounded slice produces Chapters 1, 2, and 3. The supported source has no usable outline and exposes individually positioned glyphs instead of ordinary words, so the adapter uses verified physical page ranges. Unsupported chapter numbers fail closed rather than guessing boundaries.

Select a subset with:

```bash
python scripts/ingest_ibc_2018.py /path/to/icc-2018.pdf \
  --output-dir generated-private/ibc-2018 \
  --chapters 1,2
```

The command refuses to replace a nonempty output directory. Add `--force` only after confirming that the directory contains this generator's disposable output.

## Output

The output directory contains:

- `manifest.json`: source checksum, edition identity, extractor identity, seed version, layout-analysis version, reconstruction method, and chapter file list;
- `chapter-<number>.json`: source map, private layout evidence, document AST, diagnostics, and structural counts for one chapter.

Source identity is edition-scoped:

```text
artifact_id: icc:ibc
edition_id: 2018:pdf:sha256:<exact PDF digest>
```

The manifest records the file name but not the absolute local path. ChapterSeed `0.2.0` adds private layout evidence while the public Document AST remains at `0.1.0`.

## Private-output boundary

Generated JSON may reproduce IBC source expression. Keep the PDF and generated files in `local-sources/`, `generated-private/`, encrypted storage, or another access-controlled location. Do not add them to public Git, issues, pull requests, CI artifacts, or documentation examples.

Only project-authored ingestion code, synthetic fixtures, checksums, source locators, diagnostics, and documentation belong in the public repository unless a separate publication review establishes a lawful basis.

## Structural behavior

The extractor:

1. reads only the verified physical page ranges for supported chapters;
2. reconstructs visual lines from individually positioned glyphs and preserves font and bounding-box evidence;
3. detects recurring headers and footers across each selected chapter and removes a line only when both its normalized structure and margin position support removal;
4. estimates the body font and records heading evidence without replacing IBC-specific heading rules;
5. infers page-local reading order from stable line-start clusters, falling back to top-to-bottom when two columns are not supported;
6. excludes publisher user-note commentary while retaining an explicit removal reason for every excluded line;
7. reconstructs announced ruled tables from vector boundaries into deterministic base-grid rows and cells;
8. classifies chapter, part, section, provision, note, list, definition, paragraph, heading, table, and unsupported structures;
9. proves that every retained visual line is consumed exactly once and that block, row, cell, fragment, source-map, and AST spans round-trip.

Confidence values and evidence identifiers are review aids. They are not probabilities, code interpretations, or legal reliability claims. Table reconstruction is structural only and does not infer semantic row spans, column spans, units, applicability, or regulatory meaning.

## Exhaustive source audit

A parser change is not cleared by structural counts alone. For the bounded source, the private audit should enumerate every retained and excluded fragment and match it back to the source by physical page, PDF block number, bounding box, and glyph content. It should also verify one-time line consumption, column order, table-cell partitioning, serialized row and cell provenance, source-map spans, and nested Document AST spans.

For independent extraction checks, compare the parser's compact glyph sequence with both PyMuPDF word extraction and Poppler word boxes. Any disagreement supported by both independent readings requires review. Deliberate character normalization, such as mapping a known private-use glyph to its displayed mathematical symbol, must be counted explicitly rather than hidden as a match.

The parser uses geometry-aware character spacing, baseline-connected superscript and subscript attachment, and source-derived word-boundary and line-hyphenation evidence. These rules remain conservative: they use evidence present in the selected source slice and do not import a general dictionary or silently rewrite unsupported ambiguities.

## Known limitations

The adapter supports Chapters 1 through 3 only. It does not infer arbitrary chapter boundaries, interpret revision markings, resolve definitions or references, or convert provisions into semantic rules. Ruled tables are projected onto the finest stable boundary grid; merged visual headers remain base-grid cells rather than inferred semantic spans. Ambiguous non-ruled table layouts remain visible with diagnostics instead of being guessed.

## Verify generated seeds without displaying source text

A private validation process should check:

- source SHA-256, size, edition identity, and page count;
- chapter number, title, physical page range, and output file name;
- recurring-furniture removal counts and page-order modes;
- source-map and document AST span round-tripping;
- exact retained-line and fragment consumption;
- expected definition-entry presence in Chapter 2;
- ruled table, row, and cell counts in Chapter 3;
- explicit diagnostics for any ambiguous table-like layout.

Avoid printing source text in shared logs.
