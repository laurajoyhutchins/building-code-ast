# NFPA 13 (2019) table semantics contract

Predecessor: `feature/nfpa13-exception-semantics` (PR #78)

Owns:
- the generic table-lookup semantic contract required by reviewed NFPA 13 cases;
- explicit separation of table-region detection, cell geometry, header/span interpretation, semantic roles, and lookup derivation;
- units, merged headers, spanning cells, footnotes, qualifications, and ambiguity states;
- exact provenance from selected semantic values back to row/column evidence.

Does not own:
- broad NFPA table interpretation;
- automatic engineering calculations;
- figure/diagram semantics;
- compliance or sprinkler-design conclusions.

Completion:
- JSON/model contract is defined before source-family interpretation;
- synthetic fixtures cover merged headers, spanning cells, units, footnotes, and ambiguous header relationships;
- ambiguous tables fail closed without invented semantic columns;
- lookup outputs preserve the derivation path explaining row and column selection.

Successor: `feature/nfpa13-table-reviewed-slice`.
