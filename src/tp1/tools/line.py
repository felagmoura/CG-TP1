from __future__ import annotations

import pygame

from .. import config as C
from ..algorithms.lines import draw_line_bresenham, draw_line_dda
from ..render.raster import put_pixel
from ..scene.models import Line, Point
from ..scene.scene import Scene
from ..state import AppState


class LineTool:
    """
    Two-click line tool; parametric on algorithm ("DDA" or "BRESENHAM").
    First click sets start; second click commits and draws the line to the canvas/scene.
    """

    def __init__(self, algo: str) -> None:
        if algo not in ("DDA", "BRESENHAM"):
            raise ValueError("LineTool algo must be 'DDA' or 'BRESENHAM'")
        self.algo = algo

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = f"Line ({self.algo}): click start, then end"

    def exit(self, state: AppState, scene: Scene) -> None:
        state.pending_line_start = None
        state.status = ""

    def handle_canvas_event(
        self,
        ev: pygame.event.Event,
        cpos: tuple[int, int] | None,
        *,
        state: AppState,
        scene: Scene,
        canvas: pygame.Surface,
    ) -> None:
        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
            x, y = cpos
            if state.pending_line_start is None:
                state.pending_line_start = (x, y)
                put_pixel(canvas, x, y, C.ACCENT)
            else:
                x0, y0 = state.pending_line_start
                p0 = Point(x0, y0)
                p1 = Point(x, y)
                scene.add_line(Line(p0, p1, self.algo))
                if self.algo == "DDA":
                    draw_line_dda(canvas, p0, p1, C.BLACK)
                else:
                    draw_line_bresenham(canvas, p0, p1, C.BLACK)
                state.pending_line_start = None
