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

# --- local hit test for hover highlight (mirrors the tool logic) ---
def _hit_test_handle(bbox: pygame.Rect, mouse_canvas: tuple[int, int]) -> str | None:
    centers = bbox_handles((bbox.left, bbox.top, bbox.width, bbox.height), C.ROT_HANDLE_OFFSET)
    mx, my = mouse_canvas

    size = C.HANDLE_SIZE + 2 * C.HANDLE_HIT_PAD
    half = size // 2
    for key in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
        cx, cy = centers[key]
        rect = pygame.Rect(cx - half, cy - half, size, size)
        if rect.collidepoint(mx, my):
            return key

    rx, ry = centers["rot"]
    r_knob = max(C.HANDLE_SIZE // 2 + C.HANDLE_HIT_PAD + 3, 10)
    if (mx - rx) * (mx - rx) + (my - ry) * (my - ry) <= r_knob * r_knob:
        return "rot"

    nx, ny = centers["n"]
    vx, vy = rx - nx, ry - ny
    wx, wy = mx - nx, my - ny
    seg_len2 = vx * vx + vy * vy
    if seg_len2 > 0:
        t = max(0.0, min(1.0, (wx * vx + wy * vy) / seg_len2))
        px = nx + t * vx
        py = ny + t * vy
        dx = mx - px
        dy = my - py
        if dx * dx + dy * dy <= (C.ROT_STEM_HIT_RADIUS ** 2):
            return "rot"

    return None

def _draw_handles(overlay: pygame.Surface, bbox: pygame.Rect, hover_key: str | None) -> None:
    # Stroke bbox
    pygame.draw.rect(overlay, C.BBOX_COLOR, bbox, width=2)

    centers = bbox_handles((bbox.left, bbox.top, bbox.width, bbox.height), C.ROT_HANDLE_OFFSET)

    # Square handles
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

    # Rotation handle + stem
    rx, ry = centers["rot"]
    stem_start = centers["n"]
    pygame.draw.line(overlay, C.ROT_STEM_COLOR, stem_start, (rx, ry), width=2)

    is_rot_hover = hover_key == "rot"
    r = max(half, 5)
    r_fill = C.ROT_HANDLE_HOVER_FILL if is_rot_hover else C.ROT_HANDLE_FILL
    r_border = C.ROT_HANDLE_HOVER_BORDER if is_rot_hover else C.ROT_HANDLE_BORDER
    pygame.draw.circle(overlay, r_fill, (rx, ry), r)
    pygame.draw.circle(overlay, r_border, (rx, ry), r, width=1)

def draw_overlay(overlay: pygame.Surface, scene: Scene, state: AppState) -> None:
    overlay.fill((0, 0, 0, 0))

    # Selection rubber band
    if state.selection.selecting:
        rect = _norm_rect(state.selection.anchor, state.selection.current)
        if rect:
            pygame.draw.rect(overlay, C.ACCENT_FILL, rect)
            pygame.draw.rect(overlay, C.ACCENT_BORDER, rect, width=2)

    # Clip window (live or static)
    if state.mode == Mode.CLIP_WINDOW and state.clip.setting:
        r = _norm_rect(state.clip.anchor, state.clip.current)
        if r:
            pygame.draw.rect(overlay, C.CLIP_FILL, r)
            pygame.draw.rect(overlay, C.CLIP_COLOR, r, width=2)
    elif state.clip.window:
        pygame.draw.rect(overlay, C.CLIP_FILL, _rect_from_tuple(state.clip.window))
        pygame.draw.rect(overlay, C.CLIP_COLOR, _rect_from_tuple(state.clip.window), width=2)

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

    # Selection bbox + handles (with hover highlight)
    if state.selection.selected_lines or state.selection.selected_circles:
        sp = _selection_bbox_and_pivot(scene, state)
        if sp:
            bbox, _ = sp

            # Canvas-relative mouse for hover (convert from screen coords)
            mx, my = pygame.mouse.get_pos()
            hover_key = None
            if mx >= C.UI_W:
                hover_key = _hit_test_handle(bbox, (mx - C.UI_W, my))

            _draw_handles(overlay, bbox, hover_key)
