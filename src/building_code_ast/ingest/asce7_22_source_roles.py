"""Bounded ASCE/SEI 7-22 source-role discrimination.

The whole-document replay measurement established that locator-shaped text occurs
in normative, commentary, appendix, and reference contexts. This module keeps
that context explicit before the Document AST adapter is allowed to promote an
observation as a normative structural declaration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .asce7_22 import Asce7Observation


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


def normative_structural_observations(
    observations: Iterable[RoleQualifiedAsce7Observation],
) -> tuple[Asce7Observation, ...]:
    """Return only observations justified as normative structural declarations.

    Commentary, appendix, reference, and ambiguous observations remain available
    to callers as role-qualified evidence, but are deliberately not fed into the
    numeric-only structural adapter. This prevents duplicate publication
    locators from being resolved by silently promoting non-normative material.
    """

    return tuple(
        qualified.observation
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
