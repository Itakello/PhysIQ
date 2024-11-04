from dataclasses import dataclass, field

import pygame

from ..classes.shapes.base_shape import BaseShape
from ..classes.space import CustomSpace
from .base_manager import BaseManager


@dataclass
class SpaceManager(BaseManager):
    custom_space: CustomSpace = field(init=False, default_factory=CustomSpace)

    def link_screen(self, screen: pygame.Surface) -> None:
        self.custom_space.setup_draw_options(screen)

    def add_shapes(self, shapes: list[BaseShape]) -> None:
        self.custom_space.add_shapes(shapes)

    def check_shape_collision(self, shape: BaseShape) -> bool:
        """
        Check if the given shape would collide with any existing shapes in the space.
        Returns True if there is a collision, False otherwise.
        """

        # Query the space using both BB and shape query for more accurate results
        bb_collisions = self.custom_space.space.bb_query(
            shape.get_bb(), shape.get_filter()
        )

        # Filter out self-collisions
        collisions = [c for c in bb_collisions if c != shape.body]

        return len(collisions) > 0

    def clear_space(self) -> None:
        self.custom_space = CustomSpace()
