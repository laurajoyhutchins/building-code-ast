# Maintain repository documentation

## Purpose
Maintain LORE semantic knowledge from repository evidence without rewriting accepted history.
## Required inputs
Read the provided context packet, exact repository revision, task, records, and evidence.
## Evidence standard
Every factual claim must cite a path at a full commit SHA. Report uncertainty rather than guessing.
## Documentation-impact analysis
Determine whether architecture, decisions, constraints, findings, relationships, or procedures changed.
## Record identity and revision rules
Reuse stable IDs. Append the next positive revision and point `supersedes` to the prior canonical reference.
## Allowed outputs
Return exactly one `lore-proposal/v1` artifact containing append or transition operations.
## No-change outcome
Use `no_documentation_change` with a concrete reason and zero operations.
## Prohibited actions
Never edit generated docs, accepted records, transactions, or extracted facts directly. Never invent evidence.
## Failure conditions
Fail closed on missing evidence, ambiguous identity, stale revisions, schema mismatch, or incomplete context.
## Submission checklist
Validate schema, evidence, next revisions, supersession, uncertainty, and operation/result consistency.
