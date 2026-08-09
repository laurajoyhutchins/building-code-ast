# NEC-required neutral provenance graph core

Predecessor: current `main`. This is publication-neutral shared infrastructure required by complete NEC integration.

Owns:
- one versioned deterministic graph contract for source-backed definition, reference, and later amendment relationships;
- stable node and edge identity scoped to publication/source artifact;
- resolved, unresolved, ambiguous, cyclic, failed, and conflicting relationship states;
- exact evidence links and graph traversal diagnostics without copying protected expression;
- projection adapters from already-proven source-family graph records where behavior is genuinely common.

Does not own:
- NEC-specific reference discovery;
- definition-use selection or semantic applicability;
- destructive rewriting of Document AST or Provision AST;
- jurisdiction selection or compliance evaluation.

Completion:
- existing IBC/NFPA graph evidence can project without loss of source-specific state;
- synthetic fixtures cover cycles, missing targets, ambiguity, and deterministic serialization;
- original ASTs remain immutable graph inputs;
- generic behavior is not widened beyond behavior proven by concrete source families.

Successor: `feature/nec-2017-definition-graph`; NEC structural measurement is a sibling dependency before real whole-edition graph population.
