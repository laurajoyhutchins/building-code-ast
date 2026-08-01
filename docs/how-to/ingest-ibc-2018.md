# Ingest a Local 2018 IBC PDF

## Purpose

This procedure generates private ChapterSeed JSON files from the supported chapters of a locally supplied 2018 International Building Code PDF. Each seed contains a source manifest, normalized chapter text, positioned PDF fragments, and a validated document AST.

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

The first bounded slice produces Chapters 1, 2, and 3. The supplied PDF has no usable outline and exposes individual positioned glyphs instead of ordinary words, so the adapter is deliberately tied to the verified physical page ranges in this edition. Unsupported chapter numbers fail closed rather than guessing page boundaries.

Select a subset with:

```bash
python scripts/ingest_ibc_2018.py /path/to/icc-2018.pdf \
  --output-dir generated-private/ibc-2018 \
  --chapters 1,2
```

The command refuses to replace a nonempty output directory. Add `--force` only after confirming that the directory contains this generator's disposable output.

## Output

The output directory contains:

- `manifest.json`: source checksum, edition identity, extractor identity, reconstruction method, and chapter file list;
- `chapter-<number>.json`: source map, document AST, diagnostics, and structural counts for one chapter.

Source identity is edition-scoped:

```text
artifact_id: icc:ibc
edition_id: 2018:pdf:sha256:<exact PDF digest>
```

The manifest records the file name but not the absolute local path.

## Private-output boundary

Generated JSON may reproduce IBC source expression. Keep the PDF and generated files in `local-sources/`, `generated-private/`, encrypted storage, or another access-controlled location. Do not add them to public Git, issues, pull requests, CI artifacts, or documentation examples.

Only project-authored ingestion code, synthetic fixtures, checksums, source locators, diagnostics, and documentation belong in the public repository unless a separate publication review establishes a lawful basis.

## Structural behavior

The extractor:

1. reads only the verified physical page ranges for supported chapters;
2. reconstructs visual lines from individually positioned glyphs;
3. removes recurring headers and footers;
4. merges split same-baseline fragments without merging distant table columns;
5. reads opening matter top-to-bottom, then two-column body text left before right;
6. excludes publisher user-note commentary while retaining chapter and code headings;
7. repairs deterministic line-break hyphenation;
8. classifies chapter, part, section, provision, note, list, definition, paragraph, heading, and unsupported table-like structures;
9. validates every document AST span against the normalized chapter text.

Complex tables remain visible as unsupported structures with diagnostics rather than being silently reconstructed into cells.

## Known limitations

The first slice supports Chapters 1 through 3 only. It does not infer arbitrary chapter boundaries, reconstruct complex tables, interpret revision markings, resolve definitions or references, or convert provisions into semantic rules. Glyph reconstruction can preserve extraction artifacts that are ambiguous in the PDF text layer; coordinates and fragments remain attached for review.

## Verify generated seeds without displaying source text

A private validation process should check:

- source SHA-256, size, edition identity, and page count;
- chapter number, title, physical page range, and output file name;
- source-map span round-tripping;
- document AST validation;
- expected definition-entry presence in Chapter 2;
- explicit diagnostics for retained table-like layout in Chapter 3.

Avoid printing source text in shared logs.
