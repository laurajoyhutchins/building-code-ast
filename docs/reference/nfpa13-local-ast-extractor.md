# NFPA 13 (2019) local AST extractor

`tools/extract_nfpa13_2019_ast.py` converts an owner-supplied NFPA 13 (2019) PDF into a deterministic, source-linked local bundle. It builds on `extract_nfpa13_2019_hierarchy.py`; the hierarchy extractor remains authoritative for numbered structural identity.

The tool is intentionally local-only. Do not commit the source PDF, canonical source text, table contents, generated AST, or overlay PDFs.

## Requirements

- Python 3.12 or later
- PyMuPDF for local PDF processing
- The NFPA 13 hierarchy extractor in the same `tools/` directory

The verified source artifact has SHA-256:

```text
07c229b70cfdde21c3c67e6918040663c76aec680a0bd8d026392e21e8b81ee5
```

## Run

```bash
python tools/extract_nfpa13_2019_ast.py /path/to/nfpa-2019.pdf \
  --output local-output/nfpa13-2019-source-linked-ast.json \
  --report local-output/nfpa13-2019-source-linked-ast-validation.md \
  --overlays-dir local-output/overlays \
  --overlay-pages 21,169,182,323,489,509
```

The default expected hash fails closed when the input artifact differs. Pass an empty `--expected-sha256` only when deliberately testing another source artifact.

## Pipeline

1. Extract a page-, column-, font-, and bounding-box-aware canonical source stream.
2. Anchor the validated clause hierarchy into that stream.
3. Compute structural ranges using actual ancestry rather than depth alone.
4. Assign every retained non-whitespace source character to exactly one leaf node.
5. Parse paragraphs, nested list items, definitions, notes, exceptions, figures, and unsupported graphical text.
6. Build conservative geometry-backed table heading, row, and cell subtrees.
7. Extract clause, chapter, table, figure, and external NFPA references.
8. Add bounded semantic annotations without producing compliance conclusions.
9. Emit evidence-linked diagnostics and validate the complete bundle.

## Bundle contract

The local envelope is `nfpa13-ast-bundle/0.1.0` and contains:

- source identity and PDF boundaries;
- a `document_tree` AST with deterministic node IDs and exact spans;
- reference and Annex A correspondence relations;
- bounded semantic annotations;
- geometry-derived table matrices;
- source-map locations for rendering and audit;
- aggregate statistics and validation results.

Table and figure interpretation is deliberately conservative. Table rows and cells reflect detected page geometry, not reviewed semantic column meaning. Figure captions are preserved, but image and diagram semantics are reported as unsupported. Semantic annotations are deterministic lexical classifications, remain unreviewed, and are not engineering interpretations or compliance decisions.

## Validation

A complete run fails unless:

- every explicit hierarchy node has a source anchor;
- node locators and deterministic IDs are unique;
- all node and evidence spans reproduce the exact canonical source text;
- every child is contained by its parent;
- resolved relations target nodes or declared aliases;
- every retained non-whitespace character is owned exactly once;
- isolated revision markers do not leak into source blocks.

The verified complete-source run produced 5,100 explicit clauses, 39,566 document nodes, 27,291 source-owning leaves, 223 accepted tables, 3,423 relations, and 15,755 bounded semantic annotations. It emitted 569 evidence-linked diagnostics: 429 unsupported figure interpretations, 84 unresolved references, and 56 table captions whose geometry was preserved without guessed rows or cells. Two complete runs produced byte-identical JSON with SHA-256 `b7aa0e569b29811e93f9ff0fd06cc86dd9607ba6d69e2f0490f095ac0e1186f1`. Aggregate counts are suitable for the public repository; the text-bearing bundle is not.
