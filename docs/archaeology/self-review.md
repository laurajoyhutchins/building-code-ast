# Adversarial self-review

## Findings corrected before publication

1. **IBC and NFPA 13 were initially easy to describe as implemented repository capabilities.** Their open draft PRs contain substantial code and source validation, but they are not on `main`. All support nodes were downgraded to `branch-only`; current architecture contains only a limit marker.
2. **The NEC 2020 work could be mistaken for a changelog.** It is an expected-change design based on development records and remains blocked without an authorized 2020 source. The graph now separates process evidence from observed issued text.
3. **The NEC hierarchy oracle could sound like a dependency.** It is explicitly a private local conformance oracle. Output is neither repaired from nor coupled to it.
4. **The NEC Style Manual could be projected as authority over the edition.** It is recorded as an edition-aware parser prior and validation context, never as source repair or controlling code text.
5. **Printed and semantic hierarchy were initially too close.** The graph now distinguishes printed ownership, logical grouping, and normative dependency, including exceptions and distant references.
6. **Tables and figures risked being described uniformly.** Table boundary recovery, table semantics, figure references, and visual interpretation are separate claims. NFPA 13 figure semantics and multiple layout classes remain unresolved.
7. **UL White Book material could be forced into the code AST.** Ownership was assigned to Electrical Equipment Lineage; only a linked-corpus relationship is proposed.
8. **Merged source-evidence adapters conflicted with stale README wording.** Current architecture follows the code and tests; the documentation drift is retained as an explicit gap rather than silently rewriting non-archaeology documentation.
9. **A backward rejected edge created a cycle in the first graph draft.** The edge was reoriented to preserve causal DAG semantics, and a duplicate edge was removed.
10. **Successful fragment validation could imply complete-edition support.** Every claim now carries source family, edition, branch, and bounded support scope.

## Checks applied

- no private source links, credentials, PDFs, prose excerpts, or withheld source hashes;
- no parser, schema, fixture, data, deployment, Linear, or downstream mutation;
- no open PR represented as merged;
- no source-family rule represented as universal without evidence;
- no generated projection represented as canonical source;
- no technical AST represented as legal authority;
- no duplicate semantic IDs or typed edges;
- DAG acyclicity and deterministic generation.
