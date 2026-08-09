# Complete ACI 318-19 Document AST

Predecessor: `feature/aci-318-19-notes-figures-appendices`.

Owns:
- whole-document private execution across the exact retained ACI artifact;
- complete source-region accounting, source-span round-trip, deterministic serialization, and generic Document AST validation;
- explicit unsupported, malformed, uncertain, and ambiguous structural states;
- source-role preservation across hierarchy, equations, tables, figures, definitions, references, notes, and appendices;
- repeated-run determinism of the generated private Document AST bundle.

Does not own:
- semantic interpretation of provisions or non-prose structures;
- support percentages without measured denominators;
- publication-state reconciliation against another copy.

Completion:
- every retained source region is accounted for as supported structure, excluded artifact-local evidence, or explicit diagnostic/unsupported structure;
- Code and Commentary never collide in authority or identity;
- all node IDs and spans validate and round-trip;
- two complete exact-source runs are structurally and serialization deterministic;
- no protected generated AST is committed.

Successor: `feature/aci-318-19-structural-measurement`.
