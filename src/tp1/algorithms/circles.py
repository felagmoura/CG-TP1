from __future__ import annotations

import pygame

from ..render.raster import put_pixel
from ..scene.models import Point


def draw_circle_bresenham(
    surf: pygame.Surface,
    center: Point,
    r: int,
    color: tuple[int, int, int],
) -> None:
    if r <= 0:
        put_pixel(surf, center.x, center.y, color)
        return
    x = 0
    y = r
    d = 1 - r
    while x <= y:
        put_pixel(surf, center.x + x, center.y + y, color)
        put_pixel(surf, center.x + y, center.y + x, color)
        put_pixel(surf, center.x - x, center.y + y, color)
        put_pixel(surf, center.x - y, center.y + x, color)
        put_pixel(surf, center.x + x, center.y - y, color)
        put_pixel(surf, center.x + y, center.y - x, color)
        put_pixel(surf, center.x - x, center.y - y, color)
        put_pixel(surf, center.x - y, center.y - x, color)

        x += 1
        if d < 0:
            d += 2 * x + 1
        else:
            y -= 1
            d += 2 * (x - y) + 1
