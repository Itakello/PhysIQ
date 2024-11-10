from dataclasses import dataclass
from enum import Enum, auto


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
        RED = auto()
        GREEN = auto()
        AZURE = auto()
        PINK = auto()
        BLUE = auto()
        GREY = auto()
        BLACK = auto()
        # Add more predefined colors as needed

    _COLOR_VALUES = {
        Preset.RED: (243, 79, 70),
        Preset.GREEN: (107, 206, 187),
        Preset.AZURE: (27, 121, 242),
        Preset.PINK: (75, 74, 164),
        Preset.BLUE: (107, 206, 187),
        Preset.GREY: (185, 202, 210),
        Preset.BLACK: (0, 0, 0),
    }

    @classmethod
    def from_preset(cls, preset: Preset) -> "Color":
        return cls(*cls._COLOR_VALUES[preset])


if __file__ == "__main__":
    # Usage examples:
    black_color = Color.from_preset(Color.Preset.BLACK)
    custom_color = Color(100, 150, 200)
