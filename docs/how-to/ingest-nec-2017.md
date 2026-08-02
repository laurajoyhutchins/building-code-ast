# Ingest a Local 2017 NEC PDF

## Purpose

This procedure generates private ArticleSeed JSON files from a locally supplied 2017 NEC PDF. Each seed contains a source manifest, normalized article text, block-level PDF coordinates, and a validated document AST.

The command does not determine which edition is legally controlling, interpret compliance, resolve cross-references, or publish the source material.

## Install the optional adapter

Use Python 3.12 from the repository root:

```bash
python -m pip install -e '.[nec-pdf]'
```

The base package has no runtime dependencies. The optional extra installs PyMuPDF only for PDF layout extraction.

## Run the default seed

```bash
python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf \
  --output-dir generated-private/nec-2017
```

The default article set is `90,100,110`. Select a different bounded set with:

```bash
python scripts/ingest_nec_2017.py /path/to/nec-2017.pdf \
  --output-dir generated-private/nec-2017 \
  --articles 90,100,110,250
```

The command refuses to replace a nonempty output directory. Add `--force` only after confirming that the directory contains disposable generated output.

## Output

The output directory contains:

- `manifest.json`: source checksum, edition identity, extractor identity, and article file list;
- `article-<number>.json`: source map, document AST, diagnostics, and structural counts for one article.

Source identity is edition-scoped:

```text
artifact_id: nfpa:70
edition_id: 2017:pdf:sha256:<exact PDF digest>
```

The manifest records the file name but not the absolute local path.

## Private-output boundary

Generated JSON may reproduce NEC source expression. Keep the PDF and generated files in `local-sources/`, `generated-private/`, encrypted storage, or another access-controlled location. Do not add them to public Git, issues, pull requests, CI artifacts, or documentation examples.

Only project-authored ingestion code, synthetic fixtures, checksums, source locators, diagnostics, and documentation belong in the public repository unless a separate publication review establishes a lawful basis.

## Structural behavior

The extractor:

1. reads the PDF outline to find numeric article bookmarks;
2. extracts coordinate-bearing text blocks;
3. removes recurring page headers and footers;
4. orders two-column pages left column before right column;
5. trims article boundaries using visible `ARTICLE <number>` anchors, including same-page transitions;
6. repairs deterministic line-break hyphenation;
7. classifies headings, sections, notes, exceptions, lists, definitions, paragraphs, and unsupported table-like layout;
8. validates every document AST span against the generated normalized article text.

PDF coordinates remain in a separate source map rather than changing the public document AST contract.

## Known limitations

The first slice does not reconstruct complex tables into rows and cells, infer the meaning of gray revision shading, interpret margin change markers, resolve definitions or references, or convert arbitrary provisions into semantic rules. Table-like text is retained with a diagnostic instead of being silently guessed.

## Verify a generated seed without displaying source text

A private validation script can load each article JSON and check:

- source SHA-256 and edition identity;
- article number and output file name;
- source-map span round-tripping;
- document AST validation;
- expected structural node families;
- definition-entry presence for Article 100.

Avoid printing source text in shared logs.
