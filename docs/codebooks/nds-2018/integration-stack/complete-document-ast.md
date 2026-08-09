# Complete NDS 2018 Document AST

Predecessor: `feature/nds-2018-nonprose-structure`.

Owns:
- whole-document private execution across all 206 PDF pages of the exact retained artifact;
- complete source-region accounting, source-span round-trip, ownership, deterministic serialization, and generic Document AST validation;
- explicit unsupported, malformed, uncertain, and ambiguous regions rather than coercion into supported structure;
- repeated-run determinism of the generated private Document AST bundle;
- source-safe aggregate diagnostics and verification receipts.

Does not own:
- semantic interpretation of provisions, equations, tables, figures, definitions, or references;
- support percentages without measured denominators;
- publication-state reconciliation against another copy.

Completion:
- every retained source region is accounted for as supported structure, excluded artifact-local evidence, or explicit diagnostic/unsupported structure;
- all node IDs and spans validate and round-trip;
- two complete runs against the exact retained bytes are structurally and serialization deterministic under the declared contract;
- no protected generated AST is committed;
- remaining structural failures are enumerated rather than hidden.

Successor: `feature/nds-2018-structural-measurement`.