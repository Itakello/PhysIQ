from dataclasses import dataclass

import pymunk

from .base_shape import BaseShape


@dataclass(kw_only=True)
class Polygon(BaseShape):
    vertices: list[tuple[float, float]]
    angle: float = 0.0

    def calculate_moment(self) -> float:
        return pymunk.moment_for_poly(self.mass, self.vertices)

    def create_shapes(self) -> None:
        shape = pymunk.Poly(self.body, self.vertices)
        self.body.angle = -self.angle
        self.shapes.append(shape)
