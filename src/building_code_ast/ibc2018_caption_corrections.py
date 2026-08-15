"""Source-safe declarative corrections for known IBC 2018 caption anomalies."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


IBC2018_SOURCE_SHA256 = "c8f0b75522707a39daf5202edee25d7fdce6c177c382f828a6dc1dfd5cc0b18d"


class CaptionCorrectionAction(StrEnum):
    REPLACE_IDENTIFIER_PREFIX = "replace_identifier_prefix"
    SUPPRESS = "suppress"
    PROMOTE_SUFFIX_PREFIX = "promote_suffix_prefix"


@dataclass(frozen=True, slots=True)
class CaptionCorrection:
    correction_id: str
    source_sha256: str
    rationale: str
    action: CaptionCorrectionAction
    kind: str = "table"
    pdf_page: int | None = None
    text_prefix: str | None = None
    identifier: str | None = None
    suffix_prefix: str | None = None
    replacement_identifier_prefix: str | None = None
    identifier_prefix_length: int = 0
    promoted_suffix_length: int = 0

    def matches(
        self,
        *,
        text: str,
        pdf_page: int,
        kind: str,
        identifier: str,
        suffix: str,
    ) -> bool:
        return (
            kind == self.kind
            and (self.pdf_page is None or pdf_page == self.pdf_page)
            and (self.text_prefix is None or text.startswith(self.text_prefix))
            and (self.identifier is None or identifier == self.identifier)
            and (self.suffix_prefix is None or suffix.startswith(self.suffix_prefix))
        )


CAPTION_CORRECTIONS: tuple[CaptionCorrection, ...] = (
    CaptionCorrection(
        correction_id="caption.table-1010-split-identifier",
        source_sha256=IBC2018_SOURCE_SHA256,
        rationale=(
            "Normalize the source-observed split four-digit table identifier without "
            "changing the remaining caption payload."
        ),
        action=CaptionCorrectionAction.REPLACE_IDENTIFIER_PREFIX,
        text_prefix="TABLE 1 010",
        replacement_identifier_prefix="1010",
        identifier_prefix_length=1,
    ),
    CaptionCorrection(
        correction_id="caption.page-556-embedded-table-label",
        source_sha256=IBC2018_SOURCE_SHA256,
        rationale=(
            "Exclude table-like labels on the source-safe page coordinate already "
            "classified as embedded figure detections."
        ),
        action=CaptionCorrectionAction.SUPPRESS,
        pdf_page=556,
    ),
    CaptionCorrection(
        correction_id="caption.table-4-hyphenated-identifier",
        source_sha256=IBC2018_SOURCE_SHA256,
        rationale=(
            "Fold the source-observed hyphenated fragment into the published table "
            "identifier instead of retaining it as caption suffix."
        ),
        action=CaptionCorrectionAction.PROMOTE_SUFFIX_PREFIX,
        identifier="4",
        suffix_prefix="-",
        promoted_suffix_length=2,
    ),
)


def apply_caption_corrections(
    *,
    text: str,
    pdf_page: int,
    kind: str,
    identifier: str,
    suffix: str,
    designation: str,
) -> tuple[str, str, str, str] | None:
    """Apply only registered exact-source corrections in deterministic order."""

    for correction in CAPTION_CORRECTIONS:
        if not correction.matches(
            text=text,
            pdf_page=pdf_page,
            kind=kind,
            identifier=identifier,
            suffix=suffix,
        ):
            continue
        if correction.action is CaptionCorrectionAction.SUPPRESS:
            return None
        if correction.action is CaptionCorrectionAction.REPLACE_IDENTIFIER_PREFIX:
            if correction.replacement_identifier_prefix is None:
                raise ValueError(f"{correction.correction_id} is missing a replacement prefix")
            identifier = (
                correction.replacement_identifier_prefix
                + identifier[correction.identifier_prefix_length :]
            )
            continue
        if correction.action is CaptionCorrectionAction.PROMOTE_SUFFIX_PREFIX:
            promoted = suffix[: correction.promoted_suffix_length]
            identifier = f"{identifier}{promoted}"
            suffix = suffix[correction.promoted_suffix_length :].strip()
            continue
        raise ValueError(f"unsupported caption correction action: {correction.action}")
    return kind, identifier, suffix, designation
