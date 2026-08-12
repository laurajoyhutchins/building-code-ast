"""Bounded TMS 402-16 observation production from recovered source regions.

The retained TMS 402/602-16 artifact is image-based and presents normative
code beside informational commentary on many, but not all, TMS 402 pages.
This module consumes coordinate-bearing OCR/recovery regions and requires
explicit page-layout evidence before assigning normative authority. Unsupported
layouts, page furniture, front matter, and regions crossing the code/commentary
boundary remain explicitly ambiguous and are not emitted as parser inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from ..document_model import DocumentSourceArtifact
from .pdf_layout import PdfBlock
from .tms402_16 import Tms402Observation


_TMS402_ARTIFACT_ID = (
    "sha256:947476cf326fef261cb6af581565c8089945c6651eb054d791b5c910431f8e1d"
)
_TMS402_COMPONENT_ID = "tms-402-16"
_TMS402_FIRST_PAGE = 57
_TMS402_FIRST_CODE_PAGE = 67
_TMS402_LAST_PAGE = 320
_TOP_CONTENT_Y = 65.0
_BOTTOM_CONTENT_Y = 750.0
_BODY_MIDPOINT = 306.0
_SUPPORTED_TEXT_ORIGINS = {"ocr"}


class Tms402SourceRole(StrEnum):
    NORMATIVE = "normative"
    COMMENTARY = "commentary"
    AMBIGUOUS = "ambiguous"


class Tms402PageLayout(StrEnum):
    """Recovered page-layout evidence relevant to source authority."""

    PARALLEL_CODE_COMMENTARY = "parallel_code_commentary"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class Tms402RecoveredRegion:
    """One OCR/recovery region before publication-role assignment.

    ``block`` preserves the artifact-local PDF page and region coordinates.
    ``recovery_origin`` identifies the recovery/OCR path that produced the text.
    ``page_layout`` is explicit recovery evidence; it defaults fail-closed rather
    than assuming that every page in the component has parallel code/commentary.
    """

    block: PdfBlock
    recovery_origin: str
    page_layout: Tms402PageLayout = Tms402PageLayout.UNSUPPORTED
    printed_page: str | None = None
    text_origin: str = "ocr"
    structure_hint: str | None = None
    native_locator: str | None = None

    def __post_init__(self) -> None:
        if not self.recovery_origin.strip():
            raise ValueError("TMS 402 recovery origin must be explicit")
        if self.text_origin not in _SUPPORTED_TEXT_ORIGINS:
            raise ValueError("retained TMS 402/602-16 recovery requires OCR text origin")
        if not isinstance(self.page_layout, Tms402PageLayout):
            object.__setattr__(self, "page_layout", Tms402PageLayout(self.page_layout))


@dataclass(frozen=True, slots=True)
class RoleQualifiedTms402Region:
    """Recovered region with explicit publication-role evidence."""

    region: Tms402RecoveredRegion
    source_role: Tms402SourceRole
    role_evidence: str

    def __post_init__(self) -> None:
        if not self.role_evidence.strip():
            raise ValueError("TMS 402 source-role evidence must be explicit")

    @property
    def recovery_origin(self) -> str:
        return self.region.recovery_origin

    def to_observation(self) -> Tms402Observation | None:
        """Materialize a current parser input, excluding ambiguous authority."""

        if self.source_role is Tms402SourceRole.AMBIGUOUS:
            return None
        region = self.region
        return Tms402Observation(
            block=region.block,
            printed_page=region.printed_page,
            source_role=self.source_role.value,
            text_origin=region.text_origin,
            structure_hint=region.structure_hint,
            native_locator=region.native_locator,
        )


@dataclass(frozen=True, slots=True)
class Tms402ObservationProduction:
    """Source-role evidence plus the safe current ``Tms402Observation`` stream."""

    classified_regions: tuple[RoleQualifiedTms402Region, ...]

    @property
    def observations(self) -> tuple[Tms402Observation, ...]:
        observations: list[Tms402Observation] = []
        for classified in self.classified_regions:
            observation = classified.to_observation()
            if observation is not None:
                observations.append(observation)
        return tuple(observations)

    @property
    def ambiguous_regions(self) -> tuple[RoleQualifiedTms402Region, ...]:
        return tuple(
            classified
            for classified in self.classified_regions
            if classified.source_role is Tms402SourceRole.AMBIGUOUS
        )


def _validate_source_artifact(source_artifact: DocumentSourceArtifact) -> None:
    if (
        source_artifact.artifact_id != _TMS402_ARTIFACT_ID
        or source_artifact.publication_component_id != _TMS402_COMPONENT_ID
    ):
        raise ValueError(
            "TMS 402 observation production requires the exact retained "
            "TMS 402/602-16 artifact and publication_component_id='tms-402-16'"
        )


def _classify_region(region: Tms402RecoveredRegion) -> RoleQualifiedTms402Region:
    page = region.block.page_number
    if page < _TMS402_FIRST_PAGE or page > _TMS402_LAST_PAGE:
        raise ValueError("TMS 402 observation production is bounded to PDF pages 57-320")

    if page < _TMS402_FIRST_CODE_PAGE:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.AMBIGUOUS,
            role_evidence="component front matter precedes the canonical C-1 code page",
        )

    _, y0, _, y1 = region.block.bbox
    if y0 < _TOP_CONTENT_Y or y1 > _BOTTOM_CONTENT_Y:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.AMBIGUOUS,
            role_evidence="region lies outside the canonical TMS 402 body-content bounds",
        )

    if region.page_layout is not Tms402PageLayout.PARALLEL_CODE_COMMENTARY:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.AMBIGUOUS,
            role_evidence="page layout is not explicitly recovered as parallel code/commentary",
        )

    x0, _, x1, _ = region.block.bbox
    if x1 <= _BODY_MIDPOINT:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.NORMATIVE,
            role_evidence="parallel code/commentary layout; region lies wholly left of boundary",
        )
    if x0 >= _BODY_MIDPOINT:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.COMMENTARY,
            role_evidence="parallel code/commentary layout; region lies wholly right of boundary",
        )
    return RoleQualifiedTms402Region(
        region=region,
        source_role=Tms402SourceRole.AMBIGUOUS,
        role_evidence="region crosses the normative/commentary authority boundary",
    )


def produce_tms402_16_observations(
    regions: Iterable[Tms402RecoveredRegion],
    *,
    source_artifact: DocumentSourceArtifact,
) -> Tms402ObservationProduction:
    """Classify recovered regions and emit only authority-safe parser inputs.

    The producer is intentionally bounded to the canonical TMS 402 component in
    the exact retained artifact. A region becomes normative or commentary only
    when it lies within body-content bounds, recovery has explicitly established
    the parallel code/commentary page layout, and the region lies wholly on one
    side of the artifact-local 306 pt boundary. All other in-range regions remain
    explicit ambiguous evidence.
    """

    _validate_source_artifact(source_artifact)
    return Tms402ObservationProduction(
        classified_regions=tuple(_classify_region(region) for region in regions)
    )
