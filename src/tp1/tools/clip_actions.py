from __future__ import annotations

import pygame

from ..algorithms.clipping import cohen_sutherland_clip, liang_barsky_clip
from ..render.renderer import redraw_canvas_from_scene
from ..scene.models import Line, Point
from ..scene.scene import Scene
from ..state import AppState


def clip_lines(
    *,
    algo: str,  # "CS" or "LB"
    scene: Scene,
    state: AppState,
    canvas: pygame.Surface,
) -> tuple[int, int]:
    """
    Apply clipping to lines using the current state.clip.window.
    If some lines are selected, clip only those; otherwise clip all lines.
    Returns (kept, removed).
    """
    rect = state.clip.window
    if rect is None:
        state.status = "No clip window set"
        return (0, 0)

    selected = state.selection.selected_lines
    indices = list(range(len(scene.lines))) if not selected else sorted(selected)
    selected_set = set(indices)

    keep: list[Line] = []
    kept = 0
    removed = 0

    for i, ln in enumerate(scene.lines):
        if selected and i not in selected_set:
            keep.append(ln)
            continue

        if algo == "CS":
            res = cohen_sutherland_clip(ln.p0, ln.p1, rect)
        else:
            res = liang_barsky_clip(ln.p0, ln.p1, rect)

        if res is None:
            removed += 1
        else:
            p0, p1 = res
            keep.append(Line(Point(p0.x, p0.y), Point(p1.x, p1.y), ln.algo))
            kept += 1

    scene.lines = keep
    # After structural change, clear selection and redraw
    state.selection.selected_lines.clear()
    redraw_canvas_from_scene(canvas, scene)
    state.status = f"{algo}: kept {kept}, removed {removed}"
    return kept, removed
