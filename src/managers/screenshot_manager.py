from pathlib import Path

import numpy as np
import pygame
from PIL import Image

from .base_manager import BaseManager


class ScreenshotManager(BaseManager):
    def __init__(self, subfolder: str = "") -> None:
        self.base_dir = Path("images")
        self.base_dir.mkdir(exist_ok=True)
        if subfolder:
            self.images_dir = self.base_dir / subfolder
            self.images_dir.mkdir(exist_ok=True)
        else:
            self.images_dir = self.base_dir

    @staticmethod
    def take_screenshot(screen: pygame.Surface) -> Image.Image:
        """Convert a pygame surface to PIL Image."""
        arr = pygame.surfarray.array3d(screen)
        arr = np.transpose(arr, (1, 0, 2))
        return Image.fromarray(arr)

    def save_screenshots(self, screenshots: list[Image.Image], filename: str) -> Path:
        """Save a list of screenshots to the configured directory with incremental filenames."""
        paths = []
        for i, screenshot in enumerate(screenshots, start=1):
            if len(screenshots) == 1:
                path = self.images_dir / f"{filename}.png"
            else:
                path = self.images_dir / filename
                path.mkdir(exist_ok=True)
                path = path / f"{i}.png"
            screenshot.save(path)
            paths.append(path)
        if len(screenshots) == 1:
            return paths[0]
        return self.images_dir / filename
