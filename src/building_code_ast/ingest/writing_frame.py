"""Publication-neutral coordinate projection into a text writing frame."""

from __future__ import annotations

import math


BBox = tuple[float, float, float, float]
Direction = tuple[float, float]


def _normalized_direction(direction: Direction) -> Direction:
    dx, dy = (float(direction[0]), float(direction[1]))
    magnitude = math.hypot(dx, dy)
    if magnitude <= 0.0:
        raise ValueError("writing direction must be non-zero")
    return (dx / magnitude, dy / magnitude)


def project_bbox_to_writing_frame(bbox: BBox, direction: Direction) -> BBox:
    """Project an axis-aligned page bbox into inline/block-flow coordinates."""

    dx, dy = _normalized_direction(direction)
    nx, ny = -dy, dx
    x0, y0, x1, y1 = (float(value) for value in bbox)
    corners = ((x0, y0), (x0, y1), (x1, y0), (x1, y1))
    inline = tuple(x * dx + y * dy for x, y in corners)
    block = tuple(x * nx + y * ny for x, y in corners)
    return (min(inline), min(block), max(inline), max(block))


def downstream_page_clip(
    bbox: BBox,
    direction: Direction,
    page_width: float,
    page_height: float,
) -> BBox:
    """Return the page rectangle at or after a cardinal writing-frame owner."""

    dx, dy = _normalized_direction(direction)
    x0, y0, x1, y1 = (float(value) for value in bbox)
    width, height = float(page_width), float(page_height)
    tolerance = 1e-9
    if abs(dx - 1.0) <= tolerance and abs(dy) <= tolerance:
        return (0.0, y0, width, height)
    if abs(dx + 1.0) <= tolerance and abs(dy) <= tolerance:
        return (0.0, 0.0, width, y1)
    if abs(dx) <= tolerance and abs(dy + 1.0) <= tolerance:
        return (x0, 0.0, width, height)
    if abs(dx) <= tolerance and abs(dy - 1.0) <= tolerance:
        return (0.0, 0.0, x1, height)
    raise ValueError("downstream page clip requires a cardinal writing direction")
