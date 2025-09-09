from __future__ import annotations

import pygame


def put_pixel(surf: pygame.Surface, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)
