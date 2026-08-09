# NDS 2018 reference graph

Predecessor: `feature/nds-2018-structural-measurement`.

Owns:
- projecting measured NDS structural references into deterministic graph nodes and edges;
- distinct internal section, table, figure, equation, appendix, external-standard, bibliography/reference-list, unresolved, and ambiguous target families;
- exact source evidence and explicit resolution state on every relationship;
- deterministic cycles and traversal diagnostics without treating cycles as semantic equivalence.

Does not own:
- definition-use semantics;
- importing external-standard text;
- semantic table/equation dependencies;
- guessing numeric-looking citations as internal sections.

Completion:
- every measured reference family has an explicit graph disposition;
- resolved targets preserve publication and artifact identity;
- unresolved and ambiguous references remain targetless or explicitly multi-candidate rather than guessed;
- graph serialization and IDs are deterministic independent of discovery order;
- source-safe tests plus private full-document projection verify one disposition per recognized reference.

Successor: `feature/nds-2018-definition-graph`.