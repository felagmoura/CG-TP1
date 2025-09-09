from __future__ import annotations

import math

import pygame

from ..render.renderer import redraw_canvas_from_scene
from ..scene.scene import Scene
from ..state import AppState
from ..utils.geom import bbox_of_points
from ..utils.transforms import rotate_point_i


def _selection_bbox_center(scene: Scene, state: AppState) -> tuple[float, float] | None:
    pts: list[tuple[int, int]] = []
    for i in state.selection.selected_lines:
        if 0 <= i < len(scene.lines):
            ln = scene.lines[i]
            pts.append((ln.p0.x, ln.p0.y))
            pts.append((ln.p1.x, ln.p1.y))
    for i in state.selection.selected_circles:
        if 0 <= i < len(scene.circles):
            c = scene.circles[i]
            pts.append((c.c.x - c.r, c.c.y - c.r))
            pts.append((c.c.x + c.r, c.c.y + c.r))
    bb = bbox_of_points(pts)
    if not bb:
        return None
    l, t, w, h = bb
    return (l + w / 2.0, t + h / 2.0)


class RotateTool:
    """Rotate selection around its bounding-box center by dragging the mouse."""

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Drag around pivot to rotate"

    def exit(self, state: AppState, scene: Scene) -> None:
        state.transform.reset()
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
        tr = state.transform
        sel = state.selection

        if ev.type == pygame.MOUSEBUTTONDOWN and cpos and (sel.selected_lines or sel.selected_circles):
            pivot = _selection_bbox_center(scene, state)
            if not pivot:
                return
            tr.dragging = True
            tr.anchor = cpos
            tr.pivot = pivot
            ax, ay = cpos[0] - pivot[0], cpos[1] - pivot[1]
            tr.anchor_angle = math.atan2(ay, ax) if (ax or ay) else 0.0

            tr.lines_snapshot = [
                (i, (scene.lines[i].p0.x, scene.lines[i].p0.y, scene.lines[i].p1.x, scene.lines[i].p1.y))
                for i in sel.selected_lines
            ]
            tr.circles_snapshot = [
                (i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
                for i in sel.selected_circles
            ]

        elif ev.type == pygame.MOUSEMOTION and cpos and tr.dragging and tr.pivot:
            cx, cy = tr.pivot
            vx, vy = cpos[0] - cx, cpos[1] - cy
            cur_angle = math.atan2(vy, vx) if (vx or vy) else tr.anchor_angle
            theta = cur_angle - tr.anchor_angle

            for i, (x0, y0, x1, y1) in tr.lines_snapshot:
                nx0, ny0 = rotate_point_i(x0, y0, cx, cy, theta)
                nx1, ny1 = rotate_point_i(x1, y1, cx, cy, theta)
                scene.lines[i].p0.x, scene.lines[i].p0.y = nx0, ny0
                scene.lines[i].p1.x, scene.lines[i].p1.y = nx1, ny1

            for i, (cx0, cy0, r0) in tr.circles_snapshot:
                ncx, ncy = rotate_point_i(cx0, cy0, cx, cy, theta)
                scene.circles[i].c.x, scene.circles[i].c.y = ncx, ncy
                scene.circles[i].r = r0

            redraw_canvas_from_scene(canvas, scene)

        elif ev.type == pygame.MOUSEBUTTONUP and tr.dragging:
            self.exit(state, scene)
            redraw_canvas_from_scene(canvas, scene)
