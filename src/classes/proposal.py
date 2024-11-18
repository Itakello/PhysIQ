import json
from dataclasses import dataclass
from pathlib import Path

import pygame

# from PIL import Image
from .shapes.circle import Circle


@dataclass
class Proposal:
    idx: int
    bodies: list[Circle]
    screen: pygame.Surface
    good: bool

    def save(self, path: Path) -> None:
        config_root_filename = "good_proposal" if self.good else "bad_proposal"
        file_name = f"{config_root_filename}_{self.idx:03d}"
        # Save the json file
        data = {
            "bodies": [body.to_dict() for body in self.bodies],
        }
        with (path / f"{file_name}.json").open("w") as f:
            f.write(json.dumps(data, indent=4))

        # Save the image file
        pygame.image.save(self.screen, path / f"{file_name}.png")
