import json
from dataclasses import dataclass
from pathlib import Path

from ..config import config
from .shapes.base_shape import BaseBody
from .task import Task


@dataclass
class Template:
    id: str
    category: str

    def __post_init__(self) -> None:
        self.path = Path(f"data/templates/{self.category}/{self.id}")
        self.tasks = [d.name for d in self.path.iterdir() if d.is_dir()]

    def get_first_iteration(self) -> Task:
        data = json.loads((self.path / self.tasks[0] / "data.json").read_text())
        return Task(
            id=self.id,
            category=self.category,
            idx=self.tasks[0],
            bodies_data=data["bodies"],
            collision_pair_indices=(
                data["relationship"]["bodyId1"] + 1,
                data["relationship"]["bodyId2"] + 1,
            ),
        )

    def get_all_iterations(self) -> list[Task]:
        tasks = []
        for task in self.tasks:
            data = json.loads((self.path / task / "data.json").read_text())
            tasks.append(
                Task(
                    id=self.id,
                    category=self.category,
                    idx=task,
                    bodies_data=data["bodies"],
                    collision_pair_indices=(
                        data["relationship"]["bodyId1"] + 1,
                        data["relationship"]["bodyId2"] + 1,
                    ),
                )
            )
        return tasks
