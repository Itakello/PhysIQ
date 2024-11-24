from dataclasses import dataclass

import pygame

from ..config import const
from .base_manager import BaseManager


@dataclass
class SurfaceManager(BaseManager):
    _screen: pygame.Surface | None = None
    _sim_surface: pygame.Surface | None = None

    @property
    def screen(self) -> pygame.Surface:
        if not self._screen:
            raise ValueError("Screen surface not created.")
        return self._screen

    @property
    def sim_surface(self) -> pygame.Surface:
        if not self._sim_surface:
            raise ValueError("Simulation surface not created.")
        return self._sim_surface

    def create_surfaces(self) -> None:
        self._screen = pygame.display.set_mode(
            [dim * const.SCREEN_SCALE_FACTOR for dim in const.SCENE_DIMENSIONS]
        )
        self._sim_surface = pygame.Surface(
            [dim * const.RESOLUTION_SCALE_FACTOR for dim in const.SCENE_DIMENSIONS]
        )

    def clear_sim_surface(self) -> None:
        self.sim_surface.fill((255, 255, 255))

    def scale_and_display(self) -> None:
        pygame.transform.smoothscale(
            self.sim_surface, self.screen.get_size(), self.screen
        )
        pygame.display.flip()

    def get_snapshot(self) -> pygame.Surface:
        return self.sim_surface.copy()
