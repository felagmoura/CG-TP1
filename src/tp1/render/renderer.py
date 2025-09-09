from __future__ import annotations

import pygame

from .. import config as C
from ..scene.scene import Scene


def clear_canvas(canvas: pygame.Surface) -> None:
    canvas.fill(C.CANVAS_BG)


def redraw_canvas_from_scene(canvas: pygame.Surface, scene: Scene) -> None:
    """
    Full re-rasterization of the scene onto the canvas surface.
    Keeps algorithm imports local to avoid circular import issues.
    """
    clear_canvas(canvas)

    from ..algorithms.circles import draw_circle_bresenham
    from ..algorithms.lines import draw_line_bresenham, draw_line_dda

    for ln in scene.lines:
        if ln.algo == "DDA":
            draw_line_dda(canvas, ln.p0, ln.p1, C.BLACK)
        else:
            draw_line_bresenham(canvas, ln.p0, ln.p1, C.BLACK)

    for c in scene.circles:
        draw_circle_bresenham(canvas, c.c, c.r, C.BLACK)
