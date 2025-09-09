import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame

# --- Config ---
WIDTH, HEIGHT = 1000, 650
UI_W = 220
CANVAS_W, CANVAS_H = WIDTH - UI_W, HEIGHT

BG = (30, 30, 35)
UI_BG = (40, 40, 48)
UI_BTN = (60, 60, 68)
UI_BTN_HOVER = (72, 72, 84)
UI_STROKE = (90, 90, 100)
CANVAS_BG = (245, 245, 245)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
ACCENT = (0, 120, 255)
ACCENT_FILL = (0, 120, 255, 40)   
ACCENT_BORDER = (0, 120, 255, 200) 
CLIP_COLOR = (60, 200, 120, 200)
CLIP_FILL = (60, 200, 120, 40)

# --- Geometry / Scene ---
@dataclass
class Point:
    x: int
    y: int

@dataclass
class Line:
    p0: Point
    p1: Point
    algo: str # "DDA" | "BRESENHAM"

@dataclass
class Circle:
    c: Point
    r: int
    algo: str = "BRESENHAM"

class Scene:
    def __init__(self):
        self.lines: List[Line] = []
        self.circles: List[Circle] = []

    def clear(self):
        self.lines.clear()
        self.circles.clear()

# --- UI Button ---
class Button:
    def __init__(self, rect: pygame.Rect, label: str, on_click):
        self.rect = rect
        self.label = label
        self.on_click = on_click
        self.hover = False

    def draw(self, surf, font):
        color = UI_BTN_HOVER if self.hover else UI_BTN
        pygame.draw.rect(surf, color, self.rect, border_radius=8)
        pygame.draw.rect(surf, UI_STROKE, self.rect, width=1, border_radius=8)
        txt = font.render(self.label, True, WHITE)
        surf.blit(txt, (self.rect.x + 10, self.rect.y + (self.rect.h - txt.get_height()) // 2))

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEMOTION and hasattr(ev, "pos"):
            self.hover = self.rect.collidepoint(ev.pos)
        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and hasattr(ev, "pos"):
            if self.rect.collidepoint(ev.pos) and ev.type == pygame.MOUSEBUTTONDOWN:
                self.on_click()

# --- Rasterization ---
def put_pixel(surf: pygame.Surface, x: int, y: int, color: Tuple[int, int, int] = BLACK):
    if 0 <= x < surf.get_width() and 0 <= y < surf.get_height():
        surf.set_at((x, y), color)

def draw_line_dda(surf: pygame.Surface, p0: Point, p1: Point, color: Tuple[int, int, int] = BLACK):
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

def draw_line_bresenham(surf: pygame.Surface, p0: Point, p1: Point, color: Tuple[int, int, int] = BLACK):
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

def draw_circle_bresenham(surf: pygame.Surface, center: Point, r: int, color: Tuple[int, int, int] = BLACK):
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

# --- Selection helpers ---
def norm_rect(a: Tuple[int, int], b: Tuple[int, int]) -> pygame.Rect:
    (x0, y0), (x1, y1) = a, b
    left = min(x0, x1)
    top = min(y0, y1)
    w = abs(x1 - x0)
    h = abs(y1 - y0)
    return pygame.Rect(left, top, w, h)

def point_in_rect(pt: Point, rect: pygame.Rect) -> bool:
    return rect.collidepoint(pt.x, pt.y)

# --- Transform math ---
def rotate_point(px: float, py: float, cx: float, cy: float, theta: float) -> Tuple[int, int]:
    ct = math.cos(theta)
    st = math.sin(theta)

    x = cx + ct*(px - cx) - st*(py - cy)
    y = cy + st*(px - cx) + ct*(py - cy)

    return (int(round(x)), int(round(y)))

def scale_point(px: float, py: float, cx: float, cy: float, s: float) -> Tuple[int, int]:
    x = cx + s*(px - cx)
    y = cy + s*(py - cy)

    return (int(round(x)), int(round(y)))

# --- Clipping (Cohen–Sutherland & Liang–Barsky) ---
INSIDE, LEFT, RIGHT, BOTTOM, TOP = 0, 1, 2, 4, 8

def _cs_code(x: int, y: int, rect: pygame.Rect) -> int:
    code = INSIDE
    if x < rect.left: 
        code |= LEFT
    elif x > rect.right: 
        code |= RIGHT
    if y < rect.top: 
        code |= TOP
    elif y > rect.bottom: 
        code |= BOTTOM
    return code

def cohen_sutherland_clip(p0: Point, p1: Point, rect: pygame.Rect) -> Optional[Tuple[Point, Point]]:
    x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
    code0 = _cs_code(x0, y0, rect)
    code1 = _cs_code(x1, y1, rect)

    while True:
        if not (code0 | code1):
            return Point(x0, y0), Point(x1, y1)
        if code0 & code1:
            return None
        code_out = code0 or code1
        if code_out & TOP:
            x = x0 + (x1 - x0) * (rect.top - y0) / (y1 - y0) if y1 != y0 else x0
            y = rect.top
        elif code_out & BOTTOM:
            x = x0 + (x1 - x0) * (rect.bottom - y0) / (y1 - y0) if y1 != y0 else x0
            y = rect.bottom
        elif code_out & RIGHT:
            y = y0 + (y1 - y0) * (rect.right - x0) / (x1 - x0) if x1 != x0 else y0
            x = rect.right
        else:  # LEFT
            y = y0 + (y1 - y0) * (rect.left - x0) / (x1 - x0) if x1 != x0 else y0
            x = rect.left

        if code_out == code0:
            x0, y0 = int(round(x)), int(round(y))
            code0 = _cs_code(x0, y0, rect)
        else:
            x1, y1 = int(round(x)), int(round(y))
            code1 = _cs_code(x1, y1, rect)

def liang_barsky_clip(p0: Point, p1: Point, rect: pygame.Rect) -> Optional[Tuple[Point, Point]]:
    x0, y0, x1, y1 = p0.x, p0.y, p1.x, p1.y
    dx = x1 - x0
    dy = y1 - y0

    x_min, x_max = rect.left, rect.right
    y_min, y_max = rect.top, rect.bottom

    p = [-dx, dx, -dy, dy]
    q = [x0 - x_min, x_max - x0, y0 - y_min, y_max - y0]

    u0, u1 = 0.0, 1.0
    
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
            continue

        r = qi / pi
        if pi < 0:
            if r > u1: 
                return None
            if r > u0: 
                u0 = r
        else:
            if r < u0: 
                return None
            if r < u1: 
                u1 = r
    nx0 = int(round(x0 + u0 * dx))
    ny0 = int(round(y0 + u0 * dy))
    nx1 = int(round(x0 + u1 * dx))
    ny1 = int(round(y0 + u1 * dy))
    return Point(nx0, ny0), Point(nx1, ny1)

def apply_clipping_to_lines(scene: Scene, rect: pygame.Rect, algo: str, selected: Optional[set] = None) -> Tuple[int,int]:
    indices = list(range(len(scene.lines))) if not selected else sorted(selected)
    keep = []
    kept = 0
    removed = 0
    selected_set = set(indices)
    for i, ln in enumerate(scene.lines):
        if i not in selected_set and selected is not None:
            keep.append(ln)
            continue
        if algo == "CS":
            res = cohen_sutherland_clip(ln.p0, ln.p1, rect)
        else:
            res = liang_barsky_clip(ln.p0, ln.p1, rect)
        if res is None:
            removed += 1
            # drop line
        else:
            (np0, np1) = res
            keep.append(Line(Point(np0.x, np0.y), Point(np1.x, np1.y), ln.algo))
            kept += 1
    scene.lines = keep
    return kept, removed

def main():
    pygame.init()
    pygame.display.set_caption("TP1 CG - Mode: IDLE")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Surfaces
    ui = pygame.Surface((UI_W, HEIGHT))
    canvas = pygame.Surface((CANVAS_W, CANVAS_H))
    overlay = pygame.Surface((CANVAS_W, CANVAS_H), pygame.SRCALPHA)

    font = pygame.font.SysFont("consolas", 18, bold=True)
    font_small = pygame.font.SysFont("consolas", 16)

    # --- App state ---
    mode = "IDLE"
    scene = Scene()

    # drawing states
    pending_start: Optional[Point] = None
    pending_center: Optional[Point] = None

    # selection state
    selecting: bool = False
    sel_anchor: Optional[Tuple[int, int]] = None
    sel_current: Optional[Tuple[int, int]] = None
    selected_lines: set[int] = set()
    selected_circles: set[int] = set()

    def reset_selection():
        nonlocal selecting, sel_anchor, sel_current, selected_lines, selected_circles
        selecting = False
        sel_anchor = None
        sel_current = None
        selected_lines.clear()
        selected_circles.clear()
    
    # transform drag state (shared across translate/rotate/scale)
    dragging: bool = False
    drag_anchor: Optional[Tuple[int, int]] = None
    lines_snapshot: List[Tuple[int, Tuple[int, int, int, int]]] = []
    circles_snapshot: List[Tuple[int, Tuple[int, int, int, int]]] = []
    pivot: Optional[Tuple[float, float]] = None
    anchor_angle: float = 0.0
    anchor_dist: float = 1.0

    # clipping window state
    clip_setting: bool = False
    clip_anchor: Optional[Tuple[int, int]] = None
    clip_current: Optional[Tuple[int, int]] = None
    clip_window: Optional[pygame.Rect] = None

    def translating_state_reset():
        nonlocal dragging, drag_anchor, lines_snapshot, circles_snapshot, pivot
        dragging = False
        drag_anchor = None
        lines_snapshot = []
        circles_snapshot = []
        pivot = None


    def set_line_dda():
        nonlocal mode, pending_start, pending_center
        mode = "LINE_DDA"
        pending_start = None
        pending_center = None
        reset_selection()
        translating_state_reset()

    def set_line_bresenham():
        nonlocal mode, pending_start, pending_center
        mode = "LINE_BRESENHAM"
        pending_start = None
        pending_center = None
        reset_selection()
        translating_state_reset()

    def set_circle_bresenham():
        nonlocal mode, pending_start, pending_center
        mode = "CIRCLE_BRESENHAM"
        pending_start = None
        pending_center = None
        reset_selection()
        translating_state_reset()


    def set_select_mode():
        nonlocal mode, pending_start, pending_center
        mode = "SELECT"
        pending_start = None
        pending_center = None
        translating_state_reset()

    def set_translate_mode():
        nonlocal mode, pending_start, pending_center
        mode = "TRANSLATE"
        pending_start = None
        pending_center = None
        translating_state_reset()


    def set_rotate_mode():
        nonlocal mode, pending_start, pending_center
        mode = "ROTATE"
        pending_start = None
        pending_center = None
        translating_state_reset()

    def set_scale_mode():
        nonlocal mode, pending_start, pending_center
        mode = "SCALE_UNIFORM"
        pending_start = None
        pending_center = None
        translating_state_reset()

    def set_clip_window_mode():
        nonlocal mode
        mode = "CLIP_WINDOW"
        translating_state_reset()

    def do_clip_cs():
        if not clip_window: 
            return
        target = selected_lines if selected_lines else None
        apply_clipping_to_lines(scene, clip_window, "CS", target)
        reset_selection()
        redraw_canvas_from_scene()

    def do_clip_lb():
        if not clip_window: 
            return
        target = selected_lines if selected_lines else None
        apply_clipping_to_lines(scene, clip_window, "LB", target)
        reset_selection()
        redraw_canvas_from_scene()

    def clear_canvas():
        nonlocal mode, pending_start, pending_center, clip_window
        mode = "IDLE"
        pending_start = None
        pending_center = None
        scene.clear()
        reset_selection()
        translating_state_reset()
        clip_window = None
        canvas.fill(CANVAS_BG)

    buttons = []
    pad, bw, bh = 12, UI_W - 2 * 12, 44
    y = 56

    def add_button(label, cb):
        nonlocal y
        buttons.append(Button(pygame.Rect(pad, y, bw, bh), label, cb))
        y += bh + 10

    add_button("Select", set_select_mode)
    add_button("Translate", set_translate_mode)
    add_button("Rotate", set_rotate_mode)
    add_button("Scale (Uniform)", set_scale_mode)

    add_button("Line (DDA)", set_line_dda)
    add_button("Line (Bresenham)", set_line_bresenham)
    add_button("Circle (Bresenham)", set_circle_bresenham)

    add_button("Set Clip Window", set_clip_window_mode)      
    add_button("Clip (Cohen-Suth.)", do_clip_cs)             
    add_button("Clip (Liang-Barsky)", do_clip_lb)            

    add_button("Clear Canvas", clear_canvas)

    canvas.fill(CANVAS_BG)

    def to_canvas_pos(pos) -> Optional[Tuple[int, int]]:
        x, y = pos
        if x < UI_W:
            return None
        return (x - UI_W, y)
    
    def selection_bbox_and_pivot() -> Optional[Tuple[pygame.Rect, Tuple[float,float]]]:
        xs: List[int] = []
        ys: List[int] = []
        for i in selected_lines:
            ln = scene.lines[i]
            xs.extend([ln.p0.x, ln.p1.x])
            ys.extend([ln.p0.y, ln.p1.y])
        for i in selected_circles:
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
    
    def redraw_canvas_from_scene():
        canvas.fill(CANVAS_BG)
        for ln in scene.lines:
            if ln.algo == "DDA":
                draw_line_dda(canvas, ln.p0, ln.p1, BLACK)
            else:
                draw_line_bresenham(canvas, ln.p0, ln.p1, BLACK)
        for c in scene.circles:
            draw_circle_bresenham(canvas, c.c, c.r, BLACK)
    
    def redraw_overlay():
        overlay.fill((0,0,0,0))

        if selecting and sel_anchor and sel_current:
            rect = norm_rect(sel_anchor, sel_current)
            pygame.draw.rect(overlay, ACCENT_FILL, rect)
            pygame.draw.rect(overlay, ACCENT_BORDER, rect, width=2)

        if mode == "CLIP_WINDOW" and clip_setting and clip_anchor and clip_current:
            r = norm_rect(clip_anchor, clip_current)
            pygame.draw.rect(overlay, CLIP_FILL, r)
            pygame.draw.rect(overlay, CLIP_COLOR, r, width=2)
        elif clip_window:
            pygame.draw.rect(overlay, CLIP_FILL, clip_window)
            pygame.draw.rect(overlay, CLIP_COLOR, clip_window, width=2)

        if selected_lines:
            valid_line_indices = {i for i in selected_lines if 0 <= i < len(scene.lines)}
            if valid_line_indices != selected_lines:
                selected_lines.intersection_update(valid_line_indices)
        if selected_circles:
            valid_circle_indices = {i for i in selected_circles if 0 <= i < len(scene.circles)}
            if valid_circle_indices != selected_circles:
                selected_circles.intersection_update(valid_circle_indices)

        # Draw pivot + bbox for transforms
        sp = selection_bbox_and_pivot()
        if sp:
            bbox, (cx, cy) = sp
            pygame.draw.rect(overlay, (80,180,255,120), bbox, width=2)
            pygame.draw.circle(overlay, (255,140,0,220), (int(cx), int(cy)), 4)  # pivot marker

        # highlights
        for i in selected_lines:
            ln = scene.lines[i]
            if ln.algo == "DDA":
                draw_line_dda(overlay, ln.p0, ln.p1, ACCENT[:3])
            else:
                draw_line_bresenham(overlay, ln.p0, ln.p1, ACCENT[:3])
        for i in selected_circles:
            c = scene.circles[i]
            draw_circle_bresenham(overlay, c.c, c.r, ACCENT[:3])
    
    def run_selection(rect: pygame.Rect):
        nonlocal selected_lines, selected_circles
        selected_lines = set()
        selected_circles = set()

        for i, ln in enumerate(scene.lines):
            if point_in_rect(ln.p0, rect) or point_in_rect(ln.p1, rect):
                selected_lines.add(i)

        for i, c in enumerate(scene.circles):
            if point_in_rect(c.c, rect):
                selected_circles.add(i)



    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                if hasattr(ev, "pos") and ev.pos[0] < UI_W:
                    for b in buttons:
                        b.handle_event(ev)
                else:
                    cpos = to_canvas_pos(ev.pos) if hasattr(ev, "pos") else None

                    # --- SELECT mode ---
                    if mode == "SELECT":
                        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
                            selecting = True
                            sel_anchor = cpos
                            sel_current = cpos
                        elif ev.type == pygame.MOUSEMOTION and cpos and selecting:
                            sel_current = cpos
                        elif ev.type == pygame.MOUSEBUTTONUP and cpos and selecting:
                            selecting = False
                            rect = norm_rect(sel_anchor, sel_current)
                            run_selection(rect)

                    # --- CLIP_WINDOW mode ---
                    elif mode == "CLIP_WINDOW":
                        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
                            clip_setting = True
                            clip_anchor = cpos
                            clip_current = cpos
                        elif ev.type == pygame.MOUSEMOTION and cpos and clip_setting:
                            clip_current = cpos
                        elif ev.type == pygame.MOUSEBUTTONUP and cpos and clip_setting:
                            clip_setting = False
                            clip_window = norm_rect(clip_anchor, clip_current)

                    # --- TRANSLATE mode ---
                    elif mode == "TRANSLATE":
                        if ev.type == pygame.MOUSEBUTTONDOWN and cpos and (selected_lines or selected_circles):
                            dragging = True
                            drag_anchor = cpos

                            lines_snapshot = [(i, (scene.lines[i].p0.x, scene.lines[i].p0.y,
                                                   scene.lines[i].p1.x, scene.lines[i].p1.y))
                                              for i in selected_lines]
                            circles_snapshot = [(i, (scene.circles[i].c.x, scene.circles[i].c.y))
                                                for i in selected_circles]
                        elif ev.type == pygame.MOUSEMOTION and cpos and dragging and drag_anchor:
                            dx = cpos[0] - drag_anchor[0]
                            dy = cpos[1] - drag_anchor[1]
                            # apply to scene using snapshots (no cumulative drift)
                            for i, (x0, y0, x1, y1) in lines_snapshot:
                                scene.lines[i].p0.x = x0 + dx
                                scene.lines[i].p0.y = y0 + dy
                                scene.lines[i].p1.x = x1 + dx
                                scene.lines[i].p1.y = y1 + dy
                            for i, (cx, cy) in circles_snapshot:
                                scene.circles[i].c.x = cx + dx
                                scene.circles[i].c.y = cy + dy
                            redraw_canvas_from_scene()
                        elif ev.type == pygame.MOUSEBUTTONUP and dragging:
                            dragging = False
                            drag_anchor = None
                            lines_snapshot = []
                            circles_snapshot = []

                     # --- ROTATE (around selection bbox center) ---
                    elif mode == "ROTATE":
                        if ev.type == pygame.MOUSEBUTTONDOWN and cpos and (selected_lines or selected_circles):
                            sp = selection_bbox_and_pivot()
                            if not sp:
                                continue
                            _, (cx, cy) = sp
                            pivot = (cx, cy)
                            dragging = True
                            drag_anchor = cpos
                            ax, ay = cpos[0] - cx, cpos[1] - cy
                            anchor_angle = math.atan2(ay, ax) if (ax or ay) else 0.0
                            # snapshot originals
                            lines_snapshot = [(i, (scene.lines[i].p0.x, scene.lines[i].p0.y,
                                                   scene.lines[i].p1.x, scene.lines[i].p1.y))
                                              for i in selected_lines]
                            circles_snapshot = [(i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
                                                for i in selected_circles]
                        elif ev.type == pygame.MOUSEMOTION and cpos and dragging and pivot:
                            cx, cy = pivot
                            vx, vy = cpos[0] - cx, cpos[1] - cy
                            cur_angle = math.atan2(vy, vx) if (vx or vy) else anchor_angle
                            theta = cur_angle - anchor_angle
                            # rotate from snapshots
                            for i, (x0, y0, x1, y1) in lines_snapshot:
                                nx0, ny0 = rotate_point(x0, y0, cx, cy, theta)
                                nx1, ny1 = rotate_point(x1, y1, cx, cy, theta)
                                scene.lines[i].p0.x, scene.lines[i].p0.y = nx0, ny0
                                scene.lines[i].p1.x, scene.lines[i].p1.y = nx1, ny1
                            for i, (cx0, cy0, r0) in circles_snapshot:
                                ncx, ncy = rotate_point(cx0, cy0, cx, cy, theta)
                                scene.circles[i].c.x, scene.circles[i].c.y = ncx, ncy
                                scene.circles[i].r = r0  # radius unchanged by rotation
                            redraw_canvas_from_scene()
                        elif ev.type == pygame.MOUSEBUTTONUP and dragging:
                            dragging = False
                            drag_anchor = None
                            lines_snapshot = []
                            circles_snapshot = []
                            pivot = None

                    # --- SCALE_UNIFORM (around selection bbox center) ---
                    elif mode == "SCALE_UNIFORM":
                        if ev.type == pygame.MOUSEBUTTONDOWN and cpos and (selected_lines or selected_circles):
                            sp = selection_bbox_and_pivot()
                            if not sp:
                                continue
                            _, (cx, cy) = sp
                            pivot = (cx, cy)
                            dragging = True
                            drag_anchor = cpos
                            dx0, dy0 = cpos[0] - cx, cpos[1] - cy
                            anchor_dist = max(1e-6, math.hypot(dx0, dy0))  # avoid /0
                            # snapshot originals
                            lines_snapshot = [(i, (scene.lines[i].p0.x, scene.lines[i].p0.y,
                                                   scene.lines[i].p1.x, scene.lines[i].p1.y))
                                              for i in selected_lines]
                            circles_snapshot = [(i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
                                                for i in selected_circles]
                        elif ev.type == pygame.MOUSEMOTION and cpos and dragging and pivot:
                            cx, cy = pivot
                            dx, dy = cpos[0] - cx, cpos[1] - cy
                            cur_dist = max(1e-6, math.hypot(dx, dy))
                            s = cur_dist / anchor_dist
                            # scale from snapshots (uniform)
                            for i, (x0, y0, x1, y1) in lines_snapshot:
                                nx0, ny0 = scale_point(x0, y0, cx, cy, s)
                                nx1, ny1 = scale_point(x1, y1, cx, cy, s)
                                scene.lines[i].p0.x, scene.lines[i].p0.y = nx0, ny0
                                scene.lines[i].p1.x, scene.lines[i].p1.y = nx1, ny1
                            for i, (cx0, cy0, r0) in circles_snapshot:
                                ncx, ncy = scale_point(cx0, cy0, cx, cy, s)
                                scene.circles[i].c.x, scene.circles[i].c.y = ncx, ncy
                                scene.circles[i].r = max(0, int(round(r0 * s)))
                            redraw_canvas_from_scene()
                        elif ev.type == pygame.MOUSEBUTTONUP and dragging:
                            dragging = False
                            drag_anchor = None
                            lines_snapshot = []
                            circles_snapshot = []
                            pivot = None

                    elif ev.type == pygame.MOUSEBUTTONDOWN and cpos:
                        cx, cy = cpos
                        if mode == "LINE_DDA":
                            if pending_start is None:
                                pending_start = Point(cx, cy)
                                put_pixel(canvas, cx, cy, (0, 120, 255))
                            else:
                                end = Point(cx, cy)
                                scene.lines.append(Line(pending_start, end, "DDA"))
                                draw_line_dda(canvas, pending_start, end, BLACK)
                                pending_start = None

                        elif mode == "LINE_BRESENHAM":
                            if pending_start is None:
                                pending_start = Point(cx, cy)
                                put_pixel(canvas, cx, cy, (0, 120, 255))
                            else:
                                end = Point(cx, cy)
                                scene.lines.append(Line(pending_start, end, "DDA"))
                                draw_line_bresenham(canvas, pending_start, end, BLACK)
                                pending_start = None

                        elif mode == "CIRCLE_BRESENHAM":
                            if pending_center is None:
                                pending_center = Point(cx, cy)
                                put_pixel(canvas, cx, cy, (0, 120, 255))

                            else:
                                dx =  cx - pending_center.x
                                dy = cy - pending_center.y
                                r = max(0, int(round(math.hypot(dx, dy))))
                                scene.circles.append(Circle(pending_center, r, "BRESENHAM"))   
                                draw_circle_bresenham(canvas, pending_center, r, BLACK)
                                pending_center = None                             


        # draw UI
        ui.fill(UI_BG)
        title = font.render("TP1 - CG", True, WHITE)
        ui.blit(title, (12, 12))
        mode_txt = font_small.render(f"Moda: {mode}", True, (220, 220, 230))
        ui.blit(mode_txt, (12, 34))
        sel_info = f"Selected: {len(selected_lines)} lines, {len(selected_circles)} circles"
        ui.blit(font_small.render(sel_info, True, (200, 210, 220)), (12, 54 + 44*4 + 40))  # under buttons


        for b in buttons:
            b.draw(ui, font_small)

        redraw_overlay()
    
        # compose frame
        screen.fill(BG)
        screen.blit(ui, (0, 0))
        screen.blit(canvas, (UI_W, 0))
        screen.blit(overlay, (UI_W, 0))
        pygame.display.set_caption(f"TP1 CG — Mode: {mode}")
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
