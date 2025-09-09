from __future__ import annotations

import pygame

from ..render.renderer import redraw_canvas_from_scene
from ..scene.scene import Scene
from ..state import AppState


class TranslateTool:
    """Click-drag to translate the current selection (snapshot-based, no drift)."""

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Drag selection to move"

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
            tr.dragging = True
            tr.anchor = cpos
            tr.lines_snapshot = [
                (i, (scene.lines[i].p0.x, scene.lines[i].p0.y, scene.lines[i].p1.x, scene.lines[i].p1.y))
                for i in sel.selected_lines
            ]
            tr.circles_snapshot = [
                (i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
                for i in sel.selected_circles
            ]

        elif ev.type == pygame.MOUSEMOTION and cpos and tr.dragging and tr.anchor:
            dx = cpos[0] - tr.anchor[0]
            dy = cpos[1] - tr.anchor[1]
            for i, (x0, y0, x1, y1) in tr.lines_snapshot:
                scene.lines[i].p0.x = x0 + dx
                scene.lines[i].p0.y = y0 + dy
                scene.lines[i].p1.x = x1 + dx
                scene.lines[i].p1.y = y1 + dy
            for i, (cx0, cy0, r0) in tr.circles_snapshot:
                scene.circles[i].c.x = cx0 + dx
                scene.circles[i].c.y = cy0 + dy
                scene.circles[i].r = r0
            redraw_canvas_from_scene(canvas, scene)

        elif ev.type == pygame.MOUSEBUTTONUP and tr.dragging:
            self.exit(state, scene)  # resets transform + status
            redraw_canvas_from_scene(canvas, scene)
