from __future__ import annotations

import sys

import pygame

from . import config as C
from .events import EventDispatcher
from .render.renderer import clear_canvas, redraw_canvas_from_scene
from .scene.ops import apply_clipping_to_lines
from .scene.scene import Scene
from .state import AppState, Mode, make_initial_state
from .tools import (
    CircleTool,
    ClipWindowTool,
    LineTool,
    SelectTransformTool,
)
from .ui.overlay import draw_overlay
from .ui.sidebar import Sidebar


def _init_pygame() -> tuple[pygame.Surface, pygame.Surface, pygame.Surface, pygame.Surface]:
    pygame.init()
    pygame.display.set_caption("TP1 CG — Mode: IDLE")

    screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT))
    ui = pygame.Surface((C.UI_W, C.HEIGHT))
    canvas = pygame.Surface((C.CANVAS_W, C.CANVAS_H))
    overlay = pygame.Surface((C.CANVAS_W, C.CANVAS_H), pygame.SRCALPHA)

    screen.fill(C.BG)
    ui.fill(C.UI_BG)
    canvas.fill(C.CANVAS_BG)
    overlay.fill((0, 0, 0, 0))

    return screen, ui, canvas, overlay


def _init_fonts() -> tuple[pygame.font.Font, pygame.font.Font]:
    try:
        font = pygame.font.SysFont(C.FONT_FAMILY_MAIN, C.FONT_SIZE_MAIN, bold=True)
        small = pygame.font.SysFont(C.FONT_FAMILY_MAIN, C.FONT_SIZE_SMALL)
    except Exception:
        font = pygame.font.Font(None, C.FONT_SIZE_MAIN)
        small = pygame.font.Font(None, C.FONT_SIZE_SMALL)
    return font, small


def _wire_sidebar(
    sidebar: Sidebar,
    *,
    state: AppState,
    scene: Scene,
    canvas: pygame.Surface,
) -> None:

    def set_mode(mode: Mode) -> None:
        state.mode = mode
        state.status = f"{mode.name.title()}"

    def clear_all() -> None:
        scene.clear()
        clear_canvas(canvas)
        state.reset_all()
        state.mode = Mode.IDLE
        state.status = "Cleared"

    # Persistent preview callbacks for clipping
    def preview_clip_cs() -> None:
        state.mode = Mode.CLIP_WINDOW
        state.clip.preview_algo = "CS"
        state.status = "Preview: Cohen–Sutherland (Enter=apply, 0=off)"
        redraw_canvas_from_scene(canvas, scene, state)

    def preview_clip_lb() -> None:
        state.mode = Mode.CLIP_WINDOW
        state.clip.preview_algo = "LB"
        state.status = "Preview: Liang–Barsky (Enter=apply, 0=off)"
        redraw_canvas_from_scene(canvas, scene, state)

    # Buttons (order similar to original UI)
    sidebar.add_button("Select", lambda: set_mode(Mode.SELECT))

    sidebar.add_button("Line (DDA)", lambda: set_mode(Mode.LINE_DDA))
    sidebar.add_button("Line (Bresenham)", lambda: set_mode(Mode.LINE_BRESENHAM))
    sidebar.add_button("Circle (Bresenham)", lambda: set_mode(Mode.CIRCLE_BRESENHAM))

    sidebar.add_button("Set Clip Window", lambda: set_mode(Mode.CLIP_WINDOW))
    sidebar.add_button("Preview: Cohen–Suth.", preview_clip_cs)
    sidebar.add_button("Preview: Liang–Barsky", preview_clip_lb)

    sidebar.add_button("Clear Canvas", clear_all)


def main() -> None:
    screen, ui, canvas, overlay = _init_pygame()
    clock = pygame.time.Clock()
    font, font_small = _init_fonts()

    # Global runtime state
    state: AppState = make_initial_state()
    scene = Scene()
    sidebar = Sidebar()

    _wire_sidebar(sidebar, state=state, scene=scene, canvas=canvas)

    dispatcher = EventDispatcher(state=state, scene=scene, sidebar=sidebar, canvas=canvas)
    dispatcher.register_tools(
        {
            Mode.SELECT: SelectTransformTool(),
            Mode.LINE_DDA: LineTool("DDA"),
            Mode.LINE_BRESENHAM: LineTool("BRESENHAM"),
            Mode.CIRCLE_BRESENHAM: CircleTool(),
            Mode.CLIP_WINDOW: ClipWindowTool(),
            # IDLE has no tool
        }
    )

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.type == pygame.KEYDOWN:
                # --- keyboard shortcuts ---
                if ev.key == pygame.K_v:
                    state.mode = Mode.SELECT
                    state.status = "Select / Transform"

                elif ev.key == pygame.K_1:
                    # Always enable persistent preview (Cohen–Sutherland)
                    state.mode = Mode.CLIP_WINDOW
                    state.clip.preview_algo = "CS"
                    state.status = "Preview: Cohen–Sutherland (Enter=apply, 0=off)"
                    redraw_canvas_from_scene(canvas, scene, state)

                elif ev.key == pygame.K_2:
                    # Always enable persistent preview (Liang–Barsky)
                    state.mode = Mode.CLIP_WINDOW
                    state.clip.preview_algo = "LB"
                    state.status = "Preview: Liang–Barsky (Enter=apply, 0=off)"
                    redraw_canvas_from_scene(canvas, scene, state)

                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    # Apply current preview destructively
                    if state.clip.window and state.clip.preview_algo:
                        rect = pygame.Rect(*state.clip.window)
                        target = state.selection.selected_lines or None
                        kept, removed = apply_clipping_to_lines(
                            scene, rect, state.clip.preview_algo, target
                        )
                        state.status = f"Applied preview ({state.clip.preview_algo}): kept {kept}, removed {removed}"
                        state.clip.preview_algo = None
                        redraw_canvas_from_scene(canvas, scene, state)

                elif ev.key == pygame.K_0:
                    # Turn preview off
                    if state.clip.preview_algo:
                        state.clip.preview_algo = None
                        state.status = "Preview off"
                        redraw_canvas_from_scene(canvas, scene, state)

            else:
                dispatcher.handle(ev)

        sidebar.draw(ui, font, font_small, state)
        draw_overlay(overlay, scene, state)

        screen.fill(C.BG)
        screen.blit(ui, (0, 0))
        screen.blit(canvas, (C.UI_W, 0))
        screen.blit(overlay, (C.UI_W, 0))

        pygame.display.set_caption(f"TP1 CG — Mode: {state.mode.name}")
        pygame.display.flip()
        clock.tick(C.FPS)

    pygame.quit()
    sys.exit(0)
