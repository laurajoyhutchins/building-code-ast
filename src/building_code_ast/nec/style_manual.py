"""Edition-aware NEC Style Manual rules used as parser priors.

The profiles in this module describe expected editorial structure. They do not
replace source evidence, repair parser output, or assert that every published
NEC provision conforms perfectly to its applicable style manual.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re


NEC_STYLE_PROFILE_VERSION = "0.1.0"


class DefinitionPlacement(StrEnum):
    """Where document requirement definitions are expected to appear."""

    ARTICLE_100_OR_ARTICLE_LOCAL = "article_100_or_article_local"
    ARTICLE_100_ONLY = "article_100_only"


class ParallelNumberingPolicy(StrEnum):
    """Whether common section numbers across related Articles are advisory."""

    ENCOURAGED = "encouraged"
    REQUIRED = "required"


class ThirdLevelTitlePolicy(StrEnum):
    """Expected treatment of titles on third-level subdivisions."""

    OPTIONAL = "optional"
    OPTIONAL_BUT_SIBLING_CONSISTENT = "optional_but_sibling_consistent"


class MarkerRole(StrEnum):
    """Conservative interpretation of one parenthetical marker."""

    SUBDIVISION = "subdivision"
    LIST_ITEM = "list_item"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class NecStyleProfile:
    """One code-edition view of the relevant NEC Style Manual rules."""

    code_edition: int
    style_manual_edition: int
    source_url: str
    definition_placement: DefinitionPlacement
    parallel_numbering: ParallelNumberingPolicy
    third_level_title_policy: ThirdLevelTitlePolicy
    article_100_is_subdivided: bool = False
    informational_note_numbering_is_local: bool = True
    first_section_is_scope: bool = True
    named_subdivision_levels: int = 3
    profile_version: str = NEC_STYLE_PROFILE_VERSION


@dataclass(frozen=True, slots=True)
class MarkerInterpretation:
    """Evidence-backed marker role without pretending numbering is decisive."""

    role: MarkerRole
    confidence: str
    evidence: tuple[str, ...]


_PROFILES = {
    2017: NecStyleProfile(
        code_edition=2017,
        style_manual_edition=2015,
        source_url=(
            "https://docinfofiles.nfpa.org/files/AboutTheCodes/70/"
            "NEC_StyleManual_2015.pdf"
        ),
        definition_placement=DefinitionPlacement.ARTICLE_100_OR_ARTICLE_LOCAL,
        parallel_numbering=ParallelNumberingPolicy.ENCOURAGED,
        third_level_title_policy=ThirdLevelTitlePolicy.OPTIONAL,
    ),
    2020: NecStyleProfile(
        code_edition=2020,
        style_manual_edition=2020,
        source_url=(
            "https://docinfofiles.nfpa.org/files/AboutTheCodes/70E/"
            "NEC_Style_Manual_2020.pdf"
        ),
        definition_placement=DefinitionPlacement.ARTICLE_100_ONLY,
        parallel_numbering=ParallelNumberingPolicy.ENCOURAGED,
        third_level_title_policy=ThirdLevelTitlePolicy.OPTIONAL,
    ),
    2023: NecStyleProfile(
        code_edition=2023,
        style_manual_edition=2023,
        source_url=(
            "https://docinfofiles.nfpa.org/files/AboutTheCodes/70/"
            "NEC_Style_Manual_2023_v2.pdf"
        ),
        definition_placement=DefinitionPlacement.ARTICLE_100_ONLY,
        parallel_numbering=ParallelNumberingPolicy.REQUIRED,
        third_level_title_policy=(
            ThirdLevelTitlePolicy.OPTIONAL_BUT_SIBLING_CONSISTENT
        ),
    ),
}

_EDITION_RE = re.compile(r"(?<!\d)(2017|2020|2023)(?!\d)")


def style_profile_for_edition(edition: int | str) -> NecStyleProfile:
    """Return the supported profile identified by an NEC edition value.

    Edition recognition is deliberately exact. Unknown or test-only edition
    strings fail closed instead of silently inheriting the nearest known rules.
    """

    if isinstance(edition, int):
        year = edition
    else:
        match = _EDITION_RE.search(edition)
        if match is None:
            raise ValueError(f"unsupported NEC edition: {edition!r}")
        year = int(match.group(1))

    try:
        return _PROFILES[year]
    except KeyError as exc:
        raise ValueError(f"unsupported NEC edition: {edition!r}") from exc


def interpret_parenthetical_marker(
    *,
    edition: int | str,
    subdivision_level: int,
    has_title: bool,
    introduced_as_list: bool,
) -> MarkerInterpretation:
    """Interpret a marker from independent structural evidence.

    Parenthetical numbering alone is not enough to distinguish an NEC
    subdivision from a list item. A title is strong subdivision evidence; an
    explicit list introduction is strong list-item evidence. Conflicting or
    absent evidence remains visible as ambiguity.
    """

    profile = style_profile_for_edition(edition)
    if subdivision_level < 1:
        raise ValueError("subdivision_level must be at least 1")

    if has_title and introduced_as_list:
        return MarkerInterpretation(
            role=MarkerRole.AMBIGUOUS,
            confidence="low",
            evidence=("title", "list-introduction", "conflicting-evidence"),
        )
    if has_title:
        return MarkerInterpretation(
            role=MarkerRole.SUBDIVISION,
            confidence="high",
            evidence=("title",),
        )
    if introduced_as_list:
        return MarkerInterpretation(
            role=MarkerRole.LIST_ITEM,
            confidence="high",
            evidence=("list-introduction",),
        )

    evidence: list[str] = []
    if subdivision_level <= 2:
        evidence.append("title-expected-at-this-level")
    elif (
        subdivision_level == 3
        and profile.third_level_title_policy
        == ThirdLevelTitlePolicy.OPTIONAL_BUT_SIBLING_CONSISTENT
    ):
        evidence.append("third-level-sibling-title-context-needed")
    elif subdivision_level > profile.named_subdivision_levels:
        evidence.append("beyond-named-subdivision-levels")
    evidence.append("numbering-alone-is-insufficient")
    return MarkerInterpretation(
        role=MarkerRole.AMBIGUOUS,
        confidence="low",
        evidence=tuple(evidence),
    )


def informational_note_identity(owner_identity: str, note_number: int) -> str:
    """Return an owner-local informational-note identity.

    NEC informational-note numbers restart beneath their containing definition,
    section, or subdivision. Including the owner prevents false document-global
    collisions between notes that share the same displayed number.
    """

    owner = re.sub(r"\s+", "", owner_identity)
    if not owner:
        raise ValueError("owner_identity must not be empty")
    if note_number < 1:
        raise ValueError("note_number must be positive")
    return f"{owner}#informational-note:{note_number}"
