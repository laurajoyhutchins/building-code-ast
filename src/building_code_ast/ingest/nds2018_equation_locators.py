"""Source-backed NDS 2018 equation-locator grammar.

The whole-document measurement exposed appendix equation labels outside the
numeric chapter/section grammar used by the first non-prose adapter. This
module owns only locator recognition. It does not parse equation mathematics
or infer appendix identity from sequence.
"""

from __future__ import annotations

import re


# Body equations are section-qualified numeric locators such as 12.1-1.
# Exact-source appendix observations use an explicit native appendix letter,
# optionally followed by a decimal subsection, such as D-1 or E.4-1.
_EQUATION_LOCATOR_RE = re.compile(
    r"^(?:\d+(?:\.\d+)+-\d+|[A-N](?:\.\d+)?-\d+)$"
)


def normalize_nds2018_equation_locator(value: str) -> str | None:
    """Return a native NDS equation locator only when its grammar is explicit."""

    locator = value.strip()
    if _EQUATION_LOCATOR_RE.fullmatch(locator) is None:
        return None
    return locator


def match_nds2018_equation_label(text: str) -> str | None:
    """Recognize a standalone parenthesized native NDS equation label."""

    value = text.strip()
    if len(value) < 3 or not (value.startswith("(") and value.endswith(")")):
        return None
    return normalize_nds2018_equation_locator(value[1:-1])
