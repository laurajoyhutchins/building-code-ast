"""Bounded extraction of official ICC proposal monographs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re

from ..model import DiagnosticSeverity
from .adapters import AdapterResult, EvidenceDiagnostic, SourceRegion
from .development import (
    DevelopmentDisposition,
    DevelopmentRecord,
    DevelopmentRecordKind,
)
from .model import EvidenceRole
from .source_packages import BoundArtifact


_PROPOSAL_HEADING_RE = re.compile(
    r"^(?P<proposal>[A-Z]+\d+-\d{2})(?:\s+Part\s+(?P<part>[IVXLCDM]+))?$"
)
_AFFECTED_LINE_RE = re.compile(r"^[A-Z][A-Z0-9 &\-]*:\s*(?P<locators>.+)$")
_LOCATOR_RE = re.compile(r"[A-Z]?\d{2,}(?:\.\d+)*(?:\([A-Za-z0-9]+\))*")


def _default_pdf_page_text(content: bytes) -> tuple[str, ...]:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for ICC development PDF extraction; "
            "install the evidence-pdf extra"
        ) from exc
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:  # pragma: no cover - dependency-specific parsing errors
        raise RuntimeError("PyMuPDF could not open the registered ICC development PDF") from exc
    try:
        return tuple(page.get_text("text") for page in document)
    finally:
        document.close()


def _page_lines(pages: tuple[str, ...]) -> tuple[tuple[int, tuple[str, ...]], ...]:
    if not isinstance(pages, tuple) or any(not isinstance(page, str) for page in pages):
        raise ValueError("page_text_extractor must return a tuple of strings")
    return tuple(
        (
            page_number,
            tuple(line.strip() for line in page.splitlines() if line.strip()),
        )
        for page_number, page in enumerate(pages, start=1)
    )


def _affected_locators(value: str) -> tuple[str, ...]:
    found: list[str] = []
    for locator in _LOCATOR_RE.findall(value):
        if locator not in found:
            found.append(locator)
    return tuple(found)


def _action_disposition(value: str) -> DevelopmentDisposition | None:
    normalized = " ".join(value.casefold().split())
    if normalized.startswith("as submitted") or normalized.startswith(
        "approved as submitted"
    ):
        return DevelopmentDisposition.APPROVED
    if normalized.startswith("as modified") or normalized.startswith(
        "approved as modified"
    ):
        return DevelopmentDisposition.APPROVED_AS_MODIFIED
    if normalized.startswith("disapproved"):
        return DevelopmentDisposition.DISAPPROVED
    if normalized.startswith("withdrawn"):
        return DevelopmentDisposition.WITHDRAWN
    if normalized.startswith("superseded"):
        return DevelopmentDisposition.SUPERSEDED
    return None


def _unsupported_multipart(
    *,
    proposal_id: str,
    part: str,
    page: int,
) -> tuple[EvidenceDiagnostic, SourceRegion]:
    region = SourceRegion(page=page, anchor=f"{proposal_id}:part-{part.casefold()}")
    return (
        EvidenceDiagnostic(
            code="unsupported-multipart-development-proposal",
            severity=DiagnosticSeverity.WARNING,
            message=(
                "Multipart ICC proposals require an explicit part-aware lineage contract; "
                "the bounded adapter does not collapse parts into one proposal."
            ),
            region=region,
        ),
        region,
    )


class IccProposalMonographPdfAdapter:
    """Extract single-part proposal roots from an official ICC proposal monograph."""

    adapter_id = "icc-proposal-monograph-pdf"
    adapter_version = "0.1.0"
    supported_roles = frozenset({EvidenceRole.DEVELOPMENT_HISTORY})
    supported_media_types = frozenset({"application/pdf"})

    def __init__(
        self,
        *,
        page_text_extractor: Callable[[bytes], tuple[str, ...]] | None = None,
    ) -> None:
        if page_text_extractor is not None and not callable(page_text_extractor):
            raise ValueError("page_text_extractor must be callable")
        self.page_text_extractor = page_text_extractor or _default_pdf_page_text

    def extract(
        self,
        source: BoundArtifact,
        content: bytes,
    ) -> AdapterResult[DevelopmentRecord]:
        pages = _page_lines(self.page_text_extractor(content))
        records: list[DevelopmentRecord] = []
        diagnostics: list[EvidenceDiagnostic] = []
        unsupported: list[SourceRegion] = []
        seen: set[str] = set()

        for page_number, lines in pages:
            for index, line in enumerate(lines):
                heading = _PROPOSAL_HEADING_RE.fullmatch(line)
                if heading is None:
                    continue
                proposal_id = heading.group("proposal")
                part = heading.group("part")
                if part is not None:
                    diagnostic, region = _unsupported_multipart(
                        proposal_id=proposal_id,
                        part=part,
                        page=page_number,
                    )
                    diagnostics.append(diagnostic)
                    unsupported.append(region)
                    continue
                if proposal_id in seen:
                    continue

                affected: tuple[str, ...] = ()
                proponent: str | None = None
                for candidate in lines[index + 1 : index + 12]:
                    affected_match = _AFFECTED_LINE_RE.fullmatch(candidate)
                    if affected_match is not None and not affected:
                        affected = _affected_locators(affected_match.group("locators"))
                    if candidate.casefold().startswith(("proponent:", "proponents:")):
                        proponent = candidate.split(":", 1)[1].strip()
                        break
                if not affected or not proponent:
                    region = SourceRegion(page=page_number, anchor=f"{proposal_id}:proposal")
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="incomplete-official-development-proposal",
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                "Proposal heading did not expose both affected locators and "
                                "a proponent within the bounded monograph layout."
                            ),
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue

                record_key = f"{proposal_id}:proposal"
                records.append(
                    DevelopmentRecord(
                        source_id=source.source_id,
                        proposal_id=proposal_id,
                        record_key=record_key,
                        kind=DevelopmentRecordKind.PROPOSAL,
                        disposition=DevelopmentDisposition.SUBMITTED,
                        sequence=1,
                        proponent=proponent,
                        affected_locators=affected,
                        parent_keys=(),
                        action_date=None,
                        summary="Official ICC proposal monograph entry.",
                        source_page=page_number,
                        source_anchor=record_key,
                    )
                )
                seen.add(proposal_id)

        return AdapterResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            records=tuple(records),
            diagnostics=tuple(diagnostics),
            unsupported_regions=tuple(unsupported),
        )


@dataclass(frozen=True, slots=True)
class IccActionStage:
    record_kind: DevelopmentRecordKind
    record_key_suffix: str
    parent_key_suffix: str
    sequence: int
    action_date: str | None = None

    def __post_init__(self) -> None:
        if self.record_kind is DevelopmentRecordKind.PROPOSAL:
            raise ValueError("record_kind must be an action kind")
        if not self.record_key_suffix.strip() or not self.parent_key_suffix.strip():
            raise ValueError("action stage key suffixes must not be empty")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 2:
            raise ValueError("action stage sequence must be an integer of at least 2")
