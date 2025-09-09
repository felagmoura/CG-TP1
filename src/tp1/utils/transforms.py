from __future__ import annotations

import math
from typing import TypeAlias

Point2f: TypeAlias = tuple[float, float]
Point2i: TypeAlias = tuple[int, int]


def rotate_point_f(px: float, py: float, cx: float, cy: float, theta: float) -> Point2f:
    """
    Rotate (px, py) around (cx, cy) by angle theta (radians).
    Returns float coordinates (no rounding).
    """
    ct = math.cos(theta)
    st = math.sin(theta)
    x = cx + ct * (px - cx) - st * (py - cy)
    y = cy + st * (px - cx) + ct * (py - cy)
    return (x, y)


def rotate_point_i(px: int, py: int, cx: float, cy: float, theta: float) -> Point2i:
    """
    Integer-rounded rotation helper for raster coordinates.
    """
    x, y = rotate_point_f(float(px), float(py), cx, cy, theta)
    return (int(round(x)), int(round(y)))


def scale_point_f(px: float, py: float, cx: float, cy: float, s: float) -> Point2f:
    """
    Uniformly scale point (px, py) about (cx, cy) by factor s. Returns float coords.
    """
    x = cx + s * (px - cx)
    y = cy + s * (py - cy)
    return (x, y)


def scale_point_i(px: int, py: int, cx: float, cy: float, s: float) -> Point2i:
    """
    Integer-rounded uniform scaling helper for raster coordinates.
    """
    x, y = scale_point_f(float(px), float(py), cx, cy, s)
    return (int(round(x)), int(round(y)))

def scale_point_xy_f(
    px: float, py: float, cx: float, cy: float, sx: float, sy: float
) -> Point2f:
    """
    Scale point (px, py) about pivot (cx, cy) with independent factors sx, sy.
    Returns floats (no rounding).
    """
    x = cx + sx * (px - cx)
    y = cy + sy * (py - cy)
    return (x, y)


def scale_point_xy_i(
    px: int, py: int, cx: float, cy: float, sx: float, sy: float
) -> Point2i:
    """
    Integer-rounded anisotropic scale helper for raster coordinates.
    """
    x, y = scale_point_xy_f(float(px), float(py), cx, cy, sx, sy)
    return (int(round(x)), int(round(y)))

def distance(x0: float, y0: float, x1: float, y1: float) -> float:
    """Euclidean distance between two points (floats)."""
    return math.hypot(x1 - x0, y1 - y0)


def angle_from_center(cx: float, cy: float, x: float, y: float) -> float:
    """
    Angle (radians) of vector (x - cx, y - cy) using atan2.
    """
    return math.atan2(y - cy, x - cx)
