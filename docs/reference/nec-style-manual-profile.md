# NEC Style Manual Profile

The NEC Style Manual profile is a versioned set of editorial expectations used as parser evidence and validation context. It is not a substitute for the published NEC text, a repair oracle, or an electrical interpretation.

The public implementation is `building_code_ast.nec.style_manual`, version `0.1.0`.

## Supported profiles

| NEC edition | Style Manual profile | Definition placement | Parallel numbering | Third-level titles |
| --- | --- | --- | --- | --- |
| 2017 | 2015 | Article 100 or an article-local definition section | Encouraged | Optional |
| 2020 | 2020 | Article 100 only | Encouraged | Optional |
| 2023 | 2023 | Article 100 only | Required | Optional, but consistent among siblings when used |

The profiles also record that Article 100 is not subdivided, informational-note numbering is local to its owner, the first section of an Article is expected to be Scope, and the named subdivision sequence has three levels: `(A)`, `(1)`, `(a)`.

## Structural evidence

Parenthetical numbering does not uniquely identify hierarchy. A marker such as `(1)` can be either a subdivision or a list item.

The parser and validators should therefore use independent evidence:

- a title is strong evidence that the marker is a subdivision;
- an explicit list introduction is strong evidence that the marker is a list item;
- title and list evidence together are conflicting evidence;
- numbering without either signal remains ambiguous;
- typography, sibling consistency, open structural context, and cross-references may strengthen or weaken the interpretation but must not silently replace source evidence.

The `interpret_parenthetical_marker` helper returns `subdivision`, `list_item`, or `ambiguous` together with confidence and the evidence used. It deliberately does not force ambiguous markers into the hierarchy.

## Informational notes

Informational notes are non-normative children of the definition, section, or subdivision they follow. Their displayed numbers restart under each owner. `informational_note_identity` therefore includes the owner identity and note number rather than treating note numbers as document-global identifiers.

Exceptions remain normative variations attached to the requirement they modify. The NEC section-review layer continues to model exceptions and informational notes separately.

## Definition placement

The 2017 profile permits Article 100 definitions and article-local definition sections. The 2020 and 2023 profiles expect requirement definitions only in Article 100. Edition-aware ingestion must preserve an unexpected definition location as source evidence and emit a diagnostic rather than deleting or relocating it.

## Authority boundary

The manuals describe expected drafting structure. The actual NEC edition remains the evidence of what was published. Examples, page references, and numbering inside a Style Manual can contain legacy or editorial defects, so conformance checks should report differences without rewriting the AST.

Official source documents:

- [2015 NEC Style Manual](https://docinfofiles.nfpa.org/files/AboutTheCodes/70/NEC_StyleManual_2015.pdf)
- [2020 NEC Style Manual](https://docinfofiles.nfpa.org/files/AboutTheCodes/70E/NEC_Style_Manual_2020.pdf)
- [2023 NEC Style Manual](https://docinfofiles.nfpa.org/files/AboutTheCodes/70/NEC_Style_Manual_2023_v2.pdf)
