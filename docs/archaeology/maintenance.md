# Archaeology maintenance procedure

1. Read current code, schemas, tests, accepted LORE records, and generated outputs before reviewing history.
2. Decide whether a change altered the model, authority boundary, parser family, support claim, validation method, or lifecycle state. Routine patches remain evidence rather than nodes.
3. Update the relevant root narrative in `narratives.md`.
4. Add a new lexicographically ordered Deciduous patch. Do not rewrite accepted historical identifiers merely because current terminology changed.
5. Use stable semantic IDs and UUIDv5 change IDs. Add exact PR, commit, path, and repository ownership evidence. Mark branch-only or unresolved work explicitly.
6. Connect the new node to the cause that made it necessary. Use canonical Deciduous edge types and put the precise causal relation in the rationale.
7. Update `evidence-register.json` when a new PR or external revision is referenced.
8. Regenerate and validate:

```bash
python scripts/validate_archaeology.py --write
python scripts/validate_archaeology.py
python -m unittest tests.test_archaeology -v
```

9. Run the repository's ordinary test suite and inspect the changed-path set. Archaeology maintenance must not silently alter parser behavior, schemas, source datasets, generated private ASTs, deployments, Linear, or downstream repositories.
10. Perform adversarial review for projected-back concepts, complete-edition overclaims, source/process confusion, hidden private dependencies, and open research labeled active.

The graph is causal documentation, not a substitute for accepted LORE knowledge or current code contracts.
