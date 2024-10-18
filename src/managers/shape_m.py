from dataclasses import dataclass, field

from itakello_logging import ItakelloLogging

from src.classes.shapes import BaseShape, Circle, Polygon
from src.classes.types import Color, Position
from src.config import config

from ..classes.shapes.compound import Compound
from .base_m import BaseManager

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class ShapeManager(BaseManager):
    shapes: list[BaseShape] = field(default_factory=list)

    def create_shape(self, shape_data: dict) -> BaseShape:
        color = config.COLORS[shape_data["color"]]
        position = Position(shape_data["position"][0], shape_data["position"][1])

        shape_type = shape_data["shapeType"]
        shape_creators = {
            0: self._create_polygon,
            1: self._create_circle,
            2: self._create_polygon,
            3: self._create_compound,
            4: self._create_compound,
        }

        creator = shape_creators.get(shape_type)
        if not creator:
            raise ValueError(f"Unsupported shape type: {shape_type}")

        shape = creator(shape_data, color, position)
        self.shapes.append(shape)
        return shape

    def _create_circle(
        self,
        shape_data: dict,
        color: Color,
        position: Position,
    ) -> Circle:
        return Circle(
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            diameter=shape_data["diameter"],
        )

    def _create_polygon(
        self, shape_data: dict, color: Color, position: Position
    ) -> Polygon:
        return Polygon(
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            vertices=shape_data["vertices"],
            angle=shape_data["angle"],
        )

    def _create_compound(
        self, shape_data: dict, color: Color, position: Position
    ) -> Compound:
        return Compound(
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            shapes_data=shape_data["shapes"],
            angle=shape_data["angle"],
        )

    def reset(self) -> None:
        self.shapes = []
        logger.debug("Shapes reset")
