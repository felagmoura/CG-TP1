from __future__ import annotations

from dataclasses import dataclass, field

from .models import Circle, Line


@dataclass
class Scene:
    lines: list[Line] = field(default_factory=list)
    circles: list[Circle] = field(default_factory=list)

    def clear(self) -> None:
        self.lines.clear()
        self.circles.clear()

    # Convenience adders return the index of the inserted item (useful for selection)
    def add_line(self, line: Line) -> int:
        self.lines.append(line)
        return len(self.lines) - 1

    def add_circle(self, circle: Circle) -> int:
        self.circles.append(circle)
        return len(self.circles) - 1

    def is_empty(self) -> bool:
        return not self.lines and not self.circles

    def __len__(self) -> int:
        """Total number of primitives."""
        return len(self.lines) + len(self.circles)
    