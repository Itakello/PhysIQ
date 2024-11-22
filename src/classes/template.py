import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .task import Task


@dataclass
class Template:
    id: str
    category: str
    run_config: dict[str, Any]

    def __post_init__(self) -> None:
        self.path = Path(f"data/templates/{self.category}/{self.id}")
        self.tasks = [d.name for d in self.path.iterdir() if d.is_dir()]

    def get_first_iteration(self) -> Task:
        task_path = self.path / self.tasks[0]
        data = json.loads((task_path / "data.json").read_text())
        task = Task(
            id=self.id,
            category=self.category,
            idx=self.tasks[0],
            bodies_data=data["bodies"],
            collision_pair_indices=(
                data["relationship"]["bodyId1"] + 1,
                data["relationship"]["bodyId2"] + 1,
            ),
            path=task_path,
            run_config=self.run_config,
        )
        return task

    def get_iterations(self, limit: int = -1) -> list[Task]:
        assert limit >= -1
        if limit == -1:
            limit = len(self.tasks)
        tasks = []
        for task in self.tasks[:limit]:
            task_path = self.path / task
            data = json.loads((task_path / "data.json").read_text())
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
                    path=task_path,
                    run_config=self.run_config,
                )
            )
        return tasks
