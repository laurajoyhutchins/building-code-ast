# NEC 2017 reference graph

Predecessor: `feature/nec-2017-definition-graph`.

Owns:
- projecting NEC internal Article/section/table/figure references into the generic provenance graph;
- projecting external-standard designation families and Annex A relationships without importing referenced standards;
- explicit resolved, unresolved, ambiguous, nonexistent, external, and cyclic target states;
- stable relationship identity and exact source evidence independent of lexical discovery order.

Does not own:
- semantic meaning of a cited requirement;
- automatic canonicalization beyond supported designation evidence;
- external-standard source ingestion;
- project applicability or compliance.

Completion:
- every structurally discovered reference is represented by a graph edge or explicit unresolved disposition;
- Annex A and in-body designation evidence reconcile without silently collapsing distinct targets;
- internal cycles remain graph cycles rather than parser errors;
- public graph artifacts remain non-reconstructive.

Successor: `feature/nec-2017-graph-reconciliation`.
