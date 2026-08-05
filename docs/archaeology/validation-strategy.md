# Validation-strategy map

## Structural invariants

- deterministic node identity from declared source identity and locator;
- exact source-span equality and in-bounds offsets;
- child spans contained by parent spans;
- unique identities and locators within their contract;
- legal parent-child types and source-order preservation;
- marker ancestry and numbering continuity where the family grammar defines them;
- explicit diagnostics for unsupported or ambiguous structures.

## Source comparison

- fragment-by-fragment comparison against the supplied source location;
- representative golden cases for clauses, definitions, exceptions, lists, notes, tables, figures, and references;
- private exact-source replay without committing source expression;
- independent known-good references used as conformance oracles, never output-repair dependencies;
- official errata, development, and amendment corpora tested against exact source bytes where redistribution permits;
- human review of failures and boundary cases.

## Edition comparison

Run each edition independently. Compare normalized structural identities only after each parser has passed its own source checks. Classify mismatches as:

- observed source change;
- expected change supported by process evidence but not yet observed;
- extraction or hierarchy defect;
- layout ambiguity;
- source absence or rights blockage;
- unresolved.

## Support-claim rule

A passing synthetic fixture proves the fixture. A passing selected source region proves that region and construct. A passing branch proves the branch at its exact head. Complete-edition support requires complete-source coverage, explicit unsupported-construct accounting, deterministic replay, and independent review. Merge state and current tests govern current support labels.

## Commands

```bash
python scripts/validate_archaeology.py --write
python scripts/validate_archaeology.py
python -m unittest tests.test_archaeology -v
python -m unittest discover -s tests -v
```
