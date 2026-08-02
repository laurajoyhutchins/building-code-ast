"""Official Washington WAC HTML extraction for the current state-site layout."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from html.parser import HTMLParser

from ..model import DiagnosticSeverity
from .adapters import AdapterResult, EvidenceDiagnostic, SourceRegion
from .amendments import (
    AmendmentOperation,
    JurisdictionalAmendmentPatch,
    _PUBLICATION_STATE_RE,
    _group_clause_texts,
    _optional_date,
    _parse_date,
    _require_text,
    _resolve_operation,
    _validated_date_mapping,
    _validated_locator_date_mapping,
    _validated_locator_mapping,
    _wac_sections,
)
from .model import EvidenceRole, SourceRegisterEntry


class _ScopedOfficialWacBlockParser(HTMLParser):
    """Capture headings plus leaf span blocks inside the official section body."""

    _GLOBAL_BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._stack: list[tuple[str, frozenset[str]]] = []
        self._capture_tag: str | None = None
        self._buffer: list[str] = []

    def _inside_section_page(self) -> bool:
        return any(
            tag == "div" and "section-page" in classes
            for tag, classes in self._stack
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = frozenset((values.get("class") or "").split())
        inside_section_page = self._inside_section_page()

        if self._capture_tag is None and tag in self._GLOBAL_BLOCK_TAGS:
            self._capture_tag = tag
            self._buffer = []
        elif self._capture_tag is None and tag == "span" and inside_section_page:
            self._capture_tag = tag
            self._buffer = []
        elif self._capture_tag is not None and tag == "br":
            self._buffer.append(" ")

        self._stack.append((tag, classes))

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._capture_tag is not None:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture_tag == tag:
            text = " ".join("".join(self._buffer).split())
            if text:
                self.blocks.append(text)
            self._capture_tag = None
            self._buffer = []

        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tag:
                del self._stack[index:]
                break


def _parse_scoped_official_blocks(content: bytes) -> tuple[str, ...]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Washington WAC HTML must be UTF-8") from exc
    parser = _ScopedOfficialWacBlockParser()
    parser.feed(text)
    parser.close()
    return tuple(parser.blocks)


class WashingtonOfficialWacHtmlAdapter:
    """Extract bounded patches from the official chapter 51-50 WAC website."""

    adapter_id = "washington-wac-html"
    adapter_version = "0.4.0"
    supported_roles = frozenset({EvidenceRole.JURISDICTIONAL_LAW})
    supported_media_types = frozenset({"text/html"})

    def __init__(
        self,
        *,
        base_publication_state_id: str,
        known_base_locators: frozenset[str],
        effective_dates_by_wac: Mapping[str, str] | None = None,
        effective_to_dates_by_wac: Mapping[str, str] | None = None,
        effective_dates_by_locator: Mapping[str, str] | None = None,
        effective_to_dates_by_locator: Mapping[str, str] | None = None,
        reserved_locators_by_wac: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(base_publication_state_id, str) or _PUBLICATION_STATE_RE.fullmatch(
            base_publication_state_id
        ) is None:
            raise ValueError("base_publication_state_id must be a publication state identifier")
        if not isinstance(known_base_locators, frozenset) or not known_base_locators:
            raise ValueError("known_base_locators must be a nonempty frozenset")
        for locator in known_base_locators:
            _require_text(locator, "known base locator")
        self.base_publication_state_id = base_publication_state_id
        self.known_base_locators = known_base_locators
        self.effective_dates_by_wac = _validated_date_mapping(
            effective_dates_by_wac, "effective_dates_by_wac"
        )
        self.effective_to_dates_by_wac = _validated_date_mapping(
            effective_to_dates_by_wac, "effective_to_dates_by_wac"
        )
        self.effective_dates_by_locator = _validated_locator_date_mapping(
            effective_dates_by_locator, "effective_dates_by_locator"
        )
        self.effective_to_dates_by_locator = _validated_locator_date_mapping(
            effective_to_dates_by_locator, "effective_to_dates_by_locator"
        )
        self.reserved_locators_by_wac = _validated_locator_mapping(
            reserved_locators_by_wac, "reserved_locators_by_wac"
        )
        for citation, end_value in self.effective_to_dates_by_wac.items():
            start_value = self.effective_dates_by_wac.get(citation)
            if start_value is not None and date.fromisoformat(end_value) <= date.fromisoformat(
                start_value
            ):
                raise ValueError(
                    f"effective_to date for {citation} must be later than effective_from"
                )
        for locator, end_value in self.effective_to_dates_by_locator.items():
            start_value = self.effective_dates_by_locator.get(locator)
            if start_value is not None and date.fromisoformat(end_value) <= date.fromisoformat(
                start_value
            ):
                raise ValueError(
                    f"effective_to date for {locator} must be later than effective_from"
                )

    def _effective_from(
        self,
        citation: str,
        locator: str,
        source: SourceRegisterEntry,
    ) -> str | None:
        return (
            self.effective_dates_by_locator.get(locator)
            or self.effective_dates_by_wac.get(citation)
            or source.publication.effective_on
        )

    def _effective_to(self, citation: str, locator: str) -> str | None:
        return self.effective_to_dates_by_locator.get(
            locator,
            self.effective_to_dates_by_wac.get(citation),
        )

    def extract(
        self,
        source: SourceRegisterEntry,
        content: bytes,
    ) -> AdapterResult[JurisdictionalAmendmentPatch]:
        if source.jurisdiction is None:
            raise ValueError("source jurisdiction is required")
        sections = _wac_sections(_parse_scoped_official_blocks(content))
        records: list[JurisdictionalAmendmentPatch] = []
        diagnostics: list[EvidenceDiagnostic] = []
        unsupported: list[SourceRegion] = []
        candidate_sequence = 0

        for citation, blocks in sections:
            candidate_sequence += 1
            section_region = SourceRegion(anchor=f"wac:{citation}")
            if any(block.strip().casefold().rstrip(".") == "reserved" for block in blocks):
                locator = self.reserved_locators_by_wac.get(citation)
                if locator is None or locator not in self.known_base_locators:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unresolved-reserved-locator",
                            severity=DiagnosticSeverity.WARNING,
                            message="Reserved WAC section requires an explicit resolvable base locator.",
                            region=section_region,
                        )
                    )
                    unsupported.append(section_region)
                    continue
                effective_from = self._effective_from(citation, locator, source)
                if effective_from is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="missing-amendment-effective-date",
                            severity=DiagnosticSeverity.WARNING,
                            message="WAC section has no registered effective date.",
                            region=section_region,
                        )
                    )
                    unsupported.append(section_region)
                    continue
                records.append(
                    JurisdictionalAmendmentPatch(
                        source_id=source.source_id,
                        jurisdiction=source.jurisdiction,
                        authority=source.issuing_body,
                        base_publication_state_id=self.base_publication_state_id,
                        wac_citation=citation,
                        locator=locator,
                        operation=AmendmentOperation.RESERVE,
                        effective_from=effective_from,
                        effective_to=self._effective_to(citation, locator),
                        replacement_text=None,
                        scope=None,
                        sequence=candidate_sequence,
                        source_anchor=f"wac:{citation}:{locator}",
                    )
                )
                continue

            clauses = _group_clause_texts(blocks)
            if not clauses:
                diagnostics.append(
                    EvidenceDiagnostic(
                        code="unsupported-wac-section",
                        severity=DiagnosticSeverity.WARNING,
                        message="WAC section did not expose a bounded code locator or reserved marker.",
                        region=section_region,
                    )
                )
                unsupported.append(section_region)
                continue

            for clause_index, (locator, replacement_text) in enumerate(clauses):
                if clause_index:
                    candidate_sequence += 1
                region = SourceRegion(anchor=f"wac:{citation}:{locator}")
                effective_from = self._effective_from(citation, locator, source)
                if effective_from is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="missing-amendment-effective-date",
                            severity=DiagnosticSeverity.WARNING,
                            message="WAC clause has no registered effective date.",
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                operation = _resolve_operation(locator, self.known_base_locators)
                if operation is None:
                    diagnostics.append(
                        EvidenceDiagnostic(
                            code="unresolved-base-locator",
                            severity=DiagnosticSeverity.WARNING,
                            message=(
                                "WAC clause could not be classified as an add or replacement "
                                "against the supplied base-locator oracle."
                            ),
                            region=region,
                        )
                    )
                    unsupported.append(region)
                    continue
                records.append(
                    JurisdictionalAmendmentPatch(
                        source_id=source.source_id,
                        jurisdiction=source.jurisdiction,
                        authority=source.issuing_body,
                        base_publication_state_id=self.base_publication_state_id,
                        wac_citation=citation,
                        locator=locator,
                        operation=operation,
                        effective_from=effective_from,
                        effective_to=self._effective_to(citation, locator),
                        replacement_text=replacement_text,
                        scope=None,
                        sequence=candidate_sequence,
                        source_anchor=f"wac:{citation}:{locator}",
                    )
                )

        return AdapterResult(
            source_id=source.source_id,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
            records=tuple(records),
            diagnostics=tuple(diagnostics),
            unsupported_regions=tuple(unsupported),
        )


WashingtonWacHtmlAdapter = WashingtonOfficialWacHtmlAdapter
