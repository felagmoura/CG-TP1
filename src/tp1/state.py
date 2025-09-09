from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TypeAlias

Point2: TypeAlias = tuple[int, int]
Rect4: TypeAlias = tuple[int, int, int, int]  # (left, top, width, height)


class Mode(Enum):
    """All interactive modes/tools in the app."""
    IDLE = auto()
    SELECT = auto()
    TRANSLATE = auto()
    ROTATE = auto()
    SCALE_UNIFORM = auto()
    LINE_DDA = auto()
    LINE_BRESENHAM = auto()
    CIRCLE_BRESENHAM = auto()
    CLIP_WINDOW = auto()


@dataclass
class SelectionState:
    selecting: bool = False
    anchor: Point2 | None = None
    current: Point2 | None = None
    selected_lines: set[int] = field(default_factory=set)
    selected_circles: set[int] = field(default_factory=set)

    def reset(self) -> None:
        self.selecting = False
        self.anchor = None
        self.current = None
        self.selected_lines.clear()
        self.selected_circles.clear()


@dataclass
class TransformState:
    dragging: bool = False
    anchor: Point2 | None = None

    # Snapshots for non-destructive drags
    lines_snapshot: list[tuple[int, tuple[int, int, int, int]]] = field(default_factory=list)
    # circles: (idx, (cx, cy, r))
    circles_snapshot: list[tuple[int, tuple[int, int, int]]] = field(default_factory=list)

    # Pivot (for rotate/scale) and baseline magnitudes
    pivot: tuple[float, float] | None = None
    anchor_angle: float = 0.0
    anchor_dist: float = 1.0

    def reset(self) -> None:
        self.dragging = False
        self.anchor = None
        self.lines_snapshot.clear()
        self.circles_snapshot.clear()
        self.pivot = None
        self.anchor_angle = 0.0
        self.anchor_dist = 1.0


@dataclass
class ClipState:
    """User-defined clipping window via drag."""
    setting: bool = False
    anchor: Point2 | None = None
    current: Point2 | None = None
    window: Rect4 | None = None

    def reset(self) -> None:
        self.setting = False
        self.anchor = None
        self.current = None
        self.window = None


@dataclass
class AppState:
    """Top-level state container owned by the app loop."""
    mode: Mode = Mode.IDLE
    selection: SelectionState = field(default_factory=SelectionState)
    transform: TransformState = field(default_factory=TransformState)
    clip: ClipState = field(default_factory=ClipState)

    # Drawing pending states (for two-click tools)
    pending_line_start: Point2 | None = None
    pending_circle_center: Point2 | None = None

    # Basic HUD/status message (optional)
    status: str = ""

    def reset_all(self) -> None:
        """Reset selection/transform/clip and pending clicks; keep mode."""
        self.selection.reset()
        self.transform.reset()
        self.clip.reset()
        self.pending_line_start = None
        self.pending_circle_center = None
        self.status = ""


def make_initial_state() -> AppState:
    """Factory to create a fresh default AppState."""
    return AppState()
