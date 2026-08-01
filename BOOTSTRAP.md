# LORE bootstrap trust root

LORE begins with a small hand-authored kernel: `lore.yaml`, schemas, the neutral maintenance skill, implementation code, and initial reviewed semantic records. Source code, schemas, accepted records, transactions, and the skill are authoritative. README and `docs/generated/` are projections and can be recovered with `lore project`. Extracted facts can be recovered with `lore extract`.

Accepted records are append-only. Changes arrive as one `lore-proposal/v1` artifact, are validated against exact Git evidence, planned in memory, and applied transactionally. Run `lore verify-self` to check the trust root, records, evidence, projections, hydration, history, and determinism. The unavoidable limitation is that the first kernel is reviewed by humans before LORE can describe itself.
