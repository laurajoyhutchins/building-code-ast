# NFPA 13 (2019) Provision AST adapter

Predecessor: `feature/nfpa13-calculation-semantics` (PR #81)

Owns:
- the NFPA-family adapter from validated Document AST structure into generic Provision AST candidates;
- supported NFPA clause shapes using applicability, exceptions, definitions, references, comparisons, actions, and calculations established by predecessors;
- structural owner preservation across introductory prose, nested clauses, and lists;
- exact source spans, parser method/revision, diagnostics, and review state;
- explicit unsupported candidates when generic semantics cannot represent the source faithfully.

Does not own:
- a competing NFPA-only semantic model;
- sentence-by-sentence flattening;
- automatic promotion of generated candidates to reviewed semantics;
- project compliance, sprinkler design, hydraulic conclusions, adoption, or jurisdiction.

Completion:
- synthetic fixtures cover plain requirements, scoped requirements, nested lists, exceptions, definition/reference dependencies, and a table/calculation dependency;
- unsupported structures retain source evidence and diagnostics;
- generated and reviewed authority states remain distinct;
- private exact-source replay demonstrates deterministic candidate generation for bounded reviewed NFPA clause shapes.

Successor: `feature/nfpa13-semantic-review-workflow`.
