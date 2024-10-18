import math
from dataclasses import dataclass

import pymunk

from .base_shape import BaseShape


@dataclass(kw_only=True)
class Compound(BaseShape):
    angle: float = 0.0
    shapes_data: list[dict]

    def __post_init__(self) -> None:
        super().__post_init__()
        # add 180 degrees to the angle
        self.body.angle = math.pi - self.angle
        for shape in self.shapes_data:
            assert shape["type"] == "polygon", "All shapes should be polygons"

    def calculate_moment(self) -> float:
        moment = 0.0
        mass_per_shape = self.mass / len(self.shapes_data)
        for shape in self.shapes_data:
            moment += pymunk.moment_for_poly(mass_per_shape, shape["vertices"])
        return moment

    def create_shapes(self) -> None:
        for shape in self.shapes_data:
            poly = pymunk.Poly(self.body, shape["vertices"])
            self.shapes.append(poly)
