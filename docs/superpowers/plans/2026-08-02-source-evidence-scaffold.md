# Source Evidence Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dependency-free, publication-neutral source register and guarded adapter boundary for future IBC errata, development-history, and jurisdictional-amendment ingestion.

**Architecture:** A new `building_code_ast.evidence` package owns immutable source metadata, strict JSON input handling, and adapter execution guards. Source-family-specific records remain outside this slice, while all adapters must pass exact-byte digest and identity checks before their output is accepted.

**Tech Stack:** Python 3.12 standard library, frozen slotted dataclasses, `StrEnum`, `Protocol`, `unittest`, Draft 2020-12 JSON Schema.

## Global Constraints

- Add no runtime dependency.
- Commit no model-code text, licensed commentary, page images, or source artifacts.
- Keep existing Document AST and Provision AST contracts unchanged.
- Keep the NEC change-history branch independent; do not edit its files in this slice.
- Reject unsupported or ambiguous metadata rather than guessing.
- Preserve exact source identity through `artifact_id`, `edition_id`, and lowercase SHA-256.

---

### Task 1: Pin the source-register contract with failing tests

**Files:**
- Create: `tests/test_source_evidence.py`

**Interfaces:**
- Consumes: no new production interface.
- Produces: executable requirements for `building_code_ast.evidence`.

- [ ] **Step 1: Write the failing model and round-trip tests**

Create tests importing:

```python
from building_code_ast.evidence import (
    ACCESS_SCOPE_VALUES,
    EVIDENCE_ROLE_VALUES,
    RIGHTS_STATUS_VALUES,
    SOURCE_REGISTER_VERSION,
    AccessScope,
    AstSourceIdentity,
    EvidenceRole,
    PublicationIdentity,
    RightsStatus,
    SourceRegister,
    SourceRegisterEntry,
    publication_state_id,
    source_register_from_dict,
)
```

Cover a synthetic 2021 IBC errata entry with printing and correction-set state. Assert `register.to_dict()` round-trips through `source_register_from_dict` and that serialization contains no source prose.

- [ ] **Step 2: Add failing invariant tests**

Add cases proving:

```python
self.assertNotEqual(
    publication_state_id(first_printing),
    publication_state_id(third_printing),
)
```

Also cover duplicate `source_id`, invalid SHA-256, malformed dates, unknown fields, unsupported enum values, and restricted entries without `rights_note`.

- [ ] **Step 3: Add failing schema-alignment test**

Load `schemas/source-register.schema.json` and assert its version constant and enum sets exactly equal the runtime values.

- [ ] **Step 4: Run the focused test and verify RED**

Run:

```bash
PYTHONPATH=src python -m unittest tests.test_source_evidence -v
```

Expected: import failure because `building_code_ast.evidence` does not exist.

- [ ] **Step 5: Commit the RED test**

```bash
git add tests/test_source_evidence.py
git commit -m "test: define source evidence contract"
```

### Task 2: Implement immutable source-register values

**Files:**
- Create: `src/building_code_ast/evidence/model.py`
- Create: `src/building_code_ast/evidence/io.py`
- Create: `src/building_code_ast/evidence/__init__.py`
- Create: `schemas/source-register.schema.json`
- Test: `tests/test_source_evidence.py`

**Interfaces:**
- Produces:
  - `publication_state_id(publication: PublicationIdentity) -> str`
  - `source_register_from_dict(value: Mapping[str, Any]) -> SourceRegister`
  - immutable values and enum constants exported from `building_code_ast.evidence`.

- [ ] **Step 1: Implement the minimal model**

Define:

```python
SOURCE_REGISTER_VERSION = "0.1.0"

class EvidenceRole(StrEnum):
    NORMATIVE_TEXT = "normative_text"
    OFFICIAL_CORRECTION = "official_correction"
    DEVELOPMENT_HISTORY = "development_history"
    JURISDICTIONAL_LAW = "jurisdictional_law"
    ADMINISTRATIVE_GUIDANCE = "administrative_guidance"
    OFFICIAL_INTERPRETATION = "official_interpretation"
    COMMENTARY = "commentary"
    SECONDARY_ANALYSIS = "secondary_analysis"
```

Add `AccessScope`, `RightsStatus`, `AstSourceIdentity`, `PublicationIdentity`, `SourceRegisterEntry`, and `SourceRegister`. Use frozen slotted dataclasses and deterministic `to_dict()` methods.

- [ ] **Step 2: Implement publication-state identity**

Canonicalize all publication fields with sorted compact JSON and return:

```python
return f"publication:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"
```

- [ ] **Step 3: Implement strict deserialization**

`source_register_from_dict` must enforce exact keys recursively, construct enums explicitly, validate dates and timezone-bearing retrieval timestamps, and call runtime invariants before returning.

- [ ] **Step 4: Add the JSON Schema**

Create a closed Draft 2020-12 schema matching every runtime field. Keep `additionalProperties: false` at every object boundary and require `rights_note` structurally while allowing `null`; runtime validation enforces cross-field restricted-source rules.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
PYTHONPATH=src python -m unittest tests.test_source_evidence -v
```

Expected: all source-register tests pass.

- [ ] **Step 6: Commit the model slice**

```bash
git add src/building_code_ast/evidence schemas/source-register.schema.json tests/test_source_evidence.py
git commit -m "feat: add publication-neutral source register"
```

### Task 3: Pin and implement guarded adapter execution

**Files:**
- Modify: `tests/test_source_evidence.py`
- Create: `src/building_code_ast/evidence/adapters.py`
- Modify: `src/building_code_ast/evidence/__init__.py`

**Interfaces:**
- Produces:
  - `SourceRegion`
  - `EvidenceDiagnostic`
  - `AdapterResult[T]`
  - `EvidenceAdapter[T]`
  - `run_evidence_adapter(adapter, source, content) -> AdapterResult[T]`

- [ ] **Step 1: Write failing adapter tests**

Define a local fake adapter and prove:

- digest mismatch raises before `extract` is called;
- unsupported evidence role and media type are rejected;
- valid content reaches the adapter;
- result `source_id`, `adapter_id`, and `adapter_version` must exactly match the invocation;
- invalid pages and bounding boxes fail closed;
- diagnostics and unsupported regions survive unchanged.

- [ ] **Step 2: Run focused tests and verify RED**

```bash
PYTHONPATH=src python -m unittest tests.test_source_evidence -v
```

Expected: import failure for adapter types or missing runner behavior.

- [ ] **Step 3: Implement adapter values and protocol**

Use a generic protocol:

```python
class EvidenceAdapter(Protocol[RecordT]):
    adapter_id: str
    adapter_version: str
    supported_roles: frozenset[EvidenceRole]
    supported_media_types: frozenset[str]

    def extract(
        self,
        source: SourceRegisterEntry,
        content: bytes,
    ) -> AdapterResult[RecordT]: ...
```

- [ ] **Step 4: Implement guarded execution**

`run_evidence_adapter` must validate adapter metadata, role, media type, and `sha256(content)` before calling `extract`. It must then validate the returned envelope identities.

- [ ] **Step 5: Run focused tests and verify GREEN**

```bash
PYTHONPATH=src python -m unittest tests.test_source_evidence -v
```

Expected: all adapter and register tests pass.

- [ ] **Step 6: Commit the adapter slice**

```bash
git add src/building_code_ast/evidence tests/test_source_evidence.py
git commit -m "feat: guard source evidence adapters"
```

### Task 4: Document the boundary and run repository verification

**Files:**
- Create: `docs/reference/source-evidence.md`
- Modify: `docs/README.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: completed evidence package.
- Produces: discoverable reference documentation and future adapter guidance.

- [ ] **Step 1: Write reference documentation**

Document the source-register fields, evidence-role separation, publication-state identity, rights boundary, adapter lifecycle, failure behavior, and the first three intended adapters.

- [ ] **Step 2: Link the reference**

Add one concise link in the root repository layout and the Diátaxis reference map without editing generated LORE projections or accepted records.

- [ ] **Step 3: Run the complete unit suite**

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Expected: zero failures.

- [ ] **Step 4: Compile source and tests**

```bash
PYTHONPATH=src python -m compileall -q src tests
```

Expected: exit code 0.

- [ ] **Step 5: Parse all JSON schemas**

```bash
python -c "import json, pathlib; [json.loads(path.read_text()) for path in pathlib.Path('schemas').glob('*.json')]"
```

Expected: exit code 0.

- [ ] **Step 6: Commit documentation**

```bash
git add README.md docs/README.md docs/reference/source-evidence.md
git commit -m "docs: define source evidence boundary"
```

- [ ] **Step 7: Open a draft pull request**

The PR must state the exact base and head, source/publication boundary, TDD evidence, full verification results, and the deliberate exclusion of real source acquisition or parsing.
