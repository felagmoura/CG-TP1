from __future__ import annotations

from collections.abc import Iterable
from typing import TypeAlias

from .. import config as C

Point2: TypeAlias = tuple[int, int]
Rect4: TypeAlias = tuple[int, int, int, int]  # (left, top, width, height)


def rect_from_points(a: Point2, b: Point2) -> Rect4:
    """Create (left, top, width, height) from two corner points."""
    (x0, y0), (x1, y1) = a, b
    left = min(x0, x1)
    top = min(y0, y1)
    w = abs(x1 - x0)
    h = abs(y1 - y0)
    return (left, top, w, h)


def rect_edges(rect: Rect4) -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) for a Rect4."""
    left, top, w, h = rect
    right = left + w
    bottom = top + h
    return left, top, right, bottom


def rect_center(rect: Rect4) -> tuple[float, float]:
    """Center (cx, cy) of a Rect4."""
    left, top, w, h = rect
    return left + w / 2.0, top + h / 2.0


def rect_contains_point(rect: Rect4, pt: Point2) -> bool:
    """Inclusive containment test (left/top/right/bottom included)."""
    x, y = pt
    left, top, right, bottom = rect_edges(rect)
    return left <= x <= right and top <= y <= bottom


def bbox_of_points(points: Iterable[Point2]) -> Rect4 | None:
    """
    Bounding box of an iterable of points.
    Returns None for an empty iterable.
    """
    xs: list[int] = []
    ys: list[int] = []
    for x, y in points:
        xs.append(x)
        ys.append(y)
    if not xs or not ys:
        return None
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    return (left, top, right - left, bottom - top)


def bbox_union(rects: Iterable[Rect4]) -> Rect4 | None:
    """
    Union (minimal covering rect) of an iterable of Rect4.
    Returns None for an empty iterable.
    """
    first = True
    L = T = R = B = 0
    for l, t, w, h in rects:  # noqa: E741
        r = l + w
        b = t + h
        if first:
            L, T, R, B = l, t, r, b
            first = False
        else:
            L = min(L, l)
            T = min(T, t)
            R = max(R, r)
            B = max(B, b)
    if first:
        return None
    return (L, T, R - L, B - T)

def bbox_handles(rect: Rect4, rot_offset: int) -> dict[str, Point2]:
    """
    Return centers of the 8 resize handles and the rotation handle for a bbox.

    Keys:
        "nw","n","ne","e","se","s","sw","w"  (corners + edges)
        "rot"                                (rotation knob above top-middle)

    The positions are integer pixel centers.
    """
    l, t, w, h = rect
    r = l + w
    b = t + h
    cx = l + w / 2.0
    cy = t + h / 2.0

    # Edge/Corner handle centers (ints)
    pos: dict[str, Point2] = {
        "nw": (int(l), int(t)),
        "n": (int(cx), int(t)),
        "ne": (int(r), int(t)),
        "e": (int(r), int(cy)),
        "se": (int(r), int(b)),
        "s": (int(cx), int(b)),
        "sw": (int(l), int(b)),
        "w": (int(l), int(cy)),
    }

    # Rotation handle (circle) above top-mid
    raw_rot_y = int(t) - int(rot_offset)
    rot_y = max(C.ROT_HANDLE_TOP_MARGIN, raw_rot_y)  # <-- clamp
    rot = (int(cx), rot_y)
    pos["rot"] = rot

    return pos