# NEC 2017 structural measurement

Predecessor: `feature/nec-2017-complete-document-ast`.

Owns:
- reproducible whole-publication structural support metrics against the corpus contract;
- counts and rates for hierarchy, definitions, exceptions, notes, tables, figures/graphics, annexes, references, unsupported regions, ambiguities, and source-span failures;
- deterministic source-safe reporting suitable for regression gates;
- prioritization inputs for later semantic review without changing parser output to improve percentages.

Does not own:
- parser repairs merely to satisfy a metric;
- semantic correctness claims;
- review acceptance or Provision AST generation;
- compliance conclusions.

Completion:
- every structural support percentage has an explicit denominator;
- unsupported and ambiguous states are visible in reports;
- repeated reports are deterministic for the same artifact/compiler revision;
- measurement can gate later integration closeout without publishing protected expression.

Successors: NEC graph integration and the parallel NEC 110.26 semantic proof.
