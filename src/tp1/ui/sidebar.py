from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import pygame

from .. import config as C
from ..state import AppState


@dataclass
class Sidebar:
    """
    Vertical toolbar on the left. Owns button layout, drawing, and UI-event handling
    for the sidebar region (x in [0, UI_W)).
    """
    buttons: list = field(default_factory=list)

    # Layout cursor (y start for the next button)
    _cursor_y: int = C.BTN_PAD + 44  # leave space for title/mode area

    def add_button(self, label: str, on_click: Callable[[], None]) -> None:
        rect = pygame.Rect(
            C.BTN_PAD, self._cursor_y, C.UI_W - 2 * C.BTN_PAD, C.BTN_HEIGHT
        )
        from .button import Button  # local import to avoid cycles
        self.buttons.append(Button(rect=rect, label=label, on_click=on_click))
        self._cursor_y += C.BTN_HEIGHT + C.BTN_SPACING

    def add_buttons(self, entries: Iterable[tuple[str, Callable[[], None]]]) -> None:
        for label, cb in entries:
            self.add_button(label, cb)

    def reset_layout(self) -> None:
        self._cursor_y = C.BTN_PAD + 44
        # Reflow existing buttons
        for b in self.buttons:
            b.rect.update(C.BTN_PAD, self._cursor_y, C.UI_W - 2 * C.BTN_PAD, C.BTN_HEIGHT)
            self._cursor_y += C.BTN_HEIGHT + C.BTN_SPACING

    def handle_event(self, ev: pygame.event.Event) -> None:
        # Only process events that happen inside the sidebar area
        if hasattr(ev, "pos"):
            x, _y = ev.pos
            if x >= C.UI_W:
                return
        for b in self.buttons:
            b.handle_event(ev)

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font, state: AppState) -> None:  # noqa: E501
        # background
        surf.fill(C.UI_BG)

        # Title & mode
        title = font.render("TP1 - CG", True, C.WHITE)
        mode_txt = small.render(f"Mode: {state.mode.name}", True, (220, 220, 230))
        surf.blit(title, (C.BTN_PAD, C.BTN_PAD))
        surf.blit(mode_txt, (C.BTN_PAD, C.BTN_PAD + 22))

        # Optional status line
        if state.status:
            status_txt = small.render(state.status, True, (210, 210, 220))
            surf.blit(status_txt, (C.BTN_PAD, C.BTN_PAD + 22 + 18))

        # Buttons
        for b in self.buttons:
            b.draw(surf, small)

        # Selection info footer (simple counters)
        sel = state.selection
        info = f"Selected: {len(sel.selected_lines)} lines, {len(sel.selected_circles)} circles"
        surf.blit(small.render(info, True, (200, 210, 220)), (C.BTN_PAD, self._cursor_y + 16))
