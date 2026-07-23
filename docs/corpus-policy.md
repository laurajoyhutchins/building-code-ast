# Corpus and Source Policy

## Default rule

Do not commit source text unless its inclusion and redistribution are lawful, necessary, and documented.

The repository may contain:

- project-authored synthetic provisions;
- public-domain enactments when provenance is recorded;
- short quotations used lawfully for analysis or testing when approved for the repository;
- metadata, checksums, source locators, and local-ingestion instructions that do not redistribute restricted text.

The repository must not assume that model-code text, standards, commentary, tables, figures, or a jurisdiction's adoption of a publication makes that publication freely redistributable.

## Fixture metadata

Non-synthetic fixtures should eventually include:

- source title and edition;
- issuing or adopting authority;
- section identifier;
- official source locator;
- access date;
- copyright or public-domain basis;
- transformation notes;
- checksum of the locally supplied source artifact;
- reviewer and review date.

## Local-only source handling

Restricted or uncertain source artifacts should remain outside Git. A future ingestion interface may accept local paths and emit derived ASTs, but generated artifacts must be reviewed for whether they reproduce protected expression before publication.

## Synthetic fixtures

Synthetic fixtures must be labeled as synthetic and should test grammatical and semantic structures rather than imitate long passages from a specific publication.
