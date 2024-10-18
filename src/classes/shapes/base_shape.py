from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pymunk
from itakello_logging import ItakelloLogging

from ...config import config
from ..tuples import Color, Position

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class BaseShape(ABC):
    color: Color
    position: Position
    body_type: int
    mass: float = 1.0
    body: pymunk.Body = field(init=False)
    shapes: list[pymunk.Shape] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        if self.body_type == 0:
            self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else:
            self.body = pymunk.Body(
                mass=self.mass,
                moment=self.calculate_moment(),
                body_type=pymunk.Body.DYNAMIC,
            )
        self.body.position = self.position.to_tuple()
        self.create_shapes()
        for shape in self.shapes:
            shape.density = config.DEFAULT_DENSITY
            shape.friction = config.DEFAULT_FRICTION
            shape.elasticity = config.DEFAULT_RESTITUTION
            shape.color = self.color.to_tuple()
        logger.debug(f"Created {self.__class__.__name__} shape")

    @abstractmethod
    def calculate_moment(self) -> float:
        raise NotImplementedError("Subclasses must implement calculate_moment method")

    @abstractmethod
    def create_shapes(self) -> None:
        raise NotImplementedError("Subclasses must implement create_shapes method")

    def add_to_space(self, space: pymunk.Space) -> None:
        space.add(self.body, *self.shapes)
