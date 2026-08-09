# NEC 2017 definition graph

Predecessor: `feature/provenance-graph-core`.
Sibling dependency before whole-edition population: `feature/nec-2017-structural-measurement`.

Owns:
- projecting NEC Article 100 and other structurally recognized definition scopes into the generic provenance graph;
- stable definition identities, alternate terms, scope/applicability qualifiers, source locators, and exact evidence;
- definition-use candidates with resolved, unresolved, and ambiguous states;
- preservation of cycles and multiple plausible definitions without forced selection.

Does not own:
- semantic applicability to a project;
- reference graph population beyond definition relationships;
- Provision AST rule interpretation;
- copying NEC definition prose into public graph artifacts.

Completion:
- all structurally recognized NEC definitions receive deterministic graph identity or explicit unsupported disposition;
- definition-use candidates preserve ambiguity and scope evidence;
- graph output remains non-reconstructive and exact-source linked;
- private whole-edition replay validates graph determinism.

Successor: `feature/nec-2017-reference-graph`.
