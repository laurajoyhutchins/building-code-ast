"""Conservative alias reconciliation for source-safe IBC 2018 citations.

The module never infers incorporation by reference or document meaning. It only
links an observed citation to a Chapter 35 family when a normalized alias has a
single eligible family target.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping, Sequence


_EDITION_DASH_RE = re.compile(r"[\u2012\u2013\u2014]\s*(?=\d)")
_TRAILING_CAPTURE_RE = re.compile(r"^(.*?)(?:[\s.]+)([A-Z])\.?$")
_NON_KEY_RE = re.compile(r"[^A-Z0-9./()\-]+")
_KNOWN_PREFIXES = (
    "ASCE/SEI",
    "ANSI/AISC",
    "AAMA/WDMA/CSA",
    "ANSI/APA",
    "ANSI/AWC",
    "ASME",
    "ANSI",
    "AISC",
    "AISI",
    "ASTM",
    "ASCE",
    "SEI",
    "ICC",
    "CSA",
    "CPA",
    "AWS",
    "AAMA",
    "WDMA",
    "APA",
    "AWC",
    "NFPA",
    "ULC",
    "UL",
    "CPSC",
)


@dataclass(frozen=True)
class FamilyAliasIndex:
    """Unique and ambiguous alias projections for Chapter 35 families."""

    unique_by_agency: Mapping[tuple[str, str], str]
    ambiguous_by_agency: frozenset[tuple[str, str]]
    unique_by_declared_prefix: Mapping[tuple[str, str], str]
    ambiguous_by_declared_prefix: frozenset[tuple[str, str]]
    family_agency: Mapping[str, str]


def _strip_edition(value: str) -> str:
    match = _EDITION_DASH_RE.search(value)
    return value[: match.start()] if match else value


def _key(value: str) -> str:
    value = value.upper().strip().replace("–", "-").replace("—", "-")
    value = re.sub(r"\s*/\s*", "/", value)
    value = _NON_KEY_RE.sub("", value)
    return value.strip(".,;:")


def _agency_aliases(value: str) -> tuple[str, ...]:
    canonical = _key(value)
    aliases = {canonical}
    aliases.update(part for part in canonical.split("/") if part)
    return tuple(sorted(alias for alias in aliases if alias))


def _remove_known_prefixes(value: str) -> set[str]:
    aliases: set[str] = set()
    pending = [value]
    visited: set[str] = set()
    normalized_prefixes = tuple(_key(prefix) for prefix in _KNOWN_PREFIXES)
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        for prefix in normalized_prefixes:
            if current.startswith(prefix) and len(current) > len(prefix):
                remainder = current[len(prefix) :].lstrip("/-")
                if remainder and remainder not in visited:
                    aliases.add(remainder)
                    pending.append(remainder)
    return aliases


def _designation_aliases(value: str) -> set[str]:
    base = _key(_strip_edition(value))
    if not base:
        return set()
    aliases = {base}
    aliases.update(_remove_known_prefixes(base))

    # Paired inch-pound / metric identifiers commonly use D226/D226M. Keep
    # both complete identifiers as aliases without attempting fuzzy matching.
    for candidate in tuple(aliases):
        parts = [part for part in candidate.split("/") if part]
        if len(parts) == 2:
            left, right = parts
            if right == f"{left}M" or left == f"{right}M":
                aliases.update(parts)
            elif re.match(r"^[A-Z]?\d+(?:\.\d+)?$", left) and re.match(
                r"^[A-Z]{2,}\w*", right
            ):
                # Compound citations such as A17.1/CSA B44 may safely expose
                # their first designation under the citation's agency.
                aliases.add(left)

    # Removing known prefixes can expose another slash pair, so perform one
    # final exact-prefix and pair expansion.
    expanded = set(aliases)
    for candidate in aliases:
        expanded.update(_remove_known_prefixes(candidate))
        parts = [part for part in candidate.split("/") if part]
        if len(parts) == 2 and parts[1] == f"{parts[0]}M":
            expanded.update(parts)
    return {item for item in expanded if item}


def _unique_projection(
    values: Mapping[Any, set[str]],
) -> tuple[dict[Any, str], frozenset[Any]]:
    unique = {key: next(iter(ids)) for key, ids in values.items() if len(ids) == 1}
    ambiguous = frozenset(key for key, ids in values.items() if len(ids) > 1)
    return unique, ambiguous


def _declared_prefix_agencies(value: str) -> set[str]:
    base = _key(_strip_edition(value))
    agencies: set[str] = set()
    for prefix in _KNOWN_PREFIXES:
        normalized = _key(prefix)
        if base.startswith(normalized) and len(base) > len(normalized):
            agencies.update(_agency_aliases(prefix))
    return agencies


def build_family_alias_index(families: Sequence[Mapping[str, Any]]) -> FamilyAliasIndex:
    by_agency: dict[tuple[str, str], set[str]] = defaultdict(set)
    by_declared_prefix: dict[tuple[str, str], set[str]] = defaultdict(set)
    family_agency: dict[str, str] = {}

    for family in families:
        family_id = str(family["id"])
        organization = str(family.get("issuing_organization") or "")
        family_agency[family_id] = _key(organization)
        agencies = _agency_aliases(organization)
        observed_values: list[str] = [str(family.get("document_family") or "")]
        observed_values.extend(str(value) for value in family.get("observed_designations", []))
        aliases: set[str] = set()
        declared_prefixes: set[str] = set()
        for observed in observed_values:
            aliases.update(_designation_aliases(observed))
            declared_prefixes.update(_declared_prefix_agencies(observed))
        for alias in aliases:
            for agency in agencies:
                by_agency[(agency, alias)].add(family_id)
            for prefix_agency in declared_prefixes:
                by_declared_prefix[(prefix_agency, alias)].add(family_id)

    unique_by_agency, ambiguous_by_agency = _unique_projection(by_agency)
    unique_by_declared_prefix, ambiguous_by_declared_prefix = _unique_projection(by_declared_prefix)
    return FamilyAliasIndex(
        unique_by_agency=unique_by_agency,
        ambiguous_by_agency=ambiguous_by_agency,
        unique_by_declared_prefix=unique_by_declared_prefix,
        ambiguous_by_declared_prefix=ambiguous_by_declared_prefix,
        family_agency=family_agency,
    )


def _citation_candidates(value: str) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(alias: str, reason: str) -> None:
        for normalized in sorted(_designation_aliases(alias)):
            if normalized not in seen:
                seen.add(normalized)
                candidates.append((normalized, reason))

    add(value, "normalized_unique_alias")
    trailing = _TRAILING_CAPTURE_RE.match(value.strip().upper())
    if trailing:
        add(trailing.group(1), "trimmed_trailing_capture_artifact")
    return candidates


def reconcile_external_citations(
    citations: Sequence[Mapping[str, Any]],
    families: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return copied citation records with only unique alias matches promoted."""

    index = build_family_alias_index(families)
    reconciled: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    preserved = 0
    newly_matched = 0

    for citation in citations:
        record = dict(citation)
        existing = record.get("normalized_document_family_id")
        if existing:
            reason = "preserved_existing_family_match"
            preserved += 1
        else:
            family_id: str | None = None
            reason = "no_unique_family_alias"
            citation_agency = _key(str(record.get("issuing_organization") or ""))
            candidates = _citation_candidates(str(record.get("observed_designation") or ""))

            for alias, transform_reason in candidates:
                family_id = index.unique_by_agency.get((citation_agency, alias))
                if family_id is None:
                    continue
                actual_agency = index.family_agency.get(family_id, "")
                if transform_reason == "trimmed_trailing_capture_artifact":
                    reason = transform_reason
                elif actual_agency != citation_agency:
                    reason = "agency_alias_unique"
                else:
                    reason = "same_agency_unique_alias"
                break

            if family_id is None:
                for alias, transform_reason in candidates:
                    family_id = index.unique_by_declared_prefix.get((citation_agency, alias))
                    if family_id is None:
                        continue
                    if transform_reason == "trimmed_trailing_capture_artifact":
                        reason = transform_reason
                    else:
                        reason = "unique_designation_alias"
                    break

            if family_id is not None:
                record["normalized_document_family_id"] = family_id
                record["normalization_confidence"] = 0.85 if reason != "unique_designation_alias" else 0.75
                record["review_state"] = "provisional"
                newly_matched += 1
            else:
                record["normalized_document_family_id"] = None
                record["normalization_confidence"] = min(
                    float(record.get("normalization_confidence") or 0.45), 0.45
                )
                record["review_state"] = "disputed"

        record["normalization_reason"] = reason
        reason_counts[reason] += 1
        reconciled.append(record)

    unmatched = sum(item.get("normalized_document_family_id") is None for item in reconciled)
    summary = {
        "record_count": len(reconciled),
        "preserved_match_count": preserved,
        "newly_matched_count": newly_matched,
        "matched_count": len(reconciled) - unmatched,
        "unmatched_count": unmatched,
        "normalization_reason_counts": dict(sorted(reason_counts.items())),
        "policy": "unique normalized aliases only; no fuzzy or semantic matching",
    }
    return reconciled, summary
