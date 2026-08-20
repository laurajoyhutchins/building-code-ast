"""Official ICC committee-action report extraction."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import re

from ..model import DiagnosticSeverity
from .adapters import AdapterResult, EvidenceDiagnostic, SourceRegion
from .development import DevelopmentRecord
from .icc_development import (
    IccActionStage,
    _PROPOSAL_HEADING_RE,
    _action_disposition,
    _default_pdf_page_text,
    _page_lines,
    _unsupported_multipart,
)
from .model import EvidenceRole
from .source_packages import BoundArtifact


_ACTION_PREFIX_RE = re.compile(r"^Committee\s+Action\s*:?\s*(?P<action>.*)$", re.IGNORECASE)


def _bounded_action(lines: tuple[str, ...]) -> str | None:
    """Return the action label from one proposal-bounded text segment."""

    for index, line in enumerate(lines):
        match = _ACTION_PREFIX_RE.match(line)
        if match is None:
            continue
        action = match.group("action").strip()
        if action:
            return action
        if index + 1 < len(lines):
            continuation = lines[index + 1].strip()
            if continuation and not continuation.casefold().startswith("committee reason"):
                return continuation
    return None


class IccCommitteeActionReportPdfAdapter:
    """Extract actions from an official ICC report using proposal-bounded blocks."""

    adapter_id = "icc-committee-action-report-pdf"
    adapter_version = "0.1.0"
    supported_roles = frozenset({EvidenceRole.DEVELOPMENT_HISTORY})
    supported_media_types = frozenset({"application/pdf"})

    def __init__(
        self,
        *,
        stage: IccActionStage,
        affected_locators_by_proposal: Mapping[str, tuple[str, ...]],
        page_text_extractor: Callable[[bytes], tuple[str, ...]] | None = None,
    ) -> None:
        if not isinstance(stage, IccActionStage):
            raise ValueError("stage must be an IccActionStage")
        if not isinstance(affected_locators_by_proposal, Mapping):
            raise ValueError("affected_locators_by_proposal must be a mapping")
        normalized: dict[str, tuple[str, ...]] = {}
        for proposal_id, locators in affected_locators_by_proposal.items():
            heading = _PROPOSAL_HEADING_RE.fullmatch(proposal_id)
            if heading is None or heading.group("part") is not None:
                raise ValueError("affected locator mapping contains an invalid proposal id")
            if not isinstance(locators, tuple) or not locators:
                raise ValueError("affected locator mapping values must be nonempty tuples")
            normalized[proposal_id] = locators
        if page_text_extractor is not None and not callable(page_text_extractor):
            raise ValueError("page_text_extractor must be callable")
        self.stage = stage
        self.affected_locators_by_proposal = normalized
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
            headings: list[tuple[int, re.Match[str]]] = []
            for index, line in enumerate(lines):
                heading = _PROPOSAL_HEADING_RE.fullmatch(line)
                if heading is not None:
                    headings.append((index, heading))

            for heading_index, (line_index, heading) in enumerate(headings):
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

                next_index = (
                    headings[heading_index + 1][0]
                    if heading_index + 1 < len(headings)
                    else len(lines)
                )
                action_text = _bounded_action(lines[line_index + 1 : next_index])
                if action_text is None:
                    continue

                region = SourceRegion(
                    page=page_number,
                    anchor=f"{proposal_id}:{self.stage.record_key_suffix}",
                )
                disposition = _action_disposition(action_text)
                if disposition is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unsupported-official-development-action",
                            severity=DiagnosticSeverity.WARNING,
                            message="Committee action is outside the bounded disposition vocabulary.",
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    seen.add(proposal_id)
                    continue

                locators = self.affected_locators_by_proposal.get(proposal_id)
                if locators is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unresolved-development-proposal-locators",
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                "Committee action has no registered proposal locator mapping; "
                                "the adapter will not invent affected provisions."
                            ),
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    seen.add(proposal_id)
                    continue

                record_key = f"{proposal_id}:{self.stage.record_key_suffix}"
                records.append(
                    DevelopmentRecord(
                        source_id=source.source_id,
                        proposal_id=proposal_id,
                        record_key=record_key,
                        kind=self.stage.record_kind,
                        disposition=disposition,
                        sequence=self.stage.sequence,
                        proponent=None,
                        affected_locators=locators,
                        parent_keys=(f"{proposal_id}:{self.stage.parent_key_suffix}",),
                        action_date=self.stage.action_date,
                        summary=f"Official ICC committee action: {disposition.value}.",
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
