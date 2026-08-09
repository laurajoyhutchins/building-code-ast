# ASCE 7-22 source registration

Status: implemented and exact-source verified.

Canonical roadmap: #219.

## Owns

- bind the retained ASCE/SEI 7-22 artifact to the existing publication-neutral source register;
- preserve the exact AST source identity already consumed by the landed ASCE Document AST adapter;
- record exact digest, media type, publication identity, and rights/access state;
- preserve unresolved printing and correction/addenda state explicitly without guessing;
- verify the source-register identity round-trips into `DocumentSourceArtifact` without changing durable ASCE node identity.

## Exact retained artifact

Private retained file: `asce-7-2022.pdf`.

- size: 55,404,349 bytes;
- SHA-256: `522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0`;
- physical page count: 1,047;
- media type: `application/pdf`;
- encryption: none;
- first-page publication identity: ASCE/SEI 7-22, *Minimum Design Loads and Associated Criteria for Buildings and Other Structures*;
- issuing body: American Society of Civil Engineers.

The digest exactly matches the source characterization established through PR #53 and the source identity already hard-coded by the landed ASCE adapter.

## Registered identity

Source register record: `corpora/asce-7-22/asce-7-22-source-register.json`.

- source ID: `source:asce:7:2022:pdf:522d341d`;
- AST artifact ID: `sha256:522d341d8ab21eb254c8af2d853910633233285eb3704933729e0aeefdc88eb0`;
- AST edition ID: `asce-7-22`;
- evidence role: `normative_text`;
- access scope: `licensed_local`;
- rights status: `licensed`;
- publication edition: `2022`;
- printing: unresolved / not identified by the retained artifact;
- digital revision: unresolved / not identified;
- correction/addenda state: `unresolved:retained-artifact-correction-and-addenda-state`;
- deterministic publication state ID: `publication:2e70e34ecbea96f39455a759f3e5b8d853ce02f9cc50e4c99c2c29c94aabcc03`.

The source profile established that the retained artifact is copyrighted and license-restricted. No protected prose, page images, extracted corpus, or reconstructive material is committed.

## TDD evidence

Converged branch coordinate before the source gate: `a7b05bb833212344d0b46080d98af03e06704044`.

RED head: `14e169cc794b3a93947ad779dc597d01f535ad1b`.

At RED, CI ran 454 tests and failed only because the exact ASCE source-register JSON did not yet exist.

First register attempt: `aafa088af06d2d3515c708f6cda2e25c2de28928`.

That attempt exposed a shared-contract boundary: runtime `PublicationIdentity` has an `addenda_set` member, but the strict source-register deserializer does not accept that field. This PR does not redesign the shared register. The source profile's unresolved correction/addenda evidence is therefore preserved honestly in the supported `correction_set` field rather than discarded or guessed.

Corrected GREEN head: `cd31b61f0d211c11e4a00491698c2e8b70733d8b`.

Fresh hosted checks on that exact head:

- CI: success;
- LORE: success;
- Deciduous archaeology: success.

The regression test validates the strict source-register schema, exact digest/publication state, rights/access state, and exact `DocumentSourceArtifact` identity compatibility with the existing ASCE adapter.

## Does not own

- parser changes;
- source extraction or search;
- whole-document AST generation;
- equation/table/figure/map semantics;
- printing or correction/addenda assumptions not established by the retained artifact;
- protected source payloads.

## Next evidence gate

After this registration lands, open a fresh ASCE whole-document observation/replay task only when it can actually execute against this exact artifact from then-current `main`. Do not recreate the retired descendant scaffold.
