from dataclasses import dataclass

import pygame
from Box2D import b2Shape, b2World
from loguru import logger

from ..utils.const import RESOLUTION_SCALE_FACTOR, SCENE_DIMENSIONS, SCREEN_SCALE_FACTOR
from .base_manager import BaseManager


@dataclass
class PygameManager(BaseManager):
    screen_scale_factor: int = SCREEN_SCALE_FACTOR
    resolution_scale_factor: int = RESOLUTION_SCALE_FACTOR
    scene_dimensions: tuple[int, int] = SCENE_DIMENSIONS

    def __post_init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(
            tuple(x * self.screen_scale_factor for x in self.scene_dimensions)
        )
        self.surface = pygame.Surface(
            tuple(x * self.resolution_scale_factor for x in self.scene_dimensions)
        )
        pygame.display.set_caption("PhysIQ Simulation")
        self.clock = pygame.time.Clock()

    def _to_pygame(self, world_point: tuple[float, float]) -> tuple[float, float]:
        """Convert Box2D coordinates to pixel coordinates."""
        x = world_point[0] * self.resolution_scale_factor
        y = (SCENE_DIMENSIONS[1] - world_point[1]) * self.resolution_scale_factor
        return (x, y)

    def render(self, world: b2World) -> bool:
        """Render the entire Box2D world. Returns False if user closed the window."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        self.surface.fill((255, 255, 255))  # White background

        # Draw each body's fixtures
        for body in world.bodies:
            for fixture in body.fixtures:
                shape = fixture.shape

                color = fixture.userData.get("color", (0, 0, 0))

                # Distinguish between shape types
                if shape.type == b2Shape.e_circle:
                    # circle
                    circle_shape = fixture.shape
                    center = self._to_pygame(body.transform * circle_shape.pos)
                    pygame.draw.circle(
                        surface=self.surface,
                        color=color,
                        center=center,
                        radius=circle_shape.radius * self.resolution_scale_factor,
                        width=0,
                    )

                elif shape.type == b2Shape.e_polygon:
                    # polygon
                    polygon_shape = fixture.shape
                    vertices = [body.transform * v for v in polygon_shape.vertices]
                    vertices = [self._to_pygame(v) for v in vertices]
                    pygame.draw.polygon(
                        surface=self.surface, color=color, points=vertices, width=0
                    )

        scaled_surface = pygame.transform.smoothscale(
            self.surface,
            (
                self.scene_dimensions[0] * self.screen_scale_factor,
                self.scene_dimensions[1] * self.screen_scale_factor,
            ),
        )
        self.screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        self.clock.tick(60)
        return True

    def quit(self) -> None:
        pygame.quit()
