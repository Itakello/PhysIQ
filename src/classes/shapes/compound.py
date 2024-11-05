import math
from dataclasses import dataclass, field

import pymunk

from .base_shape import BaseShape


@dataclass(kw_only=True)
class Compound(BaseShape):
    angle: float = 0.0
    shapes_data: list[dict]
    vertices_list: list[list[tuple[float, float]]] = field(
        init=False, default_factory=list
    )

    def __post_init__(self) -> None:
        # Ensure we have valid shapes
        for shape in self.shapes_data:
            assert shape["type"] == "polygon", "All shapes should be polygons"
            self.vertices_list.append(shape["vertices"])

        super().__post_init__()
        # Ensure mass is positive
        if self.mass <= 0:
            self.mass = 1.0

        # add 180 degrees to the angle
        self.body.angle = math.pi - self.angle

    def calculate_moment(self) -> float:
        total_moment = 0.0
        for vertices in self.vertices_list:
            total_moment += pymunk.moment_for_poly(
                self.mass / len(self.vertices_list), vertices
            )
        return total_moment

    def get_shapes(self) -> list[pymunk.Shape]:
        return [pymunk.Poly(self.body, vertices) for vertices in self.vertices_list]
