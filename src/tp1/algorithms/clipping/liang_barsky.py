from __future__ import annotations

from ...scene.models import Point
from ...scene.models import Rect4 as _Rect4  # (left, top, width, height)


def _edges(rect: _Rect4) -> tuple[int, int, int, int]:
    left, top, w, h = rect
    right = left + w
    bottom = top + h
    return left, top, right, bottom


def liang_barsky_clip(
    p0: Point, p1: Point, rect: _Rect4
) -> tuple[Point, Point] | None:
    """
    Clip a segment against axis-aligned rect using Liang–Barsky (parametric).
    Returns new endpoints or None if fully outside.
    """
    x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
    dx = x1 - x0
    dy = y1 - y0

    x_min, y_min, x_max, y_max = None, None, None, None
    left, top, right, bottom = _edges(rect)
    x_min, x_max = left, right
    y_min, y_max = top, bottom

    # p[i] * u <= q[i]
    p = [-dx, dx, -dy, dy]
    q = [x0 - x_min, x_max - x0, y0 - y_min, y_max - y0]

    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q, strict=False):
        if pi == 0:
            if qi < 0:
                return None 
            continue
        r = qi / pi
        if pi < 0:
            if r > u1:
                return None
            if r > u0:
                u0 = r
        else:
            if r < u0:
                return None
            if r < u1:
                u1 = r

    nx0 = int(round(x0 + u0 * dx))
    ny0 = int(round(y0 + u0 * dy))
    nx1 = int(round(x0 + u1 * dx))
    ny1 = int(round(y0 + u1 * dy))
    return Point(nx0, ny0), Point(nx1, ny1)
