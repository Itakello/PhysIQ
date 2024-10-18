from dataclasses import dataclass

from .base_tuple import BaseTuple


@dataclass(frozen=True)
class Position(BaseTuple):
    x: float
    y: float
