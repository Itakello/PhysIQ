from dataclasses import dataclass

import pymunk

from .base_shape import BaseBody


@dataclass(kw_only=True)
class Polygon(BaseBody):
    vertices: list[tuple[float, float]]
    angle: float = 0.0

    def calculate_moment(self) -> float:
        return pymunk.moment_for_poly(self.mass, self.vertices)

    def get_shapes(self) -> list[pymunk.Shape]:
        shape = pymunk.Poly(self.body, self.vertices)
        self.body.angle = -self.angle
        return [shape]
