# ASHRAE 90.1-2016 whole-document materialization receipt

Canonical roadmap: issue #219.

This gate adds a source-safe receipt for actual publication-adapter materialization plus generic Document AST validation. It does not publish the private AST or source expression and does not claim structural or semantic completeness.

## Exact retained artifact

- SHA-256: `275a343724fce483fc3038b261fb00c0c4a3360d3a54078b92a433aba56ec162`
- size: 3,475,675 bytes
- physical pages: 388

The retained bytes were rehashed before the replay. No source prose, page images, reconstructive tables/figures/equations, generated private AST, provider identifiers, or storage locators are committed.

## Receipt contract

`materialize_ashrae901_2016_document_receipt()`:

1. fails closed unless the supplied SHA-256, byte size, and 388-page layout identity match the exact retained artifact;
2. constructs observations using the same content filter and deterministic source order as the whole-document measurement;
3. calls `parse_ashrae901_2016_observations()`;
4. explicitly calls generic `validate_document_ast()` on the materialized private AST;
5. traverses the validated tree only to derive aggregate node-type and diagnostic-code counts;
6. returns no source text, node payload, source spans, protected expression, or private locator data.

The private AST remains ephemeral.

## TDD evidence

Initial RED head: `0a17dc31e9617b49aacd8c3d32b6dbd9747f26f0`.

Hosted CI ran 566 tests and failed exactly because `materialize_ashrae901_2016_document_receipt` did not yet exist. Every inherited test passed.

GREEN implementation head: `d28d5d80d4b8ff4a43a1bae17ff808660450c5e1`.

Fresh hosted checks on that implementation head:

- CI: success
- LORE: success
- Deciduous archaeology: success

The hosted source-safe test exercises the committed receipt wrapper through real publication-adapter materialization and generic validation using a synthetic 388-page layout. It also asserts that sentinel source expression never appears in the returned receipt.

## Exact-source validator-equivalent replay

The connected execution environment can access the exact private PDF and repository source through the GitHub connector, but it cannot create a network-backed Git checkout or expose the connector's repository archive as local bytes. Therefore the exact-source replay was performed by reproducing the current branch's materialization and generic validator invariants locally rather than importing the branch package directly.

Against all 8,897 retained content-region blocks, that exact-source replay produced:

- total nodes including document root: 8,898
- unique locators: 8,898
- unique deterministic node identities: 8,898
- source-span/text mismatches: 0
- child-outside-parent span violations: 0
- child source-order violations: 0

Source-safe aggregate node counts:

- document: 1
- section: 20
- subsection: 372
- table: 39
- figure: 12
- paragraph: 8,454
- diagnostics: 0

The 20 generic `section` nodes comprise the currently recognized 12 body sections plus 8 top-level appendices. This reflects the current generic Document AST representation; it is not a claim that appendix-native substructure is complete.

## What this establishes

The current post-#251 recognized structure has no observed generic validator failure under the exact-source locator, identity, span, source-order, and containment invariants. The committed wrapper also proves that the publication adapter can materialize and pass generic validation for the source-safe synthetic gate.

This does **not** establish complete exact-source Document AST support. In particular:

- 73 native numeric outline locators remain unmatched by current recognition;
- 251 appendix-native outline sublocators still have 0 current candidates;
- rotated Annex 1 figure captions outside the current content boundary remain unrecovered;
- table, figure, and equation semantics remain unreviewed/unsupported beyond their current structural evidence;
- the exact private source was not imported through the branch package in this environment, so a direct branch-wrapper replay remains a useful local verification step when a repository checkout and retained PDF are colocated.

## Next executable evidence

Do not treat the remaining 73 or 251 locators as parser work merely because they are missing. The next parser change should be selected only after exact-source review classifies those missing families and demonstrates a repeated source-backed recognition deficiency. A direct local invocation of the committed materialization receipt is also an appropriate verification step when the repository checkout and exact retained bytes are available together.
