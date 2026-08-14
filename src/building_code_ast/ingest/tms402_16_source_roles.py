"""Bounded TMS 402-16 observation production from recovered source regions.

The retained TMS 402/602-16 artifact is image-based and presents normative
code beside informational commentary on many, but not all, TMS 402 pages.
This module consumes coordinate-bearing OCR/recovery regions and requires an
explicit publication-specific authority policy before assigning source role.
Generic recovery provenance contains no left/right authority semantics.
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
class Tms402AuthorityPolicy:
    """Publication evidence required to map recovered regions to source roles."""

    first_component_page: int
    first_code_page: int
    last_component_page: int
    top_content_y: float
    bottom_content_y: float
    code_commentary_boundary_x: float
    required_parallel_layout: Tms402PageLayout = Tms402PageLayout.PARALLEL_CODE_COMMENTARY

    def __post_init__(self) -> None:
        if self.first_component_page < 1:
            raise ValueError("TMS 402 authority policy first component page must be positive")
        if not self.first_component_page <= self.first_code_page <= self.last_component_page:
            raise ValueError("TMS 402 authority policy page extent is invalid")
        if self.bottom_content_y <= self.top_content_y:
            raise ValueError("TMS 402 authority policy body bounds are invalid")
        if self.code_commentary_boundary_x <= 0.0:
            raise ValueError("TMS 402 authority policy column boundary must be positive")
        if not isinstance(self.required_parallel_layout, Tms402PageLayout):
            object.__setattr__(
                self,
                "required_parallel_layout",
                Tms402PageLayout(self.required_parallel_layout),
            )


TMS402_AUTHORITY_POLICY = Tms402AuthorityPolicy(
    first_component_page=57,
    first_code_page=67,
    last_component_page=320,
    top_content_y=65.0,
    bottom_content_y=750.0,
    code_commentary_boundary_x=306.0,
)


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


def _classify_region(
    region: Tms402RecoveredRegion,
    policy: Tms402AuthorityPolicy,
) -> RoleQualifiedTms402Region:
    page = region.block.page_number
    if page < policy.first_component_page or page > policy.last_component_page:
        raise ValueError(
            "TMS 402 observation production is bounded to PDF pages "
            f"{policy.first_component_page}-{policy.last_component_page}"
        )

    if page < policy.first_code_page:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.AMBIGUOUS,
            role_evidence="component front matter precedes the publication policy's first code page",
        )

    _, y0, _, y1 = region.block.bbox
    if y0 < policy.top_content_y or y1 > policy.bottom_content_y:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.AMBIGUOUS,
            role_evidence="region lies outside the publication policy's body-content bounds",
        )

    if region.page_layout is not policy.required_parallel_layout:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.AMBIGUOUS,
            role_evidence="page layout does not satisfy the explicit publication authority policy",
        )

    x0, _, x1, _ = region.block.bbox
    boundary = policy.code_commentary_boundary_x
    if x1 <= boundary:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.NORMATIVE,
            role_evidence="publication parallel-layout policy; region lies wholly on code side",
        )
    if x0 >= boundary:
        return RoleQualifiedTms402Region(
            region=region,
            source_role=Tms402SourceRole.COMMENTARY,
            role_evidence="publication parallel-layout policy; region lies wholly on commentary side",
        )
    return RoleQualifiedTms402Region(
        region=region,
        source_role=Tms402SourceRole.AMBIGUOUS,
        role_evidence="region crosses the publication policy's code/commentary authority boundary",
    )


def produce_tms402_16_observations(
    regions: Iterable[Tms402RecoveredRegion],
    *,
    source_artifact: DocumentSourceArtifact,
    authority_policy: Tms402AuthorityPolicy = TMS402_AUTHORITY_POLICY,
) -> Tms402ObservationProduction:
    """Classify recovered regions and emit only authority-safe parser inputs.

    Generic OCR/recovery provenance does not imply authority. A region becomes
    normative or commentary only when the explicit TMS publication policy says
    the page/layout/coordinates support that role. All other in-range regions
    remain explicit ambiguous evidence.
    """

    _validate_source_artifact(source_artifact)
    return Tms402ObservationProduction(
        classified_regions=tuple(
            _classify_region(region, authority_policy) for region in regions
        )
    )
