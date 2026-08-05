# Downstream-boundary map

| Concern | Owning system | What Building Code AST provides | What it does not decide |
| --- | --- | --- | --- |
| Source publication structure | `building-code-ast` | hierarchy, spans, provenance, references, diagnostics | legal interpretation |
| Jurisdiction and adoption | `building-code-map` | stable code-family, edition, and locator identities for linkage | which authority or edition applies to an address |
| Amendments | AST evidence layer plus downstream resolver | source-backed patch operations and conflicts | legally controlling consolidated text or permit-cycle applicability |
| Equipment and listings | `electrical-equipment-lineage` | code references and target-domain links | certification status, replacement compatibility, manufacturer lineage |
| Edition comparison | comparison tooling downstream of independently parsed editions | normalized structures, expected-change evidence, diagnostics | authoritative change without both issued sources |
| Compliance and reasoning | future downstream systems | clauses, conditions, exceptions, definitions, tables, and provenance | project compliance or engineering judgment |
| Retrieval and explanation | search/RAG/UI layers | addressable source nodes and citations | canonical structure or authority |

The boundary keeps the source tree small enough to validate and rich enough to reuse. Downstream products may create graphs and consolidated views, but they must preserve the base publication, amendments, source spans, and uncertainty.
