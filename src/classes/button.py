from dataclasses import dataclass, field

import pygame

from ..config.config import FONT_SIZE
from .types.color import Color


@dataclass
class Button:
    x: int
    y: int
    width: int
    height: int
    text: str
    color: Color = field(default=Color.from_preset(Color.Preset.GREY))
    font: pygame.font.Font = field(init=False)
    text_color: Color = field(
        default_factory=lambda: Color.from_preset(Color.Preset.BLACK)
    )
    rect: pygame.Rect = field(init=False)

    def __post_init__(self) -> None:
        self.font = pygame.font.Font(None, FONT_SIZE)
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, screen: pygame.Surface) -> None:
        pygame.draw.rect(screen, self.color.rgba, self.rect)
        text_surface = self.font.render(self.text, True, self.text_color.rgba)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, pos: tuple) -> bool:
        return self.rect.collidepoint(pos)
