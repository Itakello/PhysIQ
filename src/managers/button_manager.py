from dataclasses import dataclass, field

import pygame

from ..classes.button import Button
from .base_manager import BaseManager


@dataclass
class ButtonManager(BaseManager):
    buttons: list[Button] = field(default_factory=list)

    def add_button(self, x: int, y: int, width: int, height: int, text: str) -> Button:
        button = Button(x, y, width, height, text)
        self.buttons.append(button)
        return button

    def clear_buttons(self) -> None:
        self.buttons.clear()

    """def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            for button in self.buttons:
                if button.rect.collidepoint(pos):
                    if button.on_click:
                        button.on_click()"""

    def draw(self, surface: pygame.Surface) -> None:
        for button in self.buttons:
            button.draw(surface)

    def get_button(self, index: int) -> Button | None:
        if 0 <= index < len(self.buttons):
            return self.buttons[index]
        return None
