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

    def create_shapes(self) -> None:
        shape = pymunk.Poly.create_box(self.body, (self.width, self.height))
        self.body.angle = self.angle
        self.shapes.append(shape)
