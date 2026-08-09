# NEC 2017 non-prose structure

Predecessor: `feature/nec-2017-complete-hierarchy`.

Owns:
- structural recognition and ownership for NEC tables, table continuations, table notes/footnotes, figures, diagrams, and other technical graphical regions;
- publication-native non-prose locators where source designation exists;
- table region, row/column/cell geometry and span evidence without semantic header or engineering-role claims;
- explicit unsupported diagnostics for graphical meaning, ambiguous attachments, and unreconstructable structure.

Does not own:
- table lookup semantics or engineering interpretation;
- figure/diagram semantic interpretation;
- Provision AST calculations;
- external-reference resolution.

Completion:
- the corpus contract's non-prose inventory is structurally accounted for or explicitly unsupported;
- continuations and attached notes preserve deterministic ownership;
- table geometry remains distinct from reviewed semantic roles;
- protected table/figure content is not published in Git.

Successor: `feature/nec-2017-complete-document-ast`.
