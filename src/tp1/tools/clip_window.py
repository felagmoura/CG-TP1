from __future__ import annotations

import pygame

from .. import config as C
from ..render.renderer import redraw_canvas_from_scene
from ..scene.scene import Scene
from ..state import AppState, Mode
from ..utils.geom import bbox_handles, clamp_rect_to_canvas, resize_rect_from_handle

# -------- Cursor helpers (same pattern used elsewhere) --------

_last_cursor_const: int | None = None

def _set_cursor(system_cursor_const: int) -> None:
    global _last_cursor_const
    if _last_cursor_const == system_cursor_const:
        return
    try:
        pygame.mouse.set_cursor(system_cursor_const)  # type: ignore[arg-type]
        _last_cursor_const = system_cursor_const
        return
    except Exception:
        pass
    try:
        pygame.mouse.set_cursor(pygame.cursors.Cursor(system_cursor_const))
        _last_cursor_const = system_cursor_const
    except Exception:
        pass


def _cursor_for_handle(handle: str) -> int:
    if handle in ("n", "s"):
        return pygame.SYSTEM_CURSOR_SIZENS
    if handle in ("e", "w"):
        return pygame.SYSTEM_CURSOR_SIZEWE
    if handle in ("ne", "sw"):
        return pygame.SYSTEM_CURSOR_SIZENESW
    if handle in ("nw", "se"):
        return pygame.SYSTEM_CURSOR_SIZENWSE
    return pygame.SYSTEM_CURSOR_ARROW


# -------- Local hit-testing for the 8 clip handles --------

def _hit_test_clip_handle(bbox: pygame.Rect, mouse_canvas: tuple[int, int]) -> str | None:
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


class ClipWindowTool:
    """
    Phase 5: creation + hover UX + MOVE + RESIZE + keyboard polish
      - Delete/Backspace: clear the clip window
      - Arrow keys: nudge by 1px (Shift = 10px)
      - Idle status shows rect metrics (x,y,w,h)
    """

    # gesture state
    _mode: str | None = None          # "creating" | "moving" | "resizing" | None
    _anchor: tuple[int, int] | None = None
    _rect0: tuple[int, int, int, int] | None = None  # snapshot at mouse-down
    _handle: str | None = None
    _keep_aspect: bool = False
    _from_center: bool = False

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Clip mode: drag to create; drag inside to move; handles to resize; Del to clear; Arrows to nudge"
        _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        self._mode = None
        self._anchor = None
        self._rect0 = None
        self._handle = None
        self._keep_aspect = False
        self._from_center = False

    def exit(self, state: AppState, scene: Scene) -> None:
        state.status = ""
        _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        self._mode = None
        self._anchor = None
        self._rect0 = None
        self._handle = None
        self._keep_aspect = False
        self._from_center = False

    def _set_idle_status(self, state: AppState) -> None:
        """Show x,y,w,h when we have a window and we're not dragging/creating."""
        if state.clip.window and self._mode is None and not state.clip.setting:
            l, t, w, h = state.clip.window
            state.status = f"Clip: x={l}, y={t}, w={w}, h={h}"

    def handle_canvas_event(
        self,
        ev: pygame.event.Event,
        cpos: tuple[int, int] | None,
        *,
        state: AppState,
        scene: Scene,
        canvas: pygame.Surface,
    ) -> None:
        if state.mode != Mode.CLIP_WINDOW:
            return

        # ---------- KEYBOARD: Delete clears; arrows nudge ----------
        if ev.type == pygame.KEYDOWN:
            # Only act when not in a mouse drag/creation (to avoid conflicts)
            if self._mode is None and not state.clip.setting:
                # Delete / Backspace → clear window
                if ev.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    if state.clip.window:
                        state.clip.window = None
                        state.status = "Clip window cleared"
                    return
                # Arrow keys → nudge window
                if state.clip.window and ev.key in (
                    pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN
                ):
                    step = C.CLIP_NUDGE_STEP
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        step = C.CLIP_NUDGE_STEP_FAST

                    dx = (-step if ev.key == pygame.K_LEFT else step if ev.key == pygame.K_RIGHT else 0)
                    dy = (-step if ev.key == pygame.K_UP   else step if ev.key == pygame.K_DOWN  else 0)

                    l, t, w, h = state.clip.window
                    state.clip.window = clamp_rect_to_canvas((l + dx, t + dy, w, h), C.CANVAS_W, C.CANVAS_H)
                    l, t, w, h = state.clip.window
                    state.status = f"Nudge: x={l}, y={t}, w={w}, h={h}"
                    return

        # --------------- LIVE MOVE ---------------
        if ev.type == pygame.MOUSEMOTION and self._mode == "moving" and cpos and self._anchor and self._rect0:
            dx = cpos[0] - self._anchor[0]
            dy = cpos[1] - self._anchor[1]
            l0, t0, w0, h0 = self._rect0
            new_rect = (l0 + dx, t0 + dy, w0, h0)
            state.clip.window = clamp_rect_to_canvas(new_rect, C.CANVAS_W, C.CANVAS_H)
            state.status = f"Move: ({dx}, {dy})"
            _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
            redraw_canvas_from_scene(canvas, scene, state)
            return

        # --------------- LIVE RESIZE ---------------
        if ev.type == pygame.MOUSEMOTION and self._mode == "resizing" and cpos and self._rect0 and self._handle:
            new_rect = resize_rect_from_handle(
                self._rect0,
                self._handle,
                cpos,
                keep_aspect=self._keep_aspect,
                from_center=self._from_center,
                min_w=C.CLIP_MIN_W,
                min_h=C.CLIP_MIN_H,
                bounds=(C.CANVAS_W, C.CANVAS_H),
            )
            state.clip.window = new_rect
            l, t, w, h = new_rect
            state.status = f"Resize: {w}×{h}"
            _set_cursor(_cursor_for_handle(self._handle))
            redraw_canvas_from_scene(canvas, scene, state)
            return

        # --------------- HOVER cursors (idle) ---------------
        if ev.type == pygame.MOUSEMOTION:
            if cpos is None:
                _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return

            if state.clip.window and self._mode is None and not state.clip.setting:
                l, t, w, h = state.clip.window
                bbox = pygame.Rect(l, t, w, h)

                hkey = _hit_test_clip_handle(bbox, cpos)
                if hkey:
                    _set_cursor(_cursor_for_handle(hkey))
                    self._set_idle_status(state)
                    return

                if bbox.collidepoint(cpos):
                    _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                    self._set_idle_status(state)
                    return

            _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            self._set_idle_status(state)

        # --------------- BEGIN gestures ---------------
        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
            # Prefer RESIZE if we pressed on a handle
            if state.clip.window:
                l, t, w, h = state.clip.window
                bbox = pygame.Rect(l, t, w, h)
                hkey = _hit_test_clip_handle(bbox, cpos)
                if hkey:
                    self._mode = "resizing"
                    self._handle = hkey
                    self._rect0 = state.clip.window
                    mods = pygame.key.get_mods()
                    self._keep_aspect = bool(mods & pygame.KMOD_SHIFT)
                    self._from_center = bool(mods & pygame.KMOD_ALT)
                    state.status = "Resizing clip window…"
                    _set_cursor(_cursor_for_handle(hkey))
                    return

                # Else: MOVING if inside
                if bbox.collidepoint(cpos):
                    self._mode = "moving"
                    self._anchor = cpos
                    self._rect0 = state.clip.window
                    state.status = "Moving clip window…"
                    _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                    return

            # Else: CREATING
            state.clip.setting = True
            self._mode = "creating"
            state.clip.anchor = cpos
            state.clip.current = cpos
            _set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
            return

        # --------------- UPDATE creation drag ---------------
        if ev.type == pygame.MOUSEMOTION and cpos and state.clip.setting and self._mode == "creating":
            state.clip.current = cpos
            _set_cursor(pygame.SYSTEM_CURSOR_CROSSHAIR)
            return

        # --------------- END gestures ---------------
        if ev.type == pygame.MOUSEBUTTONUP:
            # Finish MOVE
            if self._mode == "moving":
                self._mode = None
                self._anchor = None
                self._rect0 = None
                state.status = "Clip window moved"
                return

            # Finish RESIZE
            if self._mode == "resizing":
                self._mode = None
                self._rect0 = None
                self._handle = None
                self._keep_aspect = False
                self._from_center = False
                state.status = "Clip window resized"
                return

            # Finish CREATE (same as before)
            if state.clip.setting and state.clip.anchor and state.clip.current:
                state.clip.setting = False
                (x0, y0) = state.clip.anchor
                (x1, y1) = state.clip.current
                left = min(x0, x1)
                top = min(y0, y1)
                w = max(1, abs(x1 - x0))
                h = max(1, abs(y1 - y0))
                state.clip.window = clamp_rect_to_canvas((left, top, w, h), C.CANVAS_W, C.CANVAS_H)
                state.clip.anchor = None
                state.clip.current = None
                self._mode = None
                _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return
