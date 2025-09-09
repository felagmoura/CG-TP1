from __future__ import annotations

import pygame

from .. import config as C
from ..scene.scene import Scene
from ..state import AppState


def clear_canvas(canvas: pygame.Surface) -> None:
    canvas.fill(C.CANVAS_BG)


def redraw_canvas_from_scene(
    canvas: pygame.Surface, 
    scene: Scene,
    state: AppState | None = None
    ) -> None:
    
    from ..algorithms.circles import draw_circle_bresenham
    from ..algorithms.clipping import cohen_sutherland_clip, liang_barsky_clip
    from ..algorithms.lines import draw_line_bresenham, draw_line_dda


    canvas.fill(C.CANVAS_BG)

    clip_rect = None
    clip_algo = None
    if state and state.clip.window and state.clip.preview_algo:
        l, t, w, h = state.clip.window
        clip_rect = pygame.Rect(l, t, w, h)
        clip_algo = state.clip.preview_algo

    for ln in scene.lines:
        p0, p1 = ln.p0, ln.p1
        if clip_rect and clip_algo:
            if clip_algo == "CS":
                res = cohen_sutherland_clip(p0, p1, clip_rect)
            else:
                res = liang_barsky_clip(p0, p1, clip_rect)
            if res is None:
                continue
            p0, p1 = res
        if ln.algo == "DDA":
            draw_line_dda(canvas, p0, p1, C.BLACK)
        else:
            draw_line_bresenham(canvas, p0, p1, C.BLACK)

    for c in scene.circles:
        draw_circle_bresenham(canvas, c.c, c.r, C.BLACK)