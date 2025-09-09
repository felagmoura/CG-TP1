from __future__ import annotations

import pygame

from ..render.raster import put_pixel
from ..scene.models import Point


def draw_line_dda(
    surf: pygame.Surface,
    p0: Point,
    p1: Point,
    color: tuple[int, int, int],
) -> None:
    x0, y0 = p0.x, p0.y
    x1, y1 = p1.x, p1.y
    dx, dy = x1 - x0, y1 - y0
    steps = int(max(abs(dx), abs(dy)))
    if steps == 0:
        put_pixel(surf, x0, y0, color)
        return
    x_inc = dx / steps
    y_inc = dy / steps
    x, y = x0, y0
    for _ in range(steps + 1):
        put_pixel(surf, round(x), round(y), color)
        x += x_inc
        y += y_inc


def draw_line_bresenham(
    surf: pygame.Surface,
    p0: Point,
    p1: Point,
    color: tuple[int, int, int],
) -> None:
    x0, y0 = p0.x, p0.y
    x1, y1 = p1.x, p1.y
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        put_pixel(surf, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
