from __future__ import annotations

import math

import pygame

from .. import config as C
from ..algorithms.circles import draw_circle_bresenham
from ..render.raster import put_pixel
from ..scene.models import Circle, Point
from ..scene.scene import Scene
from ..state import AppState


class CircleTool:
    """Two-click circle tool using Bresenham."""

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Circle (Bresenham): click center, then radius"

    def exit(self, state: AppState, scene: Scene) -> None:
        state.pending_circle_center = None
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
            if state.pending_circle_center is None:
                state.pending_circle_center = (x, y)
                put_pixel(canvas, x, y, C.ACCENT)
            else:
                cx, cy = state.pending_circle_center
                r = max(0, int(round(math.hypot(x - cx, y - cy))))
                center = Point(cx, cy)
                scene.add_circle(Circle(center, r, "BRESENHAM"))
                draw_circle_bresenham(canvas, center, r, C.BLACK)
                state.pending_circle_center = None
