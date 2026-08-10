# NEC 2017 whole-publication structural measurement

Canonical roadmap: issue #219.

This gate measures the current NEC 2017 structural classifier against the exact retained artifact. It does not add recognition behavior or claim structural, semantic, reviewed, or engineering completeness.

## Exact retained artifact

- private retained file: `nec-2017.pdf`
- size: 7,422,245 bytes
- SHA-256: `603ef5c461247bacd716e3953222bfb227f1ddc780fffdbfcb90756b02c237c7`
- physical pages: 881
- media type: `application/pdf`
- encryption: none

No protected source text, page image, reconstructive table, or extracted corpus is committed.

## Measurement contract

`src/building_code_ast/nec2017_corpus.py` reuses the existing NEC article discovery, article selection, and block classifier. It records only source-safe aggregate counts and boundary metadata.

The report deliberately does not turn a recognized block into a semantic-coverage claim. The current NEC block classifier also has no explicit ambiguous structural state, so ambiguity is reported as unavailable rather than silently encoded as zero.

## Exact-source text-layer replay

A private whole-artifact replay against the exact retained bytes produced:

- numeric article outline denominator: 156
- chapter outline roots: 9
- informative annex outline roots: 10
- observed numeric articles: 156
- article selection failures: 0
- retained article source blocks after boundary correction for measurement: 17,820
- current-classifier recognized blocks: 17,655
- current-classifier unsupported blocks: 165
- current-classifier ambiguous blocks: unavailable with the present classifier contract

Current classifier output by structural type:

- definition entries: 239
- headings: 664
- list items: 2,585
- notes/exceptions: 2,506
- paragraphs: 4,883
- sections: 3,016
- subsections: 3,762
- unsupported: 165

These counts are observations of current classifier behavior, not validated counts of all structures present in the publication.

## Concrete boundary defect exposed by replay

The numeric-article selector has one whole-publication boundary defect visible in this measurement:

- Article 840 starts at PDF page 677;
- because it is the final numeric article, its current scan range extends to PDF page 881;
- the next structural outline root is Chapter 9 at PDF page 682;
- Chapter 9, annex, and later material can therefore survive the current final-article selection unless the measurement layer trims at that observed successor.

The measurement reports this as one boundary issue and trims successor material only for source-safe counting. It does **not** change `select_article_blocks()` in this PR. Fixing the final-article boundary is now a concrete evidence-backed implementation task rather than a planned descendant reservation.

## Table geometry boundary

The exact PDF text-layer replay completed in this runtime. A whole-document PyMuPDF `find_tables()` enrichment pass did not: the table finder exceeded the execution ceiling when applied across the publication.

Therefore the 165 unsupported count is a text-layer/current-classifier observation and is **not** claimed as the whole-publication table-region denominator. Table geometry remains separately evidenced by the already-landed NEC 110.26 exact-source slice (#61), where one announced geometric table region was promoted and one geometric coincidence remained unpromoted.

A later whole-layout evidence task should run only when the table-geometry pass can execute to completion. No table count is guessed here.

## TDD evidence

Branch convergence onto then-current `main`: `172c9dde26f15b53f1180d4478351f4bbe77a040`.

Initial RED head: `1a21031d160b0074970290e9cbb7530457a3e04f`. CI and Deciduous failed because the measurement module did not exist; LORE passed.

Initial implementation: `3cc06d6027302c60846d777206445e4a6ca49abc`.

Exact-source replay then exposed an evidence-quality defect in the measurement itself: safe same-page chapter transitions were being reported as boundary issues. A second RED test was added at `22fb28cf8e469916b79b084c59c2435de2964c52`; CI ran 457 tests and failed on the intended safe-transition distinction plus an explicit-zero serialization case.

Corrected GREEN implementation: `c193eb236ab3f6bba7a46e9966a3f4b74375f9fd`.

Fresh hosted checks on that implementation head:

- CI: success
- LORE: success
- Deciduous archaeology: success

## Boundaries and next executable work

This PR owns measurement, not the parser fix. It does not add PDF extraction behavior, hierarchy recognition, graph resolution, Provision AST semantics, table lookup meaning, compliance, or project evaluation.

The first concrete successor justified by this replay is the final-numeric-article boundary correction in `select_article_blocks()`, with Article 840 as the exact-source counterexample. Whole-document table-geometry measurement is a separate evidence gate whose retry condition is an execution environment where the complete table-finder pass can finish.
