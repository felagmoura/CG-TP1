from __future__ import annotations

import pygame

from .. import config as C
from ..scene.scene import Scene
from ..state import AppState, Mode
from ..utils.geom import bbox_handles


def _rect_from_tuple(r: tuple[int, int, int, int]) -> pygame.Rect:
    l, t, w, h = r
    return pygame.Rect(l, t, w, h)


def _norm_rect(a: tuple[int, int] | None, b: tuple[int, int] | None) -> pygame.Rect | None:
    if not a or not b:
        return None
    (x0, y0), (x1, y1) = a, b
    left = min(x0, x1)
    top = min(y0, y1)
    w = abs(x1 - x0)
    h = abs(y1 - y0)
    return pygame.Rect(left, top, w, h)


def _selection_bbox_and_pivot(scene: Scene, state: AppState) -> tuple[pygame.Rect, tuple[float, float]] | None:
    xs: list[int] = []
    ys: list[int] = []
    for i in state.selection.selected_lines:
        if 0 <= i < len(scene.lines):
            ln = scene.lines[i]
            xs.extend([ln.p0.x, ln.p1.x])
            ys.extend([ln.p0.y, ln.p1.y])
    for i in state.selection.selected_circles:
        if 0 <= i < len(scene.circles):
            c = scene.circles[i]
            xs.extend([c.c.x - c.r, c.c.x + c.r])
            ys.extend([c.c.y - c.r, c.c.y + c.r])
    if not xs or not ys:
        return None
    left, right = min(xs), max(xs)
    top, bottom = min(ys), max(ys)
    rect = pygame.Rect(left, top, right - left, bottom - top)
    cx, cy = (left + right) / 2.0, (top + bottom) / 2.0
    return rect, (cx, cy)


def _sanitize_selection(scene: Scene, state: AppState) -> None:
    if state.selection.selected_lines:
        valid = {i for i in state.selection.selected_lines if 0 <= i < len(scene.lines)}
        state.selection.selected_lines.intersection_update(valid)
    if state.selection.selected_circles:
        valid = {i for i in state.selection.selected_circles if 0 <= i < len(scene.circles)}
        state.selection.selected_circles.intersection_update(valid)


# ---------- dashed stroke helpers (axis-aligned) ----------

def _dashed_hline(surf: pygame.Surface, y: int, x0: int, x1: int, color, dash: int, gap: int, width: int) -> None:
    if x1 < x0:
        x0, x1 = x1, x0
    step = max(1, dash + gap)
    x = x0
    while x <= x1:
        xe = min(x + dash, x1)
        pygame.draw.line(surf, color, (x, y), (xe, y), width)
        x += step


def _dashed_vline(surf: pygame.Surface, x: int, y0: int, y1: int, color, dash: int, gap: int, width: int) -> None:
    if y1 < y0:
        y0, y1 = y1, y0
    step = max(1, dash + gap)
    y = y0
    while y <= y1:
        ye = min(y + dash, y1)
        pygame.draw.line(surf, color, (x, y), (x, ye), width)
        y += step


def _draw_dashed_rect(surf: pygame.Surface, rect: pygame.Rect, color, width: int, dash: int, gap: int) -> None:
    l, t, w, h = rect
    r = l + w
    b = t + h
    _dashed_hline(surf, t, l, r, color, dash, gap, width)
    _dashed_hline(surf, b, l, r, color, dash, gap, width)
    _dashed_vline(surf, l, t, b, color, dash, gap, width)
    _dashed_vline(surf, r, t, b, color, dash, gap, width)


# ---------- handle helpers ----------

def _hit_test_clip_handle(bbox: pygame.Rect, mouse_canvas: tuple[int, int]) -> str | None:
    """Return one of the 8 resize handle keys if hovered; else None."""
    centers = bbox_handles((bbox.left, bbox.top, bbox.width, bbox.height), C.ROT_HANDLE_OFFSET)
    mx, my = mouse_canvas
    size = C.HANDLE_SIZE + 2 * C.HANDLE_HIT_PAD
    half = size // 2
    for key in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
        cx, cy = centers[key]
        rect = pygame.Rect(cx - half, cy - half, size, size)
        if rect.collidepoint(mx, my):
            return key
    return None


def _draw_clip_handles(overlay: pygame.Surface, bbox: pygame.Rect, hover_key: str | None) -> None:
    """Draw 8 square resize handles for the clip window, with hover highlight."""
    centers = bbox_handles((bbox.left, bbox.top, bbox.width, bbox.height), C.ROT_HANDLE_OFFSET)
    s = C.HANDLE_SIZE
    half = s // 2
    for key in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
        cx, cy = centers[key]
        rect = pygame.Rect(cx - half, cy - half, s, s)
        is_hover = hover_key == key
        fill = C.HANDLE_HOVER_FILL if is_hover else C.HANDLE_FILL
        border = C.HANDLE_HOVER_BORDER if is_hover else C.HANDLE_BORDER
        pygame.draw.rect(overlay, fill, rect)
        pygame.draw.rect(overlay, border, rect, width=1)


def _draw_handles_with_rotation(overlay: pygame.Surface, bbox: pygame.Rect) -> None:
    """Selection bbox handles (8 squares) + rotation knob (existing behavior)."""
    pygame.draw.rect(overlay, C.BBOX_COLOR, bbox, width=2)
    centers = bbox_handles((bbox.left, bbox.top, bbox.width, bbox.height), C.ROT_HANDLE_OFFSET)

    s = C.HANDLE_SIZE
    half = s // 2
    for key in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
        cx, cy = centers[key]
        rect = pygame.Rect(cx - half, cy - half, s, s)
        pygame.draw.rect(overlay, C.HANDLE_FILL, rect)
        pygame.draw.rect(overlay, C.HANDLE_BORDER, rect, width=1)

    # Rotation knob + stem
    rx, ry = centers["rot"]
    stem_start = centers["n"]
    pygame.draw.line(overlay, C.ROT_STEM_COLOR, stem_start, (rx, ry), width=2)
    pygame.draw.circle(overlay, C.ROT_HANDLE_FILL, (rx, ry), max(half, 5))
    pygame.draw.circle(overlay, C.ROT_HANDLE_BORDER, (rx, ry), max(half, 5), width=1)


def draw_overlay(overlay: pygame.Surface, scene: Scene, state: AppState) -> None:
    overlay.fill((0, 0, 0, 0))

    # Selection rubber band
    if state.selection.selecting:
        rect = _norm_rect(state.selection.anchor, state.selection.current)
        if rect:
            pygame.draw.rect(overlay, C.ACCENT_FILL, rect)
            pygame.draw.rect(overlay, C.ACCENT_BORDER, rect, width=2)

    # --- Clip window visuals ---
    if state.mode == Mode.CLIP_WINDOW:
        # Live creating
        if state.clip.setting:
            r = _norm_rect(state.clip.anchor, state.clip.current)
            if r:
                pygame.draw.rect(overlay, C.CLIP_FILL, r)
                _draw_dashed_rect(overlay, r, C.BBOX_COLOR, C.CLIP_BORDER_WIDTH, C.CLIP_DASH_LEN, C.CLIP_DASH_GAP)
        # Existing window in clip mode: dashed border + handles with hover
        elif state.clip.window:
            r = _rect_from_tuple(state.clip.window)
            pygame.draw.rect(overlay, C.CLIP_FILL, r)
            _draw_dashed_rect(overlay, r, C.BBOX_COLOR, C.CLIP_BORDER_WIDTH, C.CLIP_DASH_LEN, C.CLIP_DASH_GAP)

            # Determine hover handle (canvas coords from mouse)
            mx, my = pygame.mouse.get_pos()
            hover_key = None
            if mx >= C.UI_W:
                hover_key = _hit_test_clip_handle(r, (mx - C.UI_W, my))

            _draw_clip_handles(overlay, r, hover_key)
    else:
        # Outside clip mode: static clip window (solid outline)
        if state.clip.window:
            r = _rect_from_tuple(state.clip.window)
            pygame.draw.rect(overlay, C.CLIP_FILL, r)
            pygame.draw.rect(overlay, C.CLIP_COLOR, r, width=2)

    # Clean selection sets
    _sanitize_selection(scene, state)

    # Selected-shape highlights (accent overlay)
    from ..algorithms.circles import draw_circle_bresenham
    from ..algorithms.lines import draw_line_bresenham, draw_line_dda

    for i in state.selection.selected_lines:
        ln = scene.lines[i]
        if ln.algo == "DDA":
            draw_line_dda(overlay, ln.p0, ln.p1, C.ACCENT)
        else:
            draw_line_bresenham(overlay, ln.p0, ln.p1, C.ACCENT)

    for i in state.selection.selected_circles:
        c = scene.circles[i]
        draw_circle_bresenham(overlay, c.c, c.r, C.ACCENT)

    # Selection bbox + handles (with rotation)
    if state.selection.selected_lines or state.selection.selected_circles:
        sp = _selection_bbox_and_pivot(scene, state)
        if sp:
            bbox, _ = sp
            _draw_handles_with_rotation(overlay, bbox)
