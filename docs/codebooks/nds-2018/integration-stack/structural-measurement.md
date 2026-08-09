# NDS 2018 structural measurement

Predecessor: `feature/nds-2018-complete-document-ast`.

Owns:
- whole-document factual denominators for NDS structural families;
- aggregate counts for chapters, sections/subsections, appendices, equations, tables, figures, definitions, footnotes/notes, reference families, unsupported regions, and ambiguities where deterministically measurable;
- measured supported/unsupported coverage by structural family without treating generated output as reviewed semantics;
- source-safe aggregate reporting suitable for public Git.

Does not own:
- repairing unsupported structures merely to improve percentages;
- semantic correctness of equations, tables, definitions, or references;
- publication-state reconciliation against another artifact.

Completion:
- every support percentage is backed by an explicit measured denominator;
- counts are reproducible from the complete private Document AST and stable across repeated runs;
- unsupported and ambiguous families are separately reported rather than merged into success;
- the report is non-reconstructive and contains no protected source expression;
- findings identify any structural blocker that must be fixed before semantic work relies on that family.

Successors:
- linear semantic trunk: `feature/nds-2018-reference-graph`;
- parallel evidence sidecar: `feature/nds-2018-publication-state-reconciliation`.