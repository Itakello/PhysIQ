from dataclasses import dataclass, field

import pygame

from ..classes.shapes.base_shape import BaseShape
from ..classes.space import CustomSpace
from .base_m import BaseManager


@dataclass
class SpaceManager(BaseManager):
    custom_space: CustomSpace = field(init=False, default=CustomSpace())

    def link_screen(self, screen: pygame.Surface) -> None:
        self.custom_space.setup_draw_options(screen)

    def add_shapes(self, shapes: list[BaseShape]) -> None:
        self.custom_space.add_shapes(shapes)
