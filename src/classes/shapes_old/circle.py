from dataclasses import dataclass

import pymunk

from .base_shape import BaseBody

RADIUS_ADJUSTMENT = 0.5


@dataclass(kw_only=True)
class Circle(BaseBody):
    radius: float

    def calculate_moment(self) -> float:
        return pymunk.moment_for_circle(self.mass, 0, self.radius + RADIUS_ADJUSTMENT)

    def get_shapes(self) -> list[pymunk.Shape]:
        return [pymunk.Circle(self.body, self.radius + RADIUS_ADJUSTMENT)]

    def get_bb(self) -> pymunk.BB:
        return self.shapes[0].cache_bb()

    def get_filter(self) -> pymunk.ShapeFilter:
        return self.shapes[0].filter

    def to_dict(self) -> dict:
        preset = self.color.get_preset()
        assert preset
        return {
            "position": self.position.x_y,
            "body_type": self.body_type,
            "angle": 0.0,
            "color": preset.value,
            "shapeType": 1,
            "radius": self.radius,
        }
