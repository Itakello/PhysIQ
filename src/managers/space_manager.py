from dataclasses import dataclass, field

import pygame
import pymunk

from ..classes.shapes.base_shape import BaseShape
from ..classes.shapes.circle import Circle
from ..classes.space import CustomSpace
from .base_manager import BaseManager


@dataclass
class SpaceManager(BaseManager):
    custom_space: CustomSpace = field(init=False, default_factory=CustomSpace)

    def link_screen(self, screen: pygame.Surface) -> None:
        self.custom_space.setup_draw_options(screen)

    def add_shapes(self, shapes: list[BaseShape]) -> None:
        self.custom_space.add_shapes(shapes)

    def check_collisions(self, circle: Circle) -> bool:
        """
        Check if the given shape would collide with any existing shapes in the space.
        Returns True if there is a collision, False otherwise.
        """

        # Query the space using both BB and shape query for more accurate results
        bb_collisions = self.custom_space.space.bb_query(
            circle.get_bb(), circle.get_filter()
        )

        # Filter out self-collisions
        collisions = [c for c in bb_collisions if c != circle.body]

        return len(collisions) > 0

    def clear_space(self) -> None:
        self.custom_space = CustomSpace()

    def get_collision_handler(self, config_data: dict) -> pymunk.CollisionHandler:
        return self.custom_space.get_collision_handler(
            config_data["bodyId1"], config_data["bodyId2"]
        )
