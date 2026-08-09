# NEC 2017 full layout evidence

Predecessor: `feature/nec-2017-corpus-contract`.

Owns:
- deterministic positioned evidence for the complete retained NEC 2017 PDF;
- PDF/printed-page mapping, reading-order reconstruction, recurring-furniture handling, and source-coordinate provenance;
- stable block/region identity independent of incidental extraction order;
- explicit evidence classes for tables, figures/graphics, notes, annex material, and ambiguous regions without assigning engineering meaning.

Does not own:
- NEC hierarchy inference;
- table cell semantics or figure interpretation;
- Provision AST semantics;
- protected source corpus publication.

Completion:
- every in-scope page can produce deterministic coordinate-bearing evidence tied to the exact artifact;
- known mixed-column and non-prose layouts have source-safe regression coverage;
- repeated extraction produces stable source-region ownership and diagnostics;
- private replay preserves unsupported regions instead of dropping them.

Successor: `feature/nec-2017-complete-hierarchy`.
