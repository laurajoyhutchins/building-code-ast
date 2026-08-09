# ACI 318-19 region classification

Predecessor: `feature/aci-318-19-whole-document-spine`.

Owns:
- deterministic classification of Code, Commentary, shared publication structure, recurring headers/footers, page numbers, and other page furniture;
- source-role recognition from exact positioned evidence rather than extracted text order or prose style;
- explicit ambiguous/full-width region diagnostics;
- source-safe synthetic tests plus private replay against representative mixed-layout pages.

Does not own:
- cross-page hierarchy repair;
- equation/table/figure semantics;
- semantic provision parsing.

Completion:
- recurring furniture is distinguished from publication content without deleting provenance;
- normative and commentary regions remain structurally distinct;
- unresolved cross-gutter content is measured rather than guessed;
- repeated classification is deterministic.

Successor: `feature/aci-318-19-cross-page-hierarchy`.
