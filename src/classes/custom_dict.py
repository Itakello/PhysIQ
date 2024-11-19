import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CustomDict(dict):
    file_name: str
    position: Path
    path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.position.mkdir(parents=True, exist_ok=True)
        self.path = self.position / self.file_name
        if self.path.exists():
            self.update(json.loads(self.path.read_text()))

    def save(self) -> None:
        self.path.write_text(json.dumps(self, indent=4))
