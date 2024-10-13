from dataclasses import dataclass

import pymunk

from .base_shape import BaseShape

RADIUS_ADJUSTMENT = 0.5


@dataclass(kw_only=True)
class Circle(BaseShape):
    diameter: float

    def calculate_moment(self) -> float:
        return pymunk.moment_for_circle(
            self.mass, 0, self.diameter / 2 + RADIUS_ADJUSTMENT
        )

    def create_shape(self) -> pymunk.Shape:
        return pymunk.Circle(self.body, self.diameter / 2 + RADIUS_ADJUSTMENT)
