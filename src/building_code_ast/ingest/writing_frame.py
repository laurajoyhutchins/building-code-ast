"""Publication-neutral coordinate projection into a text writing frame."""

from __future__ import annotations

import math


BBox = tuple[float, float, float, float]
Direction = tuple[float, float]


def project_bbox_to_writing_frame(bbox: BBox, direction: Direction) -> BBox:
    """Project an axis-aligned page bbox into inline/block-flow coordinates.

    The normalized writing direction defines the inline axis. Its left normal,
    ``(-dy, dx)``, defines the block-flow axis. Horizontal ``(1, 0)`` text is
    therefore an identity transform. The function preserves geometry only; it
    assigns no reading order, ownership, or semantic meaning.
    """

    dx, dy = (float(direction[0]), float(direction[1]))
    magnitude = math.hypot(dx, dy)
    if magnitude <= 0.0:
        raise ValueError("writing direction must be non-zero")
    dx /= magnitude
    dy /= magnitude
    nx, ny = -dy, dx

    x0, y0, x1, y1 = (float(value) for value in bbox)
    corners = (
        (x0, y0),
        (x0, y1),
        (x1, y0),
        (x1, y1),
    )
    inline = tuple(x * dx + y * dy for x, y in corners)
    block = tuple(x * nx + y * ny for x, y in corners)
    return (
        min(inline),
        min(block),
        max(inline),
        max(block),
    )
