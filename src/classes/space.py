from dataclasses import dataclass, field

import pygame
import pymunk
import pymunk.pygame_util
from pymunk.space_debug_draw_options import SpaceDebugColor
from pymunk.vec2d import Vec2d

from src.classes.shapes import BaseBody
from src.config import config

from .shapes.circle import Circle


class CustomDrawOptions(pymunk.pygame_util.DrawOptions):

    def draw_circle(
        self,
        pos: Vec2d,
        angle: float,
        radius: float,
        outline_color: SpaceDebugColor,
        fill_color: SpaceDebugColor,
    ) -> None:
        pygame.draw.circle(self.surface, fill_color, pos, int(radius))  # type: ignore


@dataclass
class CustomSpace(pymunk.Space):
    elapsed_time: float = field(init=False, default=0.0)
    _draw_options: CustomDrawOptions | None = field(init=False, default=None)

    @property
    def draw_options(self) -> CustomDrawOptions:
        if self._draw_options is None:
            raise RuntimeError("Screen must be linked before drawing")
        return self._draw_options

    def __post_init__(self) -> None:
        super().__init__()
        self.gravity = (0, config.DEFAULT_GRAVITY)
        self.iterations = config.SPACE_ITERATIONS

    def add_body(self, body: BaseBody) -> None:
        self.add(body.body, *body.shapes)

    def remove_body(self, body: BaseBody) -> None:
        self.remove(body.body, *body.shapes)

    def add_bodies(self, bodies: list[BaseBody]) -> None:
        for body in bodies:
            self.add_body(body)

    def link_screen(self, screen: pygame.Surface) -> None:
        self._draw_options = CustomDrawOptions(screen)
        self._draw_options.transform = pymunk.Transform.scaling(
            config.RESOLUTION_SCALE_FACTOR
        )
        self._draw_options.flags = pymunk.pygame_util.DrawOptions.DRAW_SHAPES

    def draw(self) -> None:
        self.debug_draw(self.draw_options)

    def get_collision_handler(self, config_data: dict) -> pymunk.CollisionHandler:
        return self.add_collision_handler(
            config_data["bodyId1"] + 1, config_data["bodyId2"] + 1
        )

    def check_collisions(self, circle: Circle) -> bool:
        # Query the space using both BB and shape query for more accurate results
        bb_collisions = self.bb_query(circle.get_bb(), circle.get_filter())

        # Filter out self-collisions
        collisions = [c for c in bb_collisions if c != circle.body]

        return len(collisions) > 0

    def clear(self) -> None:
        """Remove all bodies and constraints from the space."""
        for body in self.bodies:
            self.remove(body, *body.shapes)
        self.elapsed_time = 0.0
