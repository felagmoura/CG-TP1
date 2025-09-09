from __future__ import annotations

import pygame

from ..scene.scene import Scene
from ..state import AppState


class ToolBase:
    """
    Minimal base class for canvas tools. Dispatcher uses the `Tool` Protocol,
    but inheriting from this gives you no-op enter/exit and a consistent signature.
    """

    def enter(self, state: AppState, scene: Scene) -> None:  # noqa: D401
        """Called when this tool becomes active."""
        return

    def exit(self, state: AppState, scene: Scene) -> None:  # noqa: D401
        """Called when this tool is deactivated."""
        return

    def handle_canvas_event(
        self,
        ev: pygame.event.Event,
        cpos: tuple[int, int] | None,
        *,
        state: AppState,
        scene: Scene,
        canvas: pygame.Surface,
    ) -> None:
        raise NotImplementedError
