# Parser-family evolution map

| Layer | Shared across families | NEC | IBC | NFPA 13 | Lifecycle |
| --- | --- | --- | --- | --- | --- |
| Source identity | Artifact, edition/publication state, rights, access, exact bytes | 2017 private PDF manifest | 2018 private PDF manifest on draft | 2019 private PDF provenance bundle on draft | shared active contract |
| PDF evidence | Page, block, coordinates, source maps, diagnostics | two-column article ordering and bookmarks | glyph repair, layout bands, tables, superscripts on draft | positioned spans and table structure on draft | shared core, family extensions |
| Printed hierarchy | Document AST primitives | Article, Part, Section, parenthetical subdivisions, notes and exceptions | chapter, decimal section ancestry, Parts, enumerations, definitions, appendices by design | chapters, nested clauses, annex hierarchy | family-specific |
| Editorial evidence | explicit labels and source order | NEC Style Manual edition profiles as priors | ICC conventions and audited layout behavior | NFPA annex and reference conventions | edition/family-specific |
| Semantic review | source spans and diagnostics | Article 100 definitions; selected Sections 90.5 and 110 | not implemented on current main | external target domains and annex correspondence on draft | family-specific |
| Current support | contracts and validation | selected 2017 regions merged | draft only | draft only | qualified by tree state |

## Rejected universalizations

- PDF text order as hierarchy.
- Font size or indentation as the sole parent signal.
- One numbering grammar for NEC, IBC, and NFPA.
- Every parenthetical marker as a clause.
- Every annex ancestor as an explanatory relation.
- Every table as plain text or every visually aligned block as a table.
- Successful selected fragments as proof of complete-edition support.

The durable reuse boundary is the source/provenance and neutral structural contract. Grammar remains family- and sometimes edition-specific until stronger evidence proves otherwise.
