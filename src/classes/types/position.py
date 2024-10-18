from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    x: float
    y: float

    @property
    def x_y(self) -> tuple[float, float]:
        return (self.x, self.y)
