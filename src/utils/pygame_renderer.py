from dataclasses import dataclass

import pygame
from Box2D import b2Shape, b2World
from loguru import logger

from ..managers.base_manager import BaseManager
from .const import RESOLUTION_SCALE_FACTOR, SCENE_DIMENSIONS, SCREEN_SCALE_FACTOR


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
        x = world_point[0] * SCALE + SCENE_DIMENSIONS[0] / 2
        y = SCENE_DIMENSIONS[1] / 2 - world_point[1] * SCALE
        return (x, y)

    def render(self, world: b2World) -> bool:
        """Render the entire Box2D world. Returns False if user closed the window."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        self.screen.fill((255, 255, 255))  # White background

        # Draw each body's fixtures
        for body in world.bodies:
            for fixture in body.fixtures:
                shape = fixture.shape

                # Check if the fixture is marked "target"
                if hasattr(fixture.userData, "get") and fixture.userData.get("target"):
                    color = (255, 0, 0)  # red
                else:
                    color = (0, 0, 0)  # black

                # Distinguish between shape types
                if shape.type == b2Shape.e_circle:
                    # circle
                    circle_shape = fixture.shape
                    # Box2D circle has a 'radius' and a 'p' (the circle center relative to the body's origin)
                    circle_center = body.transform * circle_shape.pos
                    center = self._to_pygame(circle_center)
                    radius = int(circle_shape.radius * SCALE)
                    pygame.draw.circle(self.screen, color, center, radius, 2)

                elif shape.type == b2Shape.e_polygon:
                    # polygon
                    polygon_shape = fixture.shape
                    vertices = [body.transform * v for v in polygon_shape.vertices]
                    vertices = [self._to_pygame(v) for v in vertices]
                    pygame.draw.polygon(self.screen, color, vertices, 2)

                else:
                    # For edge shapes, chain shapes, etc. You can handle them similarly:
                    # if shape.type == b2Shape.e_edge, or b2Shape.e_chain, ...
                    # or just skip them for now.
                    pass

        pygame.display.flip()
        self.clock.tick(60)
        return True

    def quit(self):
        pygame.quit()
