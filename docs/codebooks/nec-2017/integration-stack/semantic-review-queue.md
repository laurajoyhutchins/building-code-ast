# NEC semantic review queue

Predecessor: `feature/nec-semantic-review-workflow`.
Sibling dependencies for complete queue denominators: `feature/nec-2017-structural-measurement` and `feature/nec-2017-graph-reconciliation`.

Owns:
- deriving a deterministic whole-publication semantic review queue from measured normative structure and graph dependencies;
- prioritization by semantic archetype, unsupported structure, ambiguity, dependency centrality, parser disagreement, and source-span risk;
- coverage reporting by review state and semantic family;
- bounded review-pack generation without turning retrieval rank into semantic confidence.

Does not own:
- automatically accepting queued candidates;
- article-by-article architecture forks;
- changing semantic models merely to reduce queue size;
- project evaluation.

Completion:
- every in-scope normative structural node has a declared semantic review/support state;
- queue ordering is deterministic and evidence-backed;
- coverage denominators are explicit and source-safe;
- review packs can be generated incrementally without pre-creating an unbounded PR forest.

Successors: parallel NEC semantic-archetype coverage branches.
