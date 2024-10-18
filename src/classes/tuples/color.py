from dataclasses import dataclass

from .base_tuple import BaseTuple


@dataclass(frozen=True)
class Color(BaseTuple):
    r: int
    g: int
    b: int
    a: int
