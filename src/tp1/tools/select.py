from __future__ import annotations

import pygame

from ..scene.scene import Scene
from ..state import AppState
from ..utils.geom import rect_from_points


class SelectTool:
    """
    Drag a rectangle to select shapes.
    Lines are selected if either endpoint is inside; circles if center is inside.
    """

    def enter(self, state: AppState, scene: Scene) -> None:
        # keep existing selection; no reset unless you prefer fresh selection on enter
        state.status = "Drag to select"

    def exit(self, state: AppState, scene: Scene) -> None:
        state.selection.selecting = False
        state.selection.anchor = None
        state.selection.current = None
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
        sel = state.selection

        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
            sel.selecting = True
            sel.anchor = cpos
            sel.current = cpos

        elif ev.type == pygame.MOUSEMOTION and cpos and sel.selecting:
            sel.current = cpos

        elif ev.type == pygame.MOUSEBUTTONUP and cpos and sel.selecting:
            sel.selecting = False
            a, b = sel.anchor, sel.current
            if not a or not b:
                return
            l, t, w, h = rect_from_points(a, b)

            # rebuild selection sets
            sel.selected_lines.clear()
            sel.selected_circles.clear()

            L, T, R, B = l, t, l + w, t + h

            # Lines: select if any endpoint is inside
            for i, ln in enumerate(scene.lines):
                if (L <= ln.p0.x <= R and T <= ln.p0.y <= B) or (
                    L <= ln.p1.x <= R and T <= ln.p1.y <= B
                ):
                    sel.selected_lines.add(i)

            # Circles: select if center is inside
            for i, c in enumerate(scene.circles):
                if L <= c.c.x <= R and T <= c.c.y <= B:
                    sel.selected_circles.add(i)

            state.status = f"Selected {len(sel.selected_lines)} lines, {len(sel.selected_circles)} circles"
