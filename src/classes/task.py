import random
from dataclasses import dataclass, field
from typing import Literal

import pygame
import pymunk
from itakello_logging import ItakelloLogging

from ..config import config
from .shapes import BaseBody, Circle, Compound, Polygon
from .space import CustomSpace
from .types import Color, Position

logger = ItakelloLogging().get_logger(__name__)


def begin(arbiter, space, data) -> Literal[True]:
    shapes = tuple(sorted([arbiter.shapes[0], arbiter.shapes[1]], key=id))
    data["collisions"][shapes] = space.time
    logger.debug(f"Shapes {shapes} have started colliding.")
    return True


def pre_solve(arbiter, space, data) -> Literal[True]:
    shapes = tuple(sorted([arbiter.shapes[0], arbiter.shapes[1]], key=id))
    start_time = data["collisions"].get(shapes)
    if start_time is not None:
        elapsed_time = space.time - start_time
        if elapsed_time >= config.COLLISION_DURATION_THRESHOLD:
            print(
                f"Shapes {shapes} have been colliding for {elapsed_time:.2f} seconds."
            )
            del data["collisions"][shapes]
    return True


def separate(arbiter, space, data) -> None:
    shapes = tuple(sorted([arbiter.shapes[0], arbiter.shapes[1]], key=id))
    if shapes in data["collisions"]:
        logger.debug(f"Shapes {shapes} have stopped colliding.")
        del data["collisions"][shapes]


@dataclass
class Task:
    id: str
    category: str
    idx: str
    bodies_data: dict
    collision_pair_indices: tuple[int, int]
    space: CustomSpace = field(init=False, default_factory=CustomSpace)
    bodies: list[BaseBody] = field(init=False, default_factory=list)
    handler: pymunk.CollisionHandler = field(init=False)

    def __post_init__(self) -> None:
        self.bodies = [
            self.create_body(idx + 1, body) for idx, body in enumerate(self.bodies_data)
        ]
        self.space.add_bodies(self.bodies)
        self.handler = self.space.add_collision_handler(*self.collision_pair_indices)
        self._setup_collision_handler()

    def link_screen(self, screen: pygame.Surface) -> None:
        self.space.link_screen(screen)

    def create_body(self, idx: int, data: dict) -> BaseBody:
        color = Color.from_preset(Color.Preset(data["color"]))
        position = Position(data["position"][0], data["position"][1])
        shape_type = data["shapeType"]
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

        body = creator(idx, data, color, position)
        self.bodies.append(body)
        return body

    def _create_circle(
        self,
        idx: int,
        shape_data: dict,
        color: Color,
        position: Position,
    ) -> Circle:
        return Circle(
            idx=idx,
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            radius=shape_data["radius"],
        )

    def _create_polygon(
        self, idx: int, shape_data: dict, color: Color, position: Position
    ) -> Polygon:
        return Polygon(
            idx=idx,
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            vertices=shape_data["vertices"],
            angle=shape_data["angle"],
        )

    def _create_compound(
        self, idx: int, shape_data: dict, color: Color, position: Position
    ) -> Compound:
        return Compound(
            idx=idx,
            color=color,
            position=position,
            body_type=shape_data["bodyType"],
            shapes_data=shape_data["shapes"],
            angle=shape_data["angle"],
        )

    def reset(self) -> None:
        self.bodies = []
        logger.warning("Shapes reset")
        logger.warning("Shapes reset")
        logger.warning("Shapes reset")

    def __str__(self) -> str:
        return f"{self.id} - {self.idx}"

    def _setup_collision_handler(self) -> None:
        self.handler.data["collisions"] = {}
        self.handler.begin = begin
        self.handler.pre_solve = pre_solve
        self.handler.separate = separate
