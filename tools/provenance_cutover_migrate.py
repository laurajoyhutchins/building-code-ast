from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "building_code_ast"
EVIDENCE = SRC / "evidence"


def replace(path: Path, old: str, new: str, *, count: int | None = None) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"expected text not found in {path}: {old!r}")
    updated = text.replace(old, new, count if count is not None else -1)
    path.write_text(updated, encoding="utf-8")


# Normalized runtime source context: publication facts + exact artifact + binding.
sp = EVIDENCE / "source_packages.py"
text = sp.read_text(encoding="utf-8")
marker = "\n\n@dataclass(frozen=True, slots=True)\nclass SourcePackage:"
if marker not in text:
    raise SystemExit("SourcePackage marker missing")
bound = '''\n\n@dataclass(frozen=True, slots=True)\nclass BoundArtifact:\n    publication: PublicationState\n    artifact: Artifact\n    binding: ArtifactBinding\n\n    def __post_init__(self) -> None:\n        if self.binding.publication_id != self.publication.publication_id:\n            raise ValueError("binding publication_id does not match publication identity")\n        if self.binding.artifact_id != self.artifact.artifact_id:\n            raise ValueError("binding artifact_id does not match artifact identity")\n\n    @property\n    def source_id(self) -> str:\n        return self.binding.source_id\n\n    @property\n    def evidence_role(self) -> EvidenceRole:\n        return self.binding.evidence_role\n\n    @property\n    def media_type(self) -> str:\n        return self.artifact.media_type\n\n    @property\n    def sha256(self) -> str:\n        return self.artifact.sha256\n\n    @property\n    def ast_source(self) -> AstSourceIdentity:\n        return self.binding.ast_source\n\n    @property\n    def jurisdiction(self) -> str | None:\n        return self.binding.jurisdiction\n\n    @property\n    def issuing_body(self) -> str:\n        if self.binding.issuing_body is None:\n            raise ValueError("binding issuing_body is required by this evidence adapter")\n        return self.binding.issuing_body\n'''
text = text.replace(marker, bound + marker, 1)
needle = '''    def binding_for_source(self, source_id: str) -> ArtifactBinding:\n        matches = [item for item in self.bindings if item.source_id == source_id]\n        if len(matches) != 1:\n            raise KeyError(source_id)\n        return matches[0]\n'''
addition = needle + '''\n    def bound_artifact(self, source_id: str) -> BoundArtifact:\n        binding = self.binding_for_source(source_id)\n        publication = next((item for item in self.publications if item.publication_id == binding.publication_id), None)\n        if publication is None:\n            raise KeyError(binding.publication_id)\n        return BoundArtifact(publication=publication, artifact=self.artifact(binding.artifact_id), binding=binding)\n'''
if needle not in text:
    raise SystemExit("binding_for_source marker missing")
text = text.replace(needle, addition, 1)
sp.write_text(text, encoding="utf-8")

# Adapter execution now accepts only a normalized BoundArtifact.
adapters = EVIDENCE / "adapters.py"
text = adapters.read_text(encoding="utf-8")
text = text.replace("from .source_packages import Artifact, ArtifactBinding", "from .source_packages import BoundArtifact")
start = text.index("@dataclass(frozen=True, slots=True)\nclass BoundArtifact:")
end = text.index("\n\n@dataclass(frozen=True, slots=True)\nclass SourceRegion:", start)
text = text[:start] + text[end + 2:]
old = '''def run_evidence_adapter(adapter: EvidenceAdapter[RecordT], binding: ArtifactBinding, artifact: Artifact, content: bytes) -> AdapterResult[RecordT]:\n    source = BoundArtifact(binding=binding, artifact=artifact)\n'''
new = '''def run_evidence_adapter(adapter: EvidenceAdapter[RecordT], source: BoundArtifact, content: bytes) -> AdapterResult[RecordT]:\n    if not isinstance(source, BoundArtifact):\n        raise TypeError("source must be a BoundArtifact from canonical provenance")\n'''
if old not in text:
    raise SystemExit("run_evidence_adapter legacy signature missing")
text = text.replace(old, new, 1)
adapters.write_text(text, encoding="utf-8")

# Migrate every evidence adapter source annotation/import to BoundArtifact.
for path in EVIDENCE.glob("*.py"):
    if path.name in {"adapters.py", "source_packages.py", "model.py", "__init__.py"}:
        continue
    text = path.read_text(encoding="utf-8")
    if "SourceRegisterEntry" not in text:
        continue
    text = text.replace("from .model import EvidenceRole, SourceRegisterEntry", "from .model import EvidenceRole\nfrom .source_packages import BoundArtifact")
    text = text.replace("from .model import SourceRegisterEntry, EvidenceRole", "from .model import EvidenceRole\nfrom .source_packages import BoundArtifact")
    text = text.replace("from .model import SourceRegisterEntry", "from .source_packages import BoundArtifact")
    text = text.replace("SourceRegisterEntry", "BoundArtifact")
    path.write_text(text, encoding="utf-8")

# Publication state IDs in AST ingestion now come from asserted bibliographic state only.
for filename, old_import, old_block, new_block in [
    (
        "ashrae621_2016.py",
        "from ..evidence.model import PublicationIdentity, publication_state_id",
        '''ASHRAE_62_1_2016_PUBLICATION = PublicationIdentity(\n    publication_family="ashrae-62.1",\n    edition="2016",\n    printing="artifact-mark:3/16;numbered-printing:unresolved",\n    correction_set=(\n        "incorporated-addenda:ashrae-62.1-2013:a,c,d,e,f,g,h,i,j,k,p,q,r,s;"\n        "correction-layer:unresolved:no-incorporated-correction-layer-established"\n    ),\n)''',
        '''ASHRAE_62_1_2016_PUBLICATION = PublicationState(\n    publication_family="ANSI/ASHRAE Standard 62.1",\n    edition="2016",\n    addenda_set="a,c,d,e,f,g,h,i,j,k,p,q,r,s",\n)''',
    ),
    (
        "ashrae901_2016.py",
        "from ..evidence.model import PublicationIdentity, publication_state_id",
        '''ASHRAE_90_1_2016_PUBLICATION = PublicationIdentity(\n    publication_family="ashrae-90.1",\n    edition="2016 I-P",\n    printing="artifact-code:10/16;numbered-printing:unresolved",\n    addenda_set="ashrae-90.1-2013:addenda-enumerated-in-90.1-2016-appendix-h",\n    correction_set="unresolved:no-incorporated-post-publication-correction-established",\n)''',
        '''ASHRAE_90_1_2016_PUBLICATION = PublicationState(\n    publication_family="ANSI/ASHRAE/IES Standard 90.1",\n    edition="2016 I-P Edition",\n    addenda_set="all addenda to Standard 90.1-2013 enumerated by retained Informative Appendix H",\n)''',
    ),
]:
    path = SRC / "ingest" / filename
    text = path.read_text(encoding="utf-8")
    if old_import not in text or old_block not in text:
        raise SystemExit(f"ASHRAE migration marker missing in {path}")
    text = text.replace(old_import, "from ..evidence.source_packages import PublicationState")
    text = text.replace(old_block, new_block)
    text = re.sub(r"edition_id=publication_state_id\((ASHRAE_[^)]+_PUBLICATION)\)", r"edition_id=\1.publication_id", text)
    path.write_text(text, encoding="utf-8")

# The old register contract test is replaced by normalized package/cutover tests.
legacy_contract_test = ROOT / "tests" / "test_source_evidence.py"
legacy_contract_test.unlink(missing_ok=True)

# Old schemas are no longer authority and must not survive the strangler.
for path in (ROOT / "schemas").glob("*source-register*"):
    path.unlink()
for path in (ROOT / "schemas").glob("*source-object*"):
    path.unlink()

# Public evidence API exposes only normalized provenance names.
init = EVIDENCE / "__init__.py"
init.write_text('''"""Public source-evidence contracts."""\n\nfrom . import amendments as _amendments\nfrom .adapters import AdapterResult, EvidenceAdapter, EvidenceDiagnostic, SourceRegion, run_evidence_adapter\nfrom .amendments import AMENDMENT_OPERATION_VALUES, AMENDMENT_PATCH_VERSION, AmendmentOperation, AmendmentSet, JurisdictionalAmendmentPatch, NormalizedWashingtonWacHtmlAdapter, amendment_patch_from_dict\nfrom .artifact_hydration import ARTIFACT_HYDRATION_RECEIPT_VERSION, ArtifactFetcher, ArtifactHydrationReceipt, ArtifactHydrationStatus, hydrate_artifact, verify_local_artifact\nfrom .artifact_locators import PRIVATE_ARTIFACT_LOCATOR_VERSION, ObjectProvider, PrivateArtifactLocator, PrivateArtifactLocatorRegistry, private_artifact_locator_registry_from_dict\nfrom .development import DEVELOPMENT_DISPOSITION_VALUES, DEVELOPMENT_KIND_VALUES, DEVELOPMENT_RECORD_VERSION, DevelopmentDisposition, DevelopmentLineage, DevelopmentRecord, DevelopmentRecordKind, IccDevelopmentTextAdapter, development_record_from_dict\nfrom .errata import ERRATA_RECORD_VERSION, ERRATUM_OPERATION_VALUES, TARGET_KIND_VALUES, ErratumOperation, ErratumRecord, IccErrataPdfAdapter, TargetKind, erratum_record_from_dict\nfrom .icc_action_report import IccCommitteeActionReportPdfAdapter\nfrom .icc_development import IccActionStage, IccProposalMonographPdfAdapter\nfrom .model import ACCESS_SCOPE_VALUES, EVIDENCE_ROLE_VALUES, RIGHTS_STATUS_VALUES, AccessScope, AstSourceIdentity, EvidenceRole, RightsStatus\nfrom .source_packages import Artifact, ArtifactBinding, BoundArtifact, Derivation, PublicationAssurance, PublicationState, SourceAuditRecord, SourcePackage, SourceReadiness, build_source_index, load_source_package, source_audit, source_package_from_dict\nfrom .washington_official import WashingtonOfficialWacHtmlAdapter, WashingtonWacHtmlAdapter\n\nIccCommitteeActionPdfAdapter = IccCommitteeActionReportPdfAdapter\n_amendments.WashingtonWacHtmlAdapter = WashingtonWacHtmlAdapter\n\n__all__ = [name for name in globals() if not name.startswith("_")]\n''', encoding="utf-8")

# No live source code may reference the strangled provenance concepts.
for forbidden in ("SourceRegisterEntry", "SourceRegister", "PublicationIdentity", "source_register_from_dict", "source_object_catalog_from_dict", "hydrate_source_object"):
    hits = []
    for path in SRC.rglob("*.py"):
        if forbidden in path.read_text(encoding="utf-8"):
            hits.append(str(path.relative_to(ROOT)))
    if hits:
        raise SystemExit(f"forbidden legacy provenance concept {forbidden!r} remains in: {hits}")

print("normalized provenance runtime migration applied")
