from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
import pygame

from .scene import Scene
from .models import Line, Point
from ..algorithms.clipping import cohen_sutherland_clip, liang_barsky_clip


def apply_clipping_to_lines(
    scene: Scene,
    rect: pygame.Rect,
    algo: str,                              # "CS" | "LB"
    selected: set[int] | None = None,       # None -> all lines
) -> tuple[int, int]:
    """
    Destructively clip lines in the scene to `rect` using `algo`.
    If `selected` is provided, only those line indices are affected; others pass through unchanged.

    Returns: (kept, removed) counts over the affected set.
    """
    affected: set[int] | None = None if not selected else set(selected)
    kept = 0
    removed = 0
    new_lines: list[Line] = []

    for i, ln in enumerate(scene.lines):
        # If selection is active and this line isn't selected, keep as-is
        if affected is not None and i not in affected:
            new_lines.append(ln)
            continue

        # Clip the line
        if algo == "CS":
            res = cohen_sutherland_clip(ln.p0, ln.p1, rect)
        else:
            res = liang_barsky_clip(ln.p0, ln.p1, rect)

        if res is None:
            removed += 1
            # drop the line
        else:
            p0, p1 = res
            new_lines.append(Line(Point(p0.x, p0.y), Point(p1.x, p1.y), ln.algo))
            kept += 1

    scene.lines = new_lines
    return kept, removed
