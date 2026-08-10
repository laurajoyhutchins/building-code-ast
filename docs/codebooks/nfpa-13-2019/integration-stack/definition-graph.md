# NFPA 13 (2019) definition graph

Predecessor: landed NFPA reference graph PR #60.

This PR owns a deterministic, source-safe projection of already-recognized NFPA 13 definition entries and reviewed definition-use candidates. It does not discover terms lexically or decide applicability, compliance, or engineering meaning.

## Exact retained source

The private retained artifact used for the bounded review is the same artifact hard-pinned by `tools/extract_nfpa13_2019_ast.py`:

- private filename: `nfpa-2019.pdf`
- size: 49,070,148 bytes
- SHA-256: `07c229b70cfdde21c3c67e6918040663c76aec680a0bd8d026392e21e8b81ee5`
- physical PDF pages: 3,853
- NFPA 13 structural extraction range: PDF pages 21 through 513
- media type: `application/pdf`
- encryption: none

No source prose, definition text, use-site text, page image, table, or reconstructive corpus is committed.

## Implemented boundary

`tools/extract_nfpa13_2019_ast.py` already recognizes Chapter 3 structural `definition_entry` nodes. This PR starts downstream of that recognition.

`src/building_code_ast/nfpa13_definition_graph.py` projects normalized definition records and candidate-use relationships with:

- stable publication-scoped identities;
- definition scope locators;
- opaque term keys;
- explicit candidate definition locators;
- `resolved`, `ambiguous`, and `unresolved` states;
- source-stream start/end evidence coordinates with source expression removed from public output;
- fail-closed duplicate and unknown-candidate validation;
- deterministic ordering and cycle representability.

## Bounded exact-source review

The exact retained PDF was read through the existing NFPA 13 source-stream rules: artifact furniture was filtered, retained lines were ordered by PDF page/column/geometry, and source offsets were assigned exactly as the production extractor does.

Two source-backed cases were reviewed privately and projected without committing their expression.

### Reviewed case A: unique candidate

- opaque term key: `term:sha256:5bc9ed47734fd40d0780b38fac15b88fe3179f6a9bdd18296143982ba965e1ba`
- definition structural owner: `3.3.46`
- definition leaf: `3.3.46#segment1#p1`
- definition source-stream span: `[35165, 35266)`
- definition PDF page: 27
- reviewed use structural owner: `6.10.2.4.3`
- reviewed use leaf: `6.10.2.4.3#segment1#p1`
- use evidence span: `[134792, 134806)`
- use PDF page: 51
- candidate definition locators: one
- projected resolution state: `resolved`

The review establishes only that this bounded use candidate maps uniquely to the reviewed Chapter 3 definition entry. It does not establish a general lexical-use detector.

### Reviewed case B: redirect plus substantive definition

- opaque term key: `term:sha256:39dbb4a5b38973b6cab8e9cfde4c2f40f946e177eaab2adcaa73ce263e8f899c`
- first Chapter 3 definition leaf: `3.3.177#segment1#p1`
- first definition source-stream span: `[59164, 59214)`
- first definition PDF page: 32
- second Chapter 3 definition leaf: `3.3.205.4.17#segment1#p1`
- second definition source-stream span: `[69192, 69509)`
- second definition begins on PDF page: 33
- reviewed use leaf: `7.2.2.4#segment1#p1`
- use evidence span: `[139228, 139250)`
- use PDF page: 52
- candidate definition locators: two
- projected resolution state: `ambiguous`

The first definition entry redirects to the second substantive definition. The projection deliberately preserves both reviewed candidates rather than silently collapsing the redirect relationship into an authoritative definition choice. That is a real exact-source validation of the graph's ambiguity state.

The private source-bearing inputs were projected through the PR contract. Public projection contained the expected source-safe spans/candidate locators and did not contain either reviewed term expression.

## Verification history

- TDD RED head: `f16f8a584fb149844183c991131fbf8a1261ca64`, where repository tests failed before the production module existed.
- GREEN implementation head: `ca6bbdea0ff0b65a59f6d41455916115772986f4`.
- prior final implementation head: `4da00a455e77ac2ef07cb95cee5514b3dce89d70`.
- convergence onto current shared/compiler work before exact-source receipt: `a4852bf0094cae6800551a4bdb8d5aa8023834aa`.

Synthetic tests cover resolved, unresolved, ambiguous, duplicate, unknown-target, deterministic-order, source-text-boundary, and cyclic cases. The bounded exact-source review above now closes the previously stated private review gate without expanding source recognition behavior.

## Boundaries

This PR does not own:

- lexical discovery of definition uses;
- automatic redirect resolution;
- applicability or exception semantics;
- table or calculation meaning;
- amendment, jurisdiction, adoption, compliance, or sprinkler-design conclusions;
- generic migration merely because the shared provenance graph now exists.

The next NFPA work should proceed through the already-open applicability gate only after this definition projection lands and that branch is converged onto the resulting `main`.