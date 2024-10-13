from dataclasses import dataclass

import pymunk

from .base_shape import BaseShape


@dataclass(kw_only=True)
class Rectangle(BaseShape):
    width: float
    height: float
    angle: float = 0.0

    def calculate_moment(self) -> float:
        return pymunk.moment_for_box(self.mass, (self.width, self.height))

    def create_shape(self) -> pymunk.Shape:
        return pymunk.Poly.create_box(self.body, (self.width, self.height))

    def __post_init__(self) -> None:
        super().__post_init__()
        self.body.angle = self.angle
