from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pygame

from .. import config as C


@dataclass
class Button:
    """Simple clickable button used in the left sidebar."""
    rect: pygame.Rect
    label: str
    on_click: Callable[[], None] | None = None
    enabled: bool = True

    # runtime fields
    _hover: bool = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font) -> None:
        color = C.UI_BTN_HOVER if self._hover and self.enabled else C.UI_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, C.UI_STROKE, self.rect, width=1, border_radius=8)

        txt_color = C.WHITE if self.enabled else (180, 180, 180)
        txt = font.render(self.label, True, txt_color)
        surf.blit(
            txt,
            (self.rect.x + 10, self.rect.y + (self.rect.h - txt.get_height()) // 2),
        )

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.MOUSEMOTION and hasattr(ev, "pos"):
            self._hover = self.rect.collidepoint(ev.pos)
        elif (
            ev.type == pygame.MOUSEBUTTONDOWN
            and ev.button == 1
            and hasattr(ev, "pos")
            and self.enabled
            and self.rect.collidepoint(ev.pos)
        ):
            if self.on_click is not None:
                self.on_click()

    def set_enabled(self, value: bool) -> None:
        self.enabled = bool(value)
        if not self.enabled:
            self._hover = False
