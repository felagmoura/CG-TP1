from __future__ import annotations

import pygame

from .. import config as C
from ..scene.scene import Scene
from ..state import AppState, Mode
from ..utils.geom import bbox_handles, clamp_rect_to_canvas

# -------- Cursor helpers (reuse style from SelectTransformTool) --------

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


# -------- Local hit-testing just for the 8 clip handles --------

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
    Phase 3: creation + hover UX + MOVE gesture.
      - Drag on empty area: create window (same as before).
      - Drag inside existing window: move it (clamped to canvas).
      - Handles are still visual-only; resizing comes next phase.
    """

    # gesture state
    _mode: str | None = None          # "creating" | "moving" | None
    _anchor: tuple[int, int] | None = None
    _rect0: tuple[int, int, int, int] | None = None  # snapshot at mouse-down

    def enter(self, state: AppState, scene: Scene) -> None:
        state.status = "Clip mode: drag to create; drag inside to move"
        _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        self._mode = None
        self._anchor = None
        self._rect0 = None

    def exit(self, state: AppState, scene: Scene) -> None:
        state.status = ""
        _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        self._mode = None
        self._anchor = None
        self._rect0 = None

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

        # --------------- MOVE (live) ---------------
        if ev.type == pygame.MOUSEMOTION and self._mode == "moving" and cpos and self._anchor and self._rect0:
            dx = cpos[0] - self._anchor[0]
            dy = cpos[1] - self._anchor[1]
            l0, t0, w0, h0 = self._rect0
            new_rect = (l0 + dx, t0 + dy, w0, h0)
            state.clip.window = clamp_rect_to_canvas(new_rect, C.CANVAS_W, C.CANVAS_H)
            state.status = f"Move: ({dx}, {dy})"
            _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
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
                    return

                if bbox.collidepoint(cpos):
                    _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                    return

            _set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        # --------------- BEGIN gestures ---------------
        if ev.type == pygame.MOUSEBUTTONDOWN and cpos:
            # If a window exists, prefer move when clicking inside (ignore handle mousedown in Phase 3)
            if state.clip.window:
                l, t, w, h = state.clip.window
                bbox = pygame.Rect(l, t, w, h)

                # if clicked on a handle, do nothing yet (Phase 4 will use this)
                if _hit_test_clip_handle(bbox, cpos):
                    # Optional: visual confirmation can be left to overlay hover highlight
                    return

                if bbox.collidepoint(cpos):
                    # Start MOVING
                    self._mode = "moving"
                    self._anchor = cpos
                    self._rect0 = state.clip.window
                    state.status = "Moving clip window…"
                    _set_cursor(pygame.SYSTEM_CURSOR_SIZEALL)
                    return

            # Else: begin CREATING
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
                # fall through to hover cursor update next motion
                return

            # Finish CREATE (same as before)
            if state.clip.setting and state.clip.anchor and state.clip.current:
                state.clip.setting = False
                (x0, y0) = state.clip.anchor
                (x1, y1) = state.clip.current
                left = min(x0, x1)
                top = min(y0, y1)
                w = abs(x1 - x0)
                h = abs(y1 - y0)
                if w >= 1 and h >= 1:
                    state.clip.window = clamp_rect_to_canvas((left, top, w, h), C.CANVAS_W, C.CANVAS_H)
                state.clip.anchor = None
                state.clip.current = None
                self._mode = None
                _set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                return
