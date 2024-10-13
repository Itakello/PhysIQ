from dataclasses import dataclass, field

import pymunk

from ..config import config


@dataclass
class BaseShape:
    color: tuple
    position: tuple
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
        self.body.position = self.position
        self.shape = self.create_shape()
        self.shape.density = config.DEFAULT_DENSITY
        self.shape.friction = config.DEFAULT_FRICTION
        self.shape.elasticity = config.DEFAULT_RESTITUTION
        self.shape.color = self.color

    def calculate_moment(self) -> float:
        # This method should be overridden by subclasses
        raise NotImplementedError("Subclasses must implement calculate_moment method")

    def create_shape(self) -> pymunk.Shape:
        raise NotImplementedError("Subclasses must implement create_shape method")

    def add_to_space(self, space: pymunk.Space) -> None:
        space.add(self.body, self.shape)
