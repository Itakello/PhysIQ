# File: /PhysIQ/src/utils/pygame_renderer.py

import pygame
from Box2D import b2Shape, b2World
from loguru import logger

from .const import RESOLUTION_SCALE_FACTOR, SCENE_DIMENSIONS, SCREEN_SCALE_FACTOR


class PygameRenderer:
    def __init__(self) -> None:
        """Initialize a fixed-size, non-resizable PyGame window."""
        pygame.init()
        self.screen = pygame.display.set_mode(
            (
                SCENE_DIMENSIONS[0] * SCREEN_SCALE_FACTOR,
                SCENE_DIMENSIONS[1] * SCREEN_SCALE_FACTOR,
            )
        )
        self.surface = pygame.Surface(
            (
                SCENE_DIMENSIONS[0] * RESOLUTION_SCALE_FACTOR,
                SCENE_DIMENSIONS[1] * RESOLUTION_SCALE_FACTOR,
            )
        )
        pygame.display.set_caption("PhysIQ Simulation")
        self.clock = pygame.time.Clock()
        logger.debug("Initialized PygameRenderer.")

    def world_to_screen(self, world_point) -> tuple[int, int]:
        """
        Convert Box2D coordinates to pixel coordinates.
        We flip y so that y=0 is at the bottom.
        """
        x = int(world_point[0] * RESOLUTION_SCALE_FACTOR)
        y = int((SCENE_DIMENSIONS[1] - world_point[1]) * RESOLUTION_SCALE_FACTOR)
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
                # Default black color
                color = (0, 0, 0)

                # If we stored color in fixture.userData, prefer that
                if fixture.userData and "color" in fixture.userData:
                    color = fixture.userData["color"]

                if shape.type == b2Shape.e_circle:
                    # Circle
                    circle_shape = fixture.shape
                    circle_center = body.transform * circle_shape.pos
                    center = self.world_to_screen(circle_center)
                    radius = int(circle_shape.radius * RESOLUTION_SCALE_FACTOR)

                    # Fill the circle with the fixture color
                    pygame.draw.circle(self.surface, color, center, radius, width=0)

                elif shape.type == b2Shape.e_polygon:
                    # Polygon or compound polygon fixture
                    polygon_shape = fixture.shape
                    vertices = [body.transform * v for v in polygon_shape.vertices]
                    screen_vertices = [self.world_to_screen(v) for v in vertices]

                    # Fill the polygon
                    pygame.draw.polygon(self.surface, color, screen_vertices, width=0)

                else:
                    # Could add e_edge or e_chain, etc.
                    pass

        # Scale the surface to the screen size and display it
        scaled_surface = pygame.transform.smoothscale(
            self.surface,
            (
                SCENE_DIMENSIONS[0] * SCREEN_SCALE_FACTOR,
                SCENE_DIMENSIONS[1] * SCREEN_SCALE_FACTOR,
            ),
        )
        self.screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        self.clock.tick(60)
        return True

    def quit(self):
        pygame.quit()
        logger.debug("Quit PygameRenderer.")
