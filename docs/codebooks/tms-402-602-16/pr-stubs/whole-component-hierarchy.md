# Complete TMS 402-16 hierarchy

Status: draft PR scaffold; implementation not started.

## Purpose

Extend the TMS 402 Document AST across the complete canonical component region with publication-native hierarchy and explicit unsupported states.

## Scope

- Parts, Chapters, sections, subsections, paragraphs, and nested list structures
- definition-section structural placement
- notes and other ordinary hierarchy-bearing regions
- deterministic source-backed locators and IDs
- exact source spans and PDF/printed-page provenance
- role-aware hierarchy assembly across pages
- complete canonical-region private replay

## Boundaries

Do not add equation/table semantics, figure interpretation, cross-document reference resolution, or project compliance logic.

## Completion gate

Every canonical hierarchy-bearing TMS 402 source region is either represented in the validated Document AST or retained as explicit unsupported/ambiguous output with source evidence. Remove this scaffold file when implementation replaces it.
