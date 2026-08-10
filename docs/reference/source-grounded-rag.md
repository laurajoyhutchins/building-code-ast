# Source-grounded RAG

Building Code AST provides a provider-neutral retrieval-augmented generation boundary over the local source-evidence store. The boundary exists to make generation inspectable and provenance-preserving; it does not turn generated prose into code authority, reviewed interpretation, or a compliance determination.

## Pipeline

```text
exact registered source artifact
  -> verified local evidence store
  -> lexical retrieval
  -> optional publication-neutral structural filters
  -> bounded neighboring source context
  -> grounding packet with exact evidence IDs
  -> caller-controlled generator
  -> generated draft with explicit evidence-ID citations
  -> citation-membership validation
```

Retrieval and context expansion are deterministic for a fixed store and query. Generation is deliberately outside the deterministic core.

## Grounding packet

`build_grounding_packet()` returns a `GroundingPacket` containing:

- the exact `SourceArtifactIdentity`;
- the trimmed query and lexical search mode;
- source-ordered retrieval hits with their retrieval-score metadata;
- bounded previous/center/next evidence context for each hit;
- exact evidence IDs, physical PDF pages, block coordinates, and source text already present in the local evidence store.

Page-local context is the default. Callers must opt in explicitly when context is allowed to cross a physical PDF page boundary.

When `StructuralSearchFilters` are supplied, structural filtering is applied before the grounding result limit. Structural candidates remain source-observation aids only; they do not assign provision meaning.

## Generation boundary

`run_grounded_generation()` accepts a caller-supplied generator callback. The repository does not select, configure, authenticate to, or invoke a remote model provider on its own.

The callback receives one `GroundingPacket` and must return a `GeneratedDraft` containing:

- a non-empty `generator_id` identifying the caller's generation implementation;
- generated text;
- one or more cited evidence IDs.

An answered result is accepted only when every cited evidence ID occurs in the grounding packet, including bounded neighboring context. Unknown citations fail closed. If retrieval returns no evidence, the generator is not called and the result is `insufficient_evidence`.

This validation proves only that the stated citations were available to the generator. It does **not** prove that the generated claim is entailed by those citations, that all relevant source material was retrieved, or that the answer is legally or technically correct.

## Python use

```python
from building_code_ast.retrieval import (
    GeneratedDraft,
    SourceArtifactIdentity,
    run_grounded_generation,
)

artifact = SourceArtifactIdentity(
    source_id="registered-source-id",
    publication_key="publication-filter-key",
    sha256="<exact-lowercase-sha256>",
    size=123456,
    page_count=100,
)


def generate(packet):
    # Caller controls whether and how packet content is sent to a model.
    # Preserve the evidence IDs used to support the generated draft.
    return GeneratedDraft(
        generator_id="my-local-generator/1",
        text="Generated answer text.",
        cited_evidence_ids=(packet.chunks[0].context.center.evidence_id,),
    )


result = run_grounded_generation(
    "generated-private/evidence.sqlite3",
    artifact=artifact,
    query="outdoor air requirement",
    generator=generate,
)
```

The example is schematic. A real generator must decide how to prompt a model, how to require citations, and whether source rights permit transmitting source text to that model or service.

## CLI use

The CLI exposes packet construction without invoking generation:

```bash
building-code-ast source rag "outdoor air requirement" \
  --store generated-private/evidence.sqlite3 \
  --source-id registered-source-id \
  --publication-key publication-filter-key \
  --sha256 <exact-lowercase-sha256> \
  --size 123456 \
  --page-count 100 \
  --limit 5
```

The JSON output records `generation: "not_invoked"`. `--candidate heading|table|figure|equation` can constrain retrieval to an existing publication-neutral structural candidate. `--cross-page` explicitly permits neighboring context to cross physical PDF pages.

The packet can contain protected source expression because it is built from the private local evidence store. Keep packet output private unless publication or transmission is independently permitted.

## Safety and authority boundary

A grounded generated answer remains generated output. Downstream systems must continue to distinguish:

- source evidence;
- retrieval metadata;
- generated prose;
- parser inference;
- unresolved ambiguity;
- human-reviewed interpretation;
- jurisdictional applicability;
- project facts and machine evaluation;
- professional or authority determinations.

Do not convert lexical retrieval scores into semantic confidence. Do not treat evidence-ID validation as claim verification. Do not infer controlling law from the retrieval artifact. Do not present this boundary as a compliance engine.

See `docs/legal-safety-boundary.md`, `docs/corpus-policy.md`, and `docs/architecture.md` for the broader project constraints.
