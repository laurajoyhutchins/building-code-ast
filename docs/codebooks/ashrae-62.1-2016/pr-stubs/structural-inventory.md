# ASHRAE 62.1-2016 structural inventory

Status: draft PR scaffold; implementation not started.

## Depends on

`ashrae-62.1-2016/publication-apparatus`

## Purpose

Produce the first whole-document structural measurement with real denominators for later support claims.

## Scope

- whole-document private execution
- counts for sections, subsections, appendices, tables, equations/calculation regions, figures, definitions, exceptions, notes, footnotes, references, unsupported structures, and ambiguities where detectable
- recognized versus unsupported ratios
- repeated-run determinism
- source-safe aggregate reporting only

## Boundaries

Do not infer semantic coverage from structural recognition and do not commit reconstructive source content.

## Completion gate

The exact retained artifact produces deterministic source-safe aggregate measurements that can bound downstream table, calculation, and textual-relation work. Remove this scaffold when implementation replaces it.
