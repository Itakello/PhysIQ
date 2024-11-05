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

    def get_shapes(self) -> list[pymunk.Shape]:
        return [pymunk.Circle(self.body, self.diameter / 2 + RADIUS_ADJUSTMENT)]

    def get_bb(self) -> pymunk.BB:
        return self.shapes[0].cache_bb()

    def get_filter(self) -> pymunk.ShapeFilter:
        return self.shapes[0].filter
