from dataclasses import dataclass
from typing import Literal

import pygame
import pymunk

from .base_manager import BaseManager


def begin(arbiter: pymunk.Arbiter, space: pymunk.Space, data: dict) -> Literal[True]:
    data["log"] = {
        "begin": 1,
        "pre_solve": 0,
        "separate": 0,
    }
    return True


def pre_solve(
    arbiter: pymunk.Arbiter, space: pymunk.Space, data: dict
) -> Literal[True]:
    print("Touching")
    data["log"]["pre_solve"] += 1
    return True


def separate(arbiter: pymunk.Arbiter, space: pymunk.Space, data: dict) -> None:
    print("Separate")
    data["log"]["separate"] += 1
    pass


@dataclass
class CollisionManager(BaseManager):
    handler: pymunk.CollisionHandler | None = None

    def setup_collision_handler(self, handler: pymunk.CollisionHandler) -> None:
        self.handler = handler
        self.handler.data["log"] = {"begin": 0, "pre_solve": 0, "separate": 0}
        self.handler.begin = begin
        self.handler.pre_solve = pre_solve
        self.handler.separate = separate
