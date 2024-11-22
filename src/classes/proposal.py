import json
from dataclasses import dataclass
from pathlib import Path

import pygame

# from PIL import Image
from .shapes.circle import Circle


@dataclass
class Proposal:
    idx: int
    attempt: int
    bodies: list[Circle]
    start_screen: pygame.Surface | None
    end_screen: pygame.Surface | None
    good: bool

    def save(self, path: Path) -> None:
        config_root_filename = "good_proposal" if self.good else "bad_proposal"
        file_name = f"{config_root_filename}_{self.idx:03d}"
        # Save the json file
        data = {
            "bodies": [body.to_dict() for body in self.bodies],
            "attempt": self.attempt,
        }
        with (path / f"{file_name}.json").open("w") as f:
            f.write(json.dumps(data, indent=4))

        # Save the start screen
        if self.start_screen:
            pygame.image.save(self.start_screen, path / f"{file_name}_start.png")

        # Save the end screen
        if self.end_screen:
            pygame.image.save(self.end_screen, path / f"{file_name}_end.png")
