from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

import pygame

from .. import config as C
from ..scene.scene import Scene
from ..state import AppState, Mode
from ..ui.sidebar import Sidebar


class Tool(Protocol):
    """
    Contract for canvas tools (to be implemented under tp1.tools.*).
    A tool may ignore events it doesn't care about.
    """

    def enter(self, state: AppState, scene: Scene) -> None: ...
    def exit(self, state: AppState, scene: Scene) -> None: ...

    def handle_canvas_event(
        self,
        ev: pygame.event.Event,
        cpos: tuple[int, int] | None,
        *,
        state: AppState,
        scene: Scene,
        canvas: pygame.Surface,
    ) -> None: ...


@dataclass
class EventDispatcher:
    """
    Routes pygame events to the sidebar (UI) or the active canvas tool based on x-position.
    Keeps track of the active tool by AppState.mode, calling enter/exit on changes.
    """
    state: AppState
    scene: Scene
    sidebar: Sidebar
    canvas: pygame.Surface

    # tool registry: Mode -> Tool instance
    _tools: dict[Mode, Tool] = field(default_factory=dict)

    # cache last mode to emit enter/exit when it changes
    _last_mode: Mode = field(default=Mode.IDLE)

    def register_tools(self, tools: Mapping[Mode, Tool]) -> None:
        self._tools.update(tools)

    @staticmethod
    def to_canvas_pos(ev: pygame.event.Event) -> tuple[int, int] | None:
        if not hasattr(ev, "pos"):
            return None
        x, y = ev.pos
        if x < C.UI_W:
            return None
        return x - C.UI_W, y

    def _maybe_switch_tool(self) -> None:
        if self.state.mode is self._last_mode:
            return
        # exit old tool
        old_tool = self._tools.get(self._last_mode)
        if old_tool is not None:
            try:
                old_tool.exit(self.state, self.scene)
            except Exception:
                pass
        # enter new tool
        new_tool = self._tools.get(self.state.mode)
        if new_tool is not None:
            try:
                new_tool.enter(self.state, self.scene)
            except Exception:
                pass
        self._last_mode = self.state.mode

    def handle(self, ev: pygame.event.Event) -> None:
        """
        Split events between the sidebar region and canvas region.
        Sidebar always gets events in [0, UI_W). Canvas tools get others.
        """
        self._maybe_switch_tool()

        if hasattr(ev, "pos"):
            x, _y = ev.pos
            if x < C.UI_W:
                # Sidebar UI
                self.sidebar.handle_event(ev)
                return

        # Canvas tool
        tool = self._tools.get(self.state.mode)
        if tool is None:
            return
        cpos = self.to_canvas_pos(ev)
        tool.handle_canvas_event(ev, cpos, state=self.state, scene=self.scene, canvas=self.canvas)
