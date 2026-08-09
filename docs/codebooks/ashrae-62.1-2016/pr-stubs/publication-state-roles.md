# ASHRAE 62.1-2016 publication state and source roles

Status: draft PR scaffold; implementation not started.

## Depends on

`ashrae-62.1-2016/document-ast-foundation`

## Purpose

Preserve the exact retained publication state and publication-defined source roles in the Document AST path.

## Scope

- incorporated addenda identity
- explicit unresolved correction/errata layer
- normative versus informative source role
- foreword, standard body, appendix, and back-matter role boundaries
- smallest publication-neutral model change only if existing contracts cannot represent the evidence

## Boundaries

Do not infer project applicability, silently apply external corrections, or introduce a parallel ASHRAE-only provenance model.

## Completion gate

The exact source replay distinguishes artifact identity from publication state and preserves role boundaries without changing protected source content. Remove this scaffold when implementation replaces it.
