from __future__ import annotations

from typing import TypeAlias

# --- Window / layout ---
WIDTH: int = 1000
HEIGHT: int = 650
UI_W: int = 220

CANVAS_W: int = WIDTH - UI_W
CANVAS_H: int = HEIGHT

FPS: int = 60

# --- Colors (RGB / RGBA tuples) ---
Color: TypeAlias = tuple[int, int, int]
ColorA: TypeAlias = tuple[int, int, int, int]

BG: Color = (30, 30, 35)
UI_BG: Color = (40, 40, 48)
UI_BTN: Color = (60, 60, 68)
UI_BTN_HOVER: Color = (72, 72, 84)
UI_STROKE: Color = (90, 90, 100)
CANVAS_BG: Color = (245, 245, 245)
WHITE: Color = (255, 255, 255)
BLACK: Color = (0, 0, 0)

ACCENT: Color = (0, 120, 255)
ACCENT_FILL: ColorA = (0, 120, 255, 40)
ACCENT_BORDER: ColorA = (0, 120, 255, 200)

CLIP_COLOR: ColorA = (60, 200, 120, 200)
CLIP_FILL: ColorA = (60, 200, 120, 40)

# --- UI / Typography ---
FONT_FAMILY_MAIN: str = "consolas"
FONT_SIZE_MAIN: int = 18
FONT_SIZE_SMALL: int = 16

# --- Button layout ---
BTN_HEIGHT: int = 44
BTN_PAD: int = 12
BTN_SPACING: int = 10

# --- Transform handles ---
HANDLE_SIZE: int = 10           # square handle width/height in px
HANDLE_HIT_PAD: int = 4         # extra radius for hit-testing 
ROT_HANDLE_OFFSET: int = 26     # distance above bbox top-middle
SNAP_ANGLE_DEG: int = 15        # rotation snapping increment
ROT_HANDLE_TOP_MARGIN: int = 8     # don’t draw knob above this Y
ROT_STEM_HIT_RADIUS: int = 6       # clickable thickness around the stem


# BBox/handle colors
BBOX_COLOR: ColorA = (80, 180, 255, 180)
HANDLE_FILL: Color = (250, 250, 250)
HANDLE_BORDER: Color = (35, 120, 220)

# Hover highlight for resize handles
HANDLE_HOVER_FILL: Color = (255, 255, 255)
HANDLE_HOVER_BORDER: Color = (0, 150, 255)

# Rotation visuals
ROT_STEM_COLOR: Color = (80, 180, 255)
ROT_HANDLE_FILL: Color = (255, 255, 255)
ROT_HANDLE_BORDER: Color = (35, 120, 220)

# Hover highlight for rotation knob
ROT_HANDLE_HOVER_FILL: Color = (255, 255, 255)
ROT_HANDLE_HOVER_BORDER: Color = (0, 150, 255)

# --- Clip window  ---
CLIP_BORDER_WIDTH: int = 2
CLIP_DASH_LEN: int = 6
CLIP_DASH_GAP: int = 4


