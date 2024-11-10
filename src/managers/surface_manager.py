from dataclasses import dataclass

import pygame

from ..config import config
from .base_manager import BaseManager


@dataclass
class SurfaceManager(BaseManager):
    screen: pygame.Surface | None = None
    sim_surface: pygame.Surface | None = None

    def create_surfaces(self) -> None:
        self.screen = pygame.display.set_mode(
            [dim * config.SCREEN_SCALE_FACTOR for dim in config.SCENE_DIMENSIONS]
        )
        self.sim_surface = pygame.Surface(
            [dim * config.RESOLUTION_SCALE_FACTOR for dim in config.SCENE_DIMENSIONS]
        )

    def clear_sim_surface(self) -> None:
        if self.sim_surface:
            self.sim_surface.fill((255, 255, 255))

    def scale_and_display(self) -> None:
        if self.sim_surface and self.screen:
            pygame.transform.smoothscale(
                self.sim_surface, self.screen.get_size(), self.screen
            )
            pygame.display.flip()
