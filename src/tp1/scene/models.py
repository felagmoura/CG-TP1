from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

LineAlgo: TypeAlias = Literal["DDA", "BRESENHAM"]
CircleAlgo: TypeAlias = Literal["BRESENHAM"]
Rect4: TypeAlias = tuple[int, int, int, int]  # (left, top, width, height)


@dataclass
class Point:
    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        return self.x, self.y

    def move_ip(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy


@dataclass
class Line:
    p0: Point
    p1: Point
    algo: LineAlgo

    def bbox(self) -> Rect4:
        left = min(self.p0.x, self.p1.x)
        top = min(self.p0.y, self.p1.y)
        width = abs(self.p1.x - self.p0.x)
        height = abs(self.p1.y - self.p0.y)
        return left, top, width, height

    def move_ip(self, dx: int, dy: int) -> None:
        self.p0.move_ip(dx, dy)
        self.p1.move_ip(dx, dy)


@dataclass
class Circle:
    c: Point
    r: int
    algo: CircleAlgo = "BRESENHAM"

    def __post_init__(self) -> None:
        if self.r < 0:
            self.r = 0

    def bbox(self) -> Rect4:
        left = self.c.x - self.r
        top = self.c.y - self.r
        size = 2 * self.r
        return left, top, size, size

    def move_ip(self, dx: int, dy: int) -> None:
        self.c.move_ip(dx, dy)
