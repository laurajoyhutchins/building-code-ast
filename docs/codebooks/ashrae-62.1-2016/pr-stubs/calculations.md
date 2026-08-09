# ASHRAE 62.1-2016 calculation structures

Status: draft PR scaffold; implementation not started.

## Depends on

`ashrae-62.1-2016/structural-inventory`

## Purpose

Begin the calculation/equation-hardening lane using measured whole-document denominators.

## Scope

- numbered and unnumbered equation identity
- mathematical region grouping
- multiline expressions and detached identifiers
- symbol occurrences and nearby definitions
- units and quantity display forms
- partial/unsupported diagnostics for typography that cannot be reconstructed faithfully
- private exact-source measurement of recognized versus unsupported calculation regions

## Boundaries

Do not fabricate formulas, silently normalize units, or turn extracted math into an executable ventilation calculator.

## Completion gate

Measured structural equation/calculation support is reported against the exact retained artifact with explicit unsupported cases. Remove this scaffold when implementation replaces it.
