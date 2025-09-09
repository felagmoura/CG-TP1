from __future__ import annotations

import pygame

from ..scene.scene import Scene
from ..state import AppState
from ..utils.geom import rect_from_points


class ClipWindowTool:
    """Drag to define the clipping window stored in state.clip.window."""

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Drag to set clip window"

    def exit(self, state: AppState, scene: Scene) -> None:
        state.clip.setting = False
        state.clip.anchor = None
        state.clip.current = None
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
        clip = state.clip
        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
            clip.setting = True
            clip.anchor = cpos
            clip.current = cpos
        elif ev.type == pygame.MOUSEMOTION and cpos and clip.setting:
            clip.current = cpos
        elif ev.type == pygame.MOUSEBUTTONUP and cpos and clip.setting:
            clip.setting = False
            a, b = clip.anchor, clip.current
            if a and b:
                clip.window = rect_from_points(a, b)
