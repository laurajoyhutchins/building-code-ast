# NEC 2020 expected changelog dataset design

**Status:** Approved for implementation

## Purpose

Build a source-safe development-history dataset that predicts where the 2020 NEC should differ from the 2017 NEC, then use that prediction as an independent verification oracle when the final 2020 edition is parsed.

The issued 2020 NEC remains the controlling text. NFPA development records are authoritative evidence of proposals, committee actions, ballots, motions, appeals, and issuance decisions, but they do not replace the issued edition.

## Architecture

The feature has four independent layers:

1. **Source manifest** records immutable identity, retrieval metadata, access scope, and source locators for privately acquired development documents.
2. **Development records** normalize Public Inputs, revisions, comments, technical-meeting actions, Council decisions, TIAs, and errata without copying protected source prose into public Git.
3. **Expected changes** resolve raw NEC references against the canonical 2017 hierarchy and apply deterministic procedural precedence to each proposal chain.
4. **Reconciliation** compares expectations with an independently generated observed 2017-to-2020 AST diff.

The expected-change projector must not modify either edition's AST and must not be consumed by the 2020 parser.

## Authority and precedence

Later procedural stages override earlier stages within the same change chain:

```text
erratum
TIA
Standards Council action
technical-meeting action
second revision
public comment
first revision
public input
```

Accepted or issued actions create positive expectations. Rejected, withdrawn, failed-ballot, and return-to-prior-edition actions create negative expectations. A proposal without a later disposition remains uncertain.

Conflicting controlling records at the same procedural stage fail closed rather than being selected by source order.

## Canonical contracts

The public contracts contain only project-authored summaries and source locators. They do not contain long quotations or reconstructed NEC text.

A source-manifest entry contains:

- stable source ID;
- document type, title, cycle, and optional panel;
- retrieval timestamp and URL;
- SHA-256 digest, media type, and optional page count;
- access scope.

A development record contains:

- stable record ID and change-chain ID;
- record type, stage, disposition, and panel;
- raw affected and expected target references;
- structural change classifications;
- a short project-authored summary;
- typed links to related records;
- an exact source locator.

An expected change contains:

- stable expectation and chain IDs;
- resolved 2017 locators and unresolved raw references;
- expected target references and change classifications;
- positive, negative, or uncertain expectation state;
- controlling and supporting record IDs;
- procedural confidence.

An observed change contains only AST lineage, classifications, a short summary, and alignment confidence. Reconciliation records classify confirmation, missing observations, contradiction, ambiguity, and unexpected observed changes.

## Reference resolution

The first implementation supports:

- exact Article, Section, and nested clause locators;
- optional `Section` prefixes;
- numeric or alphabetic sibling ranges such as `210.8(A)(1) through (5)`;
- explicit unresolved output when a reference cannot be mapped to the supplied 2017 locator set.

The resolver never attaches an unresolved reference to a nearby provision. Table, figure, exception-position, and prose-relative references remain unresolved until dedicated resolvers are added.

## Confidence

Confidence is derived rather than manually chosen:

- **high:** Council action, TIA, or erratum with all controlling references resolved;
- **medium:** second revision or technical-meeting action with all controlling references resolved;
- **low:** earlier-stage action, uncertain finality, or any unresolved controlling reference.

## First vertical slice

The first public implementation is infrastructure plus a source-free synthetic fixture. It proves:

- manifest validation;
- clause reference resolution;
- procedural precedence and negative expectations;
- deterministic expected-change projection;
- observed-change reconciliation;
- strict CLI behavior;
- preservation of the private-source boundary.

Actual NFPA records and issued-edition text remain private inputs. The next corpus step will ingest one bounded Code-Making Panel 2 change chain and reconcile it after a 2020 ArticleSeed exists.

## Non-goals

- publishing NFPA or NEC source text;
- claiming that a development proposal became final without later-stage evidence;
- interpreting electrical safety requirements;
- repairing parser output to match expectations;
- resolving tables, figures, or positional prose references in this slice;
- scraping authenticated NFPA interfaces in the public runtime.

## Verification

The implementation must use only Python 3.12 standard-library dependencies, preserve deterministic JSON ordering, reject malformed hashes and confidence values, detect same-stage procedural conflicts, and pass the repository-wide unit and compilation checks.