import math
from dataclasses import dataclass

import pymunk

from .base_shape import BaseShape


@dataclass(kw_only=True)
class Compound(BaseShape):
    angle: float = 0.0
    shape_data: dict

    def __post_init__(self) -> None:
        super().__post_init__()
        # add 180 degrees to the angle
        self.body.angle = math.pi - self.angle

    def calculate_moment(self) -> float:
        # Calculate the moment of inertia for a single shape
        return pymunk.moment_for_poly(self.mass, self.shape_data["vertices"])

    def _get_shape(self) -> pymunk.Shape:
        return pymunk.Poly(self.body, self.shape_data["vertices"])
