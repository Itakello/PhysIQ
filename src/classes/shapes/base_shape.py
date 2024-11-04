from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pymunk
from itakello_logging import ItakelloLogging

from ...config import config
from ..types import Color, Position

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class BaseShape(ABC):
    color: Color
    position: Position
    body_type: int
    mass: float = 1.0
    body: pymunk.Body = field(init=False)
    shape: pymunk.Shape = field(init=False)

    def __post_init__(self) -> None:
        if self.body_type == 0:
            self.body = pymunk.Body(body_type=pymunk.Body.STATIC)
        else:
            self.body = pymunk.Body(
                mass=self.mass,
                moment=self.calculate_moment(),
                body_type=pymunk.Body.DYNAMIC,
            )
        self.body.position = self.position.x_y
        self.shape = self._get_shape()
        self._set_defaults()
        logger.debug(f"Created {self.__class__.__name__} shape [{self.position}] ")

    @abstractmethod
    def calculate_moment(self) -> float:
        raise NotImplementedError("Subclasses must implement calculate_moment method")

    @abstractmethod
    def _get_shape(self) -> pymunk.Shape:
        raise NotImplementedError("Subclasses must implement create_shapes method")

    def _set_defaults(self) -> None:
        self.shape.density = config.DEFAULT_DENSITY
        self.shape.friction = config.DEFAULT_FRICTION
        self.shape.elasticity = config.DEFAULT_RESTITUTION
        self.shape.color = self.color.rgba

    def add_to_space(self, space: pymunk.Space) -> None:
        space.add(self.body, self.shape)

    def get_bb(self) -> pymunk.BB:
        return self.shape.cache_bb()

    def get_filter(self) -> pymunk.ShapeFilter:
        return self.shape.filter
