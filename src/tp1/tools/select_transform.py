from __future__ import annotations

import math

import pygame

from .. import config as C
from ..render.renderer import redraw_canvas_from_scene
from ..scene.scene import Scene
from ..state import AppState
from ..utils.geom import bbox_handles, rect_from_points
from ..utils.transforms import rotate_point_i, scale_point_xy_i


def _selection_bbox(scene: Scene, state: AppState) -> pygame.Rect | None:
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
    return pygame.Rect(left, top, right - left, bottom - top)


# Map each handle to its opposite (pivot when not scaling-from-center)
_OPPOSITE = {
    "nw": "se", "n": "s", "ne": "sw", "e": "w",
    "se": "nw", "s": "n", "sw": "ne", "w": "e",
}


def _affects_axes(handle: str) -> tuple[bool, bool]:
    """Return (affects_x, affects_y) for a given handle key."""
    if handle in ("n", "s"):
        return (False, True)
    if handle in ("e", "w"):
        return (True, False)
    # corners
    return (True, True)


def _hit_test_handle(bbox: pygame.Rect, mouse: tuple[int, int]) -> str | None:
    """
    Return handle key ("nw","n","ne","e","se","s","sw","w","rot") if mouse hits one.
    Otherwise None. Includes clickable rotation *stem* for better UX.
    """
    centers = bbox_handles((bbox.left, bbox.top, bbox.width, bbox.height), C.ROT_HANDLE_OFFSET)
    mx, my = mouse

    # square handles first (corners/edges)
    size = C.HANDLE_SIZE + 2 * C.HANDLE_HIT_PAD
    half = size // 2
    for key in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
        cx, cy = centers[key]
        rect = pygame.Rect(cx - half, cy - half, size, size)
        if rect.collidepoint(mx, my):
            return key

    # rotation knob: circular hit area (slightly larger than visual)
    rx, ry = centers["rot"]
    r_knob = max(C.HANDLE_SIZE // 2 + C.HANDLE_HIT_PAD + 3, 10)
    if (mx - rx) * (mx - rx) + (my - ry) * (my - ry) <= r_knob * r_knob:
        return "rot"

    # rotation stem: treat clicks near the stem as rotation, too
    nx, ny = centers["n"]  # top-middle of bbox
    # distance from point to segment (nx,ny) -> (rx,ry), squared
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


# ---- Cursor helpers ---------------------------------------------------------

# Cache the last set cursor to avoid redundant calls
_last_cursor_const: int | None = None

def _set_cursor(system_cursor_const: int) -> None:
    """Set a system cursor if available; cache to avoid redundant calls."""
    global _last_cursor_const
    if _last_cursor_const == system_cursor_const:
        return
    try:
        # Pygame 2: set a system cursor directly by constant
        pygame.mouse.set_cursor(system_cursor_const)  # type: ignore[arg-type]
        _last_cursor_const = system_cursor_const
        return
    except Exception:
        pass
    try:
        # Fallback: wrap in Cursor object
        pygame.mouse.set_cursor(pygame.cursors.Cursor(system_cursor_const))
        _last_cursor_const = system_cursor_const
    except Exception:
        # Last resort: do nothing (keep whatever cursor is active)
        pass


def _cursor_for_handle(handle: str) -> int:
    """Map a handle key to a system cursor constant."""
    if handle in ("n", "s"):
        return pygame.SYSTEM_CURSOR_SIZENS
    if handle in ("e", "w"):
        return pygame.SYSTEM_CURSOR_SIZEWE
    if handle in ("ne", "sw"):
        return pygame.SYSTEM_CURSOR_SIZENESW
    if handle in ("nw", "se"):
        return pygame.SYSTEM_CURSOR_SIZENWSE
    if handle == "rot":
        return pygame.SYSTEM_CURSOR_HAND
    return pygame.SYSTEM_CURSOR_ARROW


# ----------------------------------------------------------------------------


class SelectTransformTool:
    """
    Unified selection + transform tool.
    - Drag on empty canvas: rubber-band select.
    - Drag inside selection bbox: move selection.
    - Drag a corner/edge handle: scale (2D for corners, 1D for edges).
      * Shift: uniform scale (sx == sy) for corners.
      * Alt: scale from center (pivot = bbox center) instead of opposite side.
    - Drag the rotation handle: rotate around bbox center.
      * Shift: snap rotation to C.SNAP_ANGLE_DEG increments.
    - Hover feedback: cursor changes for move/scale/rotate.
    """

    # runtime fields for current gesture (kept inside the tool; no state.py changes)
    _mode: str | None = None  # "selecting" | "moving" | "scaling" | "rotating"
    _handle: str | None = None
    _bbox0: pygame.Rect | None = None
    _pivot: tuple[float, float] | None = None
    _h0: tuple[int, int] | None = None  # grabbed handle original position
    _anchor_angle: float = 0.0          # for rotation

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Drag to select; drag inside selection to move; handles to scale; rotate knob to rotate"
        _set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    def exit(self, state: AppState, scene: Scene) -> None:
        state.selection.selecting = False
        state.transform.reset()
        state.status = ""
        self._mode = None
        self._handle = None
        self._bbox0 = None
        self._pivot = None
        self._h0 = None
        self._anchor_angle = 0.0
        _set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # ------------ begin gestures ------------

    def _begin_move(self, cpos: tuple[int, int], state: AppState, scene: Scene) -> None:
        tr = state.transform
        sel = state.selection
        tr.dragging = True
        tr.anchor = cpos
        tr.lines_snapshot = [
            (i, (scene.lines[i].p0.x, scene.lines[i].p0.y, scene.lines[i].p1.x, scene.lines[i].p1.y))
            for i in sel.selected_lines
            if 0 <= i < len(scene.lines)
        ]
        tr.circles_snapshot = [
            (i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
            for i in sel.selected_circles
            if 0 <= i < len(scene.circles)
        ]
        state.status = "Moving…"
        self._mode = "moving"
        _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)

    def _begin_scale(self, handle: str, cpos: tuple[int, int], state: AppState, scene: Scene) -> None:
        assert handle in ("nw", "n", "ne", "e", "se", "s", "sw", "w")
        bx = _selection_bbox(scene, state)
        if not bx:
            return
        self._bbox0 = bx.copy()
        centers = bbox_handles((bx.left, bx.top, bx.width, bx.height), C.ROT_HANDLE_OFFSET)
        self._handle = handle
        self._h0 = centers[handle]

        mods = pygame.key.get_mods()
        alt = bool(mods & pygame.KMOD_ALT)
        if alt:
            # scale from center
            cx = (bx.left + bx.right) / 2.0
            cy = (bx.top + bx.bottom) / 2.0
            self._pivot = (cx, cy)
        else:
            # pivot is the opposite handle center
            opp = _OPPOSITE[handle]
            self._pivot = tuple(map(float, centers[opp]))  # type: ignore[arg-type]

        # snapshot shapes
        tr = state.transform
        sel = state.selection
        tr.dragging = True
        tr.anchor = cpos
        tr.lines_snapshot = [
            (i, (scene.lines[i].p0.x, scene.lines[i].p0.y, scene.lines[i].p1.x, scene.lines[i].p1.y))
            for i in sel.selected_lines
            if 0 <= i < len(scene.lines)
        ]
        tr.circles_snapshot = [
            (i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
            for i in sel.selected_circles
            if 0 <= i < len(scene.circles)
        ]
        self._mode = "scaling"
        state.status = "Scaling…"
        _set_cursor(_cursor_for_handle(handle))

    def _begin_rotate(self, cpos: tuple[int, int], state: AppState, scene: Scene) -> None:
        bx = _selection_bbox(scene, state)
        if not bx:
            return
        # pivot is bbox center
        cx = (bx.left + bx.right) / 2.0
        cy = (bx.top + bx.bottom) / 2.0
        self._pivot = (cx, cy)

        # anchor angle from pivot to mouse
        ax, ay = cpos[0] - cx, cpos[1] - cy
        self._anchor_angle = math.atan2(ay, ax) if (ax or ay) else 0.0

        # snapshot shapes
        tr = state.transform
        sel = state.selection
        tr.dragging = True
        tr.anchor = cpos  # not strictly needed for rotation, but keeps symmetry
        tr.lines_snapshot = [
            (i, (scene.lines[i].p0.x, scene.lines[i].p0.y, scene.lines[i].p1.x, scene.lines[i].p1.y))
            for i in sel.selected_lines
            if 0 <= i < len(scene.lines)
        ]
        tr.circles_snapshot = [
            (i, (scene.circles[i].c.x, scene.circles[i].c.y, scene.circles[i].r))
            for i in sel.selected_circles
            if 0 <= i < len(scene.circles)
        ]

        self._mode = "rotating"
        state.status = "Rotating…"
        _set_cursor(pygame.SYSTEM_CURSOR_HAND)

    # ------------ live application during drag ------------

    def _apply_move(self, cpos: tuple[int, int], *, state: AppState, scene: Scene, canvas: pygame.Surface) -> None:
        tr = state.transform
        if not (tr.dragging and tr.anchor):
            return
        dx = cpos[0] - tr.anchor[0]
        dy = cpos[1] - tr.anchor[1]
        for i, (x0, y0, x1, y1) in tr.lines_snapshot:
            if 0 <= i < len(scene.lines):
                scene.lines[i].p0.x = x0 + dx
                scene.lines[i].p0.y = y0 + dy
                scene.lines[i].p1.x = x1 + dx
                scene.lines[i].p1.y = y1 + dy
        for i, (cx0, cy0, r0) in tr.circles_snapshot:
            if 0 <= i < len(scene.circles):
                scene.circles[i].c.x = cx0 + dx
                scene.circles[i].c.y = cy0 + dy
                scene.circles[i].r = r0
        state.status = f"Move: ({dx}, {dy})"
        redraw_canvas_from_scene(canvas, scene)

    def _apply_scale(self, cpos: tuple[int, int], *, state: AppState, scene: Scene, canvas: pygame.Surface) -> None:
        if self._mode != "scaling" or self._handle is None or self._bbox0 is None or self._pivot is None:
            return

        affect_x, affect_y = _affects_axes(self._handle)
        hx0, hy0 = self._h0 if self._h0 else (cpos[0], cpos[1])
        px, py = self._pivot

        mods = pygame.key.get_mods()
        uniform = bool(mods & pygame.KMOD_SHIFT)

        sx = 1.0
        sy = 1.0
        if affect_x:
            denom_x = (hx0 - px)
            if abs(denom_x) > 1e-6:
                sx = (cpos[0] - px) / denom_x
        if affect_y:
            denom_y = (hy0 - py)
            if abs(denom_y) > 1e-6:
                sy = (cpos[1] - py) / denom_y

        if uniform and affect_x and affect_y:
            if abs(sx) >= abs(sy):
                s = sx
                sy = math.copysign(abs(s), sy if sy != 0 else 1.0)
                sx = s
            else:
                s = sy
                sx = math.copysign(abs(s), sx if sx != 0 else 1.0)
                sy = s

        tr = state.transform
        for i, (x0, y0, x1, y1) in tr.lines_snapshot:
            if 0 <= i < len(scene.lines):
                nx0, ny0 = scale_point_xy_i(x0, y0, px, py, sx, sy)
                nx1, ny1 = scale_point_xy_i(x1, y1, px, py, sx, sy)
                scene.lines[i].p0.x, scene.lines[i].p0.y = nx0, ny0
                scene.lines[i].p1.x, scene.lines[i].p1.y = nx1, ny1

        for i, (cx0, cy0, r0) in tr.circles_snapshot:
            if 0 <= i < len(scene.circles):
                ncx, ncy = scale_point_xy_i(cx0, cy0, px, py, sx, sy)
                scene.circles[i].c.x, scene.circles[i].c.y = ncx, ncy
                sr = abs(sx) if uniform else max(abs(sx), abs(sy))
                scene.circles[i].r = max(0, int(round(r0 * sr)))

        state.status = f"Scale: sx={sx:.2f} sy={sy:.2f}"
        redraw_canvas_from_scene(canvas, scene)

    def _apply_rotate(self, cpos: tuple[int, int], *, state: AppState, scene: Scene, canvas: pygame.Surface) -> None:
        if self._mode != "rotating" or self._pivot is None:
            return
        cx, cy = self._pivot
        vx, vy = cpos[0] - cx, cpos[1] - cy
        cur_angle = math.atan2(vy, vx) if (vx or vy) else self._anchor_angle
        theta = cur_angle - self._anchor_angle

        # Snap with Shift
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_SHIFT:
            snap = math.radians(C.SNAP_ANGLE_DEG)
            if snap > 0:
                theta = round(theta / snap) * snap

        tr = state.transform
        for i, (x0, y0, x1, y1) in tr.lines_snapshot:
            if 0 <= i < len(scene.lines):
                nx0, ny0 = rotate_point_i(x0, y0, cx, cy, theta)
                nx1, ny1 = rotate_point_i(x1, y1, cx, cy, theta)
                scene.lines[i].p0.x, scene.lines[i].p0.y = nx0, ny0
                scene.lines[i].p1.x, scene.lines[i].p1.y = nx1, ny1

        for i, (cx0, cy0, r0) in tr.circles_snapshot:
            if 0 <= i < len(scene.circles):
                ncx, ncy = rotate_point_i(cx0, cy0, cx, cy, theta)
                scene.circles[i].c.x, scene.circles[i].c.y = ncx, ncy
                scene.circles[i].r = r0

        deg = math.degrees(theta)
        state.status = f"Rotate: {deg:+.1f}°"
        redraw_canvas_from_scene(canvas, scene)

    # ------------ hover cursor updates ------------

    def _update_hover_cursor(
        self,
        cpos: tuple[int, int] | None,
        *,
        state: AppState,
        scene: Scene,
    ) -> None:
        """Set cursor based on hover location when idle (not dragging/selecting)."""
        if cpos is None:
            _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            return

        # If we're currently dragging, keep the respective cursor
        if self._mode == "moving":
            _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
            return
        if self._mode == "scaling" and self._handle:
            _set_cursor(_cursor_for_handle(self._handle))
            return
        if self._mode == "rotating":
            _set_cursor(pygame.SYSTEM_CURSOR_HAND)
            return

        # Otherwise, determine hover based on selection bbox & handles
        bx = _selection_bbox(scene, state)
        if not bx:
            _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            return

        h = _hit_test_handle(bx, cpos)
        if h:
            _set_cursor(_cursor_for_handle(h))
            return

        if bx.collidepoint(cpos) and (state.selection.selected_lines or state.selection.selected_circles):
            _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
        else:
            _set_cursor(pygame.SYSTEM_CURSOR_ARROW)

    # ---------------- Protocol entry ----------------

    def handle_canvas_event(
        self,
        ev: pygame.event.Event,
        cpos: tuple[int, int] | None,
        *,
        state: AppState,
        scene: Scene,
        canvas: pygame.Surface,
    ) -> None:
        sel = state.selection
        tr = state.transform

        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
            bx = _selection_bbox(scene, state)
            # Try handles first (only when we have a bbox)
            if bx:
                h = _hit_test_handle(bx, cpos)
                if h in ("nw", "n", "ne", "e", "se", "s", "sw", "w"):
                    self._begin_scale(h, cpos, state, scene)
                    return
                elif h == "rot":
                    self._begin_rotate(cpos, state, scene)
                    return

            # Inside-bbox move?
            if bx and bx.collidepoint(cpos) and (sel.selected_lines or sel.selected_circles):
                self._begin_move(cpos, state, scene)
                return

            # Else: start rubber-band selection
            sel.selecting = True
            sel.anchor = cpos
            sel.current = cpos
            state.status = "Selecting…"
            self._mode = "selecting"
            _set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)

        elif ev.type == pygame.MOUSEMOTION:
            if cpos and sel.selecting and sel.anchor:
                sel.current = cpos
                # keep crosshair while selecting
                _set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
            elif cpos and self._mode == "moving":
                self._apply_move(cpos, state=state, scene=scene, canvas=canvas)
                _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
            elif cpos and self._mode == "scaling":
                self._apply_scale(cpos, state=state, scene=scene, canvas=canvas)
                if self._handle:
                    _set_cursor(_cursor_for_handle(self._handle))
            elif cpos and self._mode == "rotating":
                self._apply_rotate(cpos, state=state, scene=scene, canvas=canvas)
                _set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                # idle hover update
                self._update_hover_cursor(cpos, state=state, scene=scene)

        elif ev.type == pygame.MOUSEBUTTONUP:
            # Finish selection
            if sel.selecting:
                sel.selecting = False
                a, b = sel.anchor, sel.current
                if a and b:
                    l, t, w, h = rect_from_points(a, b)
                    L, T, R, B = l, t, l + w, t + h

                    sel.selected_lines.clear()
                    sel.selected_circles.clear()

                    for i, ln in enumerate(scene.lines):
                        if (L <= ln.p0.x <= R and T <= ln.p0.y <= B) or (
                            L <= ln.p1.x <= R and T <= ln.p1.y <= B
                        ):
                            sel.selected_lines.add(i)
                    for i, c in enumerate(scene.circles):
                        if L <= c.c.x <= R and T <= c.c.y <= B:
                            sel.selected_circles.add(i)

                    state.status = f"Selected {len(sel.selected_lines)} lines, {len(sel.selected_circles)} circles"

                sel.anchor = None
                sel.current = None
                self._mode = None
                # After selection ends, update cursor based on hover
                self._update_hover_cursor(cpos, state=state, scene=scene)

            # Finish move/scale/rotate
            if tr.dragging or self._mode in ("moving", "scaling", "rotating"):
                tr.reset()
                self._mode = None
                self._handle = None
                self._bbox0 = None
                self._pivot = None
                self._h0 = None
                self._anchor_angle = 0.0
                redraw_canvas_from_scene(canvas, scene)
                # After gesture ends, update cursor based on hover
                self._update_hover_cursor(cpos, state=state, scene=scene)
