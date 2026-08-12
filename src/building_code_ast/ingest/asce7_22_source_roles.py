"""Bounded ASCE/SEI 7-22 source-role and declaration-context discrimination.

The whole-document replay measurement established that locator-shaped text occurs
in normative, commentary, appendix, and reference contexts. This module first
requires explicit source-role evidence, then uses preserved exact-source
font/size evidence only to decide whether a normative numeric candidate is an
actual section declaration. Typography is evidence, not source-role authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import re
from typing import Iterable

from .asce7_22 import Asce7Observation
from .pdf_layout import PdfSpan, normalize_block_text


_NUMERIC_SECTION_CANDIDATE_RE = re.compile(r"^\d+\.\d+(?:\.\d+)*\s+\S.*$")
_DECLARATION_FONT_SUFFIX = ".B"
_DECLARATION_FONT_SIZE = 9.5
_DECLARATION_FONT_SIZE_TOLERANCE = 0.05


class Asce7SourceRole(StrEnum):
    NORMATIVE = "normative"
    COMMENTARY = "commentary"
    APPENDIX = "appendix"
    REFERENCE = "reference"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class RoleQualifiedAsce7Observation:
    observation: Asce7Observation
    source_role: Asce7SourceRole
    role_evidence: str

    def __post_init__(self) -> None:
        if not self.role_evidence.strip():
            raise ValueError("ASCE source-role evidence must be explicit")


def _first_text_span(observation: Asce7Observation) -> PdfSpan | None:
    for line in observation.block.lines:
        for span in line.spans:
            if span.text.strip():
                return span
    return None


def _is_numeric_section_candidate(observation: Asce7Observation) -> bool:
    if observation.structure_hint is not None:
        return False
    return _NUMERIC_SECTION_CANDIDATE_RE.fullmatch(
        normalize_block_text(observation.block.text)
    ) is not None


def _has_declaration_typography(observation: Asce7Observation) -> bool:
    span = _first_text_span(observation)
    if span is None:
        return False
    return span.font.endswith(_DECLARATION_FONT_SUFFIX) and abs(
        span.size - _DECLARATION_FONT_SIZE
    ) <= _DECLARATION_FONT_SIZE_TOLERANCE


def _with_declaration_context(observation: Asce7Observation) -> Asce7Observation:
    if not _is_numeric_section_candidate(observation):
        return observation
    return replace(
        observation,
        section_declaration=_has_declaration_typography(observation),
    )


def normative_structural_observations(
    observations: Iterable[RoleQualifiedAsce7Observation],
) -> tuple[Asce7Observation, ...]:
    """Return source-role-qualified observations for normative structural parsing.

    Commentary, appendix, reference, and ambiguous observations remain available
    to callers as role-qualified evidence and are deliberately not fed into the
    normative parser. Within the explicitly normative stream, numeric section
    candidates are marked as declarations only when preserved first-span
    typography matches the exact-source declaration family. Missing, regular,
    bold-italic, or size-mismatched evidence fails closed as non-declaration.
    """

    return tuple(
        _with_declaration_context(qualified.observation)
        for qualified in observations
        if qualified.source_role is Asce7SourceRole.NORMATIVE
    )


def observations_by_role(
    observations: Iterable[RoleQualifiedAsce7Observation],
) -> dict[Asce7SourceRole, tuple[RoleQualifiedAsce7Observation, ...]]:
    """Partition observations without discarding non-normative source evidence."""

    buckets: dict[Asce7SourceRole, list[RoleQualifiedAsce7Observation]] = {
        role: [] for role in Asce7SourceRole
    }
    for observation in observations:
        buckets[observation.source_role].append(observation)
    return {role: tuple(items) for role, items in buckets.items()}
