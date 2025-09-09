from __future__ import annotations

import math
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

def move_rect(rect: Rect4, dx: int, dy: int) -> Rect4:
    """Translate a rect by (dx, dy) without clamping."""
    l, t, w, h = rect
    return (l + dx, t + dy, w, h)

def clamp_rect_to_canvas(rect: Rect4, width: int, height: int) -> Rect4:
    """
    Clamp rect to [0..width]×[0..height].
    If rect is larger than the canvas, it will be reduced to fit.
    """
    l, t, w, h = rect
    w = min(max(0, w), width)
    h = min(max(0, h), height)
    l = max(0, min(l, width - w))
    t = max(0, min(t, height - h))
    return (int(l), int(t), int(w), int(h))

def _opposite_corner_for(handle: str, l0: int, t0: int, r0: int, b0: int) -> tuple[float, float]:
    """Return the pivot corner (opposite to the dragged corner)."""
    if handle == "se":  # pivot NW
        return float(l0), float(t0)
    if handle == "ne":  # pivot SW
        return float(l0), float(b0)
    if handle == "sw":  # pivot NE
        return float(r0), float(t0)
    if handle == "nw":  # pivot SE
        return float(r0), float(b0)
    # default (won't be used for edges)
    return float(l0), float(t0)

def _normalize_edges(l: float, t: float, r: float, b: float) -> tuple[int, int, int, int]:
    """Ensure l<=r and t<=b; return ints."""
    if r < l:
        l, r = r, l
    if b < t:
        t, b = b, t
    return int(round(l)), int(round(t)), int(round(r)), int(round(b))

def resize_rect_from_handle(
    rect0: tuple[int, int, int, int],
    handle: str,
    mouse: tuple[int, int],
    *,
    keep_aspect: bool = False,
    from_center: bool = False,
    min_w: int = 8,
    min_h: int = 8,
    bounds: tuple[int, int] | None = None,
) -> tuple[int, int, int, int]:
    """
    Compute a new rect by 'dragging' a handle on rect0 toward mouse.
    - rect0: (l,t,w,h)
    - handle: one of "nw","n","ne","e","se","s","sw","w"
    - mouse: current canvas-space cursor (mx,my)
    - keep_aspect: if True, corners keep original aspect ratio (edges ignore)
    - from_center: if True, resize symmetrically around rect center
    - min_w/min_h: minimum resulting size
    - bounds: (canvas_w, canvas_h) for clamping; if None, no clamp
    Returns a normalized (l,t,w,h).
    """
    l0, t0, w0, h0 = rect0
    r0 = l0 + w0
    b0 = t0 + h0
    mx, my = mouse
    cx = (l0 + r0) / 2.0
    cy = (t0 + b0) / 2.0
    aspect = (w0 / h0) if h0 != 0 else 1.0

    l, t, r, b = float(l0), float(t0), float(r0), float(b0)

    # --- Corner handles ---
    if handle in ("nw", "ne", "se", "sw"):
        if from_center:
            # Pivot at center; compute half-width/height from mouse
            vx = mx - cx
            vy = my - cy
            # Aspect lock (corners only)
            if keep_aspect and h0 != 0:
                if abs(vx) / aspect >= abs(vy):
                    vy = math.copysign(abs(vx) / aspect, vy if vy != 0 else 1.0)
                else:
                    vx = math.copysign(abs(vy) * aspect, vx if vx != 0 else 1.0)
            # Enforce min size (half-dimensions when resizing from center)
            half_w = max(min_w / 2.0, abs(vx))
            half_h = max(min_h / 2.0, abs(vy))
            l = cx - half_w
            r = cx + half_w
            t = cy - half_h
            b = cy + half_h
        else:
            # Pivot at opposite corner
            px, py = _opposite_corner_for(handle, l0, t0, r0, b0)
            vx = mx - px
            vy = my - py
            # Aspect lock (corners only)
            if keep_aspect and h0 != 0:
                if abs(vx) / aspect >= abs(vy):
                    vy = math.copysign(abs(vx) / aspect, vy if vy != 0 else 1.0)
                else:
                    vx = math.copysign(abs(vy) * aspect, vx if vx != 0 else 1.0)
            # Enforce mins relative to pivot (full size)
            if abs(vx) < min_w:
                vx = math.copysign(min_w, vx if vx != 0 else 1.0)
            if abs(vy) < min_h:
                vy = math.copysign(min_h, vy if vy != 0 else 1.0)
            # Build from pivot and vector
            l = min(px, px + vx)
            r = max(px, px + vx)
            t = min(py, py + vy)
            b = max(py, py + vy)

    # --- Edge handles (1D) ---
    elif handle in ("e", "w"):
        if from_center:
            half_w = max(min_w / 2.0, abs(mx - cx))
            l = cx - half_w
            r = cx + half_w
        else:
            if handle == "e":
                l = l0
                r = mx
                # min width enforced keeping left fixed
                if (r - l) < min_w:
                    r = l + min_w
            else:  # "w"
                r = r0
                l = mx
                if (r - l) < min_w:
                    l = r - min_w
        # y-edges stay as original
        t, b = float(t0), float(b0)

    elif handle in ("n", "s"):
        if from_center:
            half_h = max(min_h / 2.0, abs(my - cy))
            t = cy - half_h
            b = cy + half_h
        else:
            if handle == "s":
                t = t0
                b = my
                if (b - t) < min_h:
                    b = t + min_h
            else:  # "n"
                b = b0
                t = my
                if (b - t) < min_h:
                    t = b - min_h
        # x-edges stay as original
        l, r = float(l0), float(r0)

    # Normalize to ints
    L, T, R, B = _normalize_edges(l, t, r, b)
    # Clamp to canvas
    if bounds:
        from .geom import clamp_rect_to_canvas  # local import to avoid cycles
        L, T, W, H = clamp_rect_to_canvas((L, T, R - L, B - T), bounds[0], bounds[1])
        return (L, T, W, H)
    return (L, T, R - L, B - T)