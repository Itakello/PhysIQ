from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int
    a: int = 255

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    class Preset(Enum):
        RED = (243, 79, 70)
        GREEN = (24, 119, 242)
        AZURE = (27, 121, 242)
        PINK = (75, 74, 164)
        BLUE = (107, 206, 187)
        GREY = (185, 202, 210)
        BLACK = (0, 0, 0)
        # Add more predefined colors as needed

    @classmethod
    def from_preset(cls, preset: Preset) -> "Color":
        return cls(*preset.value)


# Usage examples:
black_color = Color.from_preset(Color.Preset.BLACK)
custom_color = Color(100, 150, 200)
