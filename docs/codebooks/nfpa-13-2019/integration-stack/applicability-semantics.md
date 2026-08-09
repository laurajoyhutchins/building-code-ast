# NFPA 13 (2019) applicability semantics

Predecessor: `feature/nfpa13-definition-graph` (PR #76)

Owns:
- the issue #3 applicability/scope vocabulary required by reviewed NFPA 13 clauses;
- structural ownership of introductory scope over nested clauses and lists;
- exact source spans for applicability evidence;
- explicit unsupported or ambiguous applicability states;
- parser inference and review-state separation for applicability candidates.

Does not own:
- exception semantics;
- definition resolution beyond the predecessor graph;
- table, calculation, or figure meaning;
- project-specific applicability, system design, compliance, or legal conclusions.

Completion:
- synthetic fixtures cover nested applicability and scope inherited across structural owners;
- ambiguous ownership fails closed with retained evidence;
- Provision AST compatibility/versioning is documented;
- reviewed NFPA cases demonstrate that sentence boundaries are not treated as rule boundaries.

Successor: `feature/nfpa13-exception-semantics`.
