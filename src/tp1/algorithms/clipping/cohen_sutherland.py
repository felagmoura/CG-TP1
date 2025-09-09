from __future__ import annotations

from ...scene.models import Point
from ...scene.models import Rect4 as _Rect4  # (left, top, width, height)

# Region codes
INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8


def _edges(rect: _Rect4) -> tuple[int, int, int, int]:
    left, top, w, h = rect
    right = left + w
    bottom = top + h
    return left, top, right, bottom


def _code(x: int, y: int, rect: _Rect4) -> int:
    left, top, right, bottom = _edges(rect)
    code = INSIDE
    if x < left:
        code |= LEFT
    elif x > right:
        code |= RIGHT
    if y < top:
        code |= TOP
    elif y > bottom:
        code |= BOTTOM
    return code


def cohen_sutherland_clip(
    p0: Point, p1: Point, rect: _Rect4
) -> tuple[Point, Point] | None:
    """
    Clip a segment against axis-aligned rect using Cohen–Sutherland.
    Returns new endpoints or None if fully outside.
    """
    x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
    code0 = _code(x0, y0, rect)
    code1 = _code(x1, y1, rect)
    left, top, right, bottom = _edges(rect)

    while True:
        if not (code0 | code1):  # both inside
            return Point(x0, y0), Point(x1, y1)
        if code0 & code1:  # trivially reject
            return None

        code_out = code0 or code1
        if code_out & TOP:
            x = x0 + (x1 - x0) * (top - y0) / (y1 - y0) if y1 != y0 else x0
            y = top
        elif code_out & BOTTOM:
            x = x0 + (x1 - x0) * (bottom - y0) / (y1 - y0) if y1 != y0 else x0
            y = bottom
        elif code_out & RIGHT:
            y = y0 + (y1 - y0) * (right - x0) / (x1 - x0) if x1 != x0 else y0
            x = right
        else:  # LEFT
            y = y0 + (y1 - y0) * (left - x0) / (x1 - x0) if x1 != x0 else y0
            x = left

        if code_out == code0:
            x0, y0 = int(round(x)), int(round(y))
            code0 = _code(x0, y0, rect)
        else:
            x1, y1 = int(round(x)), int(round(y))
            code1 = _code(x1, y1, rect)
