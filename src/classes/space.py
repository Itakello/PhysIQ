from dataclasses import dataclass, field

import pygame
import pymunk
import pymunk.pygame_util

from src.classes.shapes import BaseShape
from src.config import config


@dataclass
class CustomSpace:
    gravity: tuple[float, float] = (0, config.DEFAULT_GRAVITY)
    iterations: int = 10
    shapes: list[BaseShape] = field(default_factory=list)
    space: pymunk.Space = field(init=False)
    draw_options: pymunk.pygame_util.DrawOptions = field(init=False)

    def __post_init__(self) -> None:
        self.space = pymunk.Space()
        self.space.gravity = self.gravity
        self.space.iterations = self.iterations

    def add_shape(self, shape: BaseShape) -> None:
        shape.add_to_space(self.space)

    def add_shapes(self, shapes: list[BaseShape]) -> None:
        for shape in shapes:
            self.add_shape(shape)

    def setup_draw_options(self, screen: pygame.Surface) -> None:
        self.draw_options = pymunk.pygame_util.DrawOptions(screen)
        self.draw_options.transform = pymunk.Transform.scaling(
            config.RESOLUTION_SCALE_FACTOR
        )

    def step(self, dt: float) -> None:
        self.space.step(dt)

    def draw(self) -> None:
        self.space.debug_draw(self.draw_options)
