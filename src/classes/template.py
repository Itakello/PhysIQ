import json
from dataclasses import dataclass
from pathlib import Path

from config import config

from .shapes.base_shape import BaseBody
from .task import Task


@dataclass
class Template:
    id: str
    category: str

    def __post_init__(self) -> None:
        self.path = Path(f"data/{self.category}/{self.id}")
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

    def save_solutions(
        self, good_proposals: list[list[BaseBody]], bad_proposals: list[list[BaseBody]]
    ) -> None:
        solutions_path = self.path / "solutions"
        solutions_path.mkdir(parents=True, exist_ok=True)

        physical_constants_file = solutions_path / "physical_constants.json"
        new_group_name = "group_001"
        metadata = {
            "gravity": config.DEFAULT_GRAVITY,
            "density": config.DEFAULT_DENSITY,
            "friction": config.DEFAULT_FRICTION,
            "restitution": config.DEFAULT_RESTITUTION,
        }

        if not physical_constants_file.exists():
            physical_constants = {"groups": {"group_001": metadata}}
        else:
            physical_constants = json.loads(physical_constants_file.read_text())
            new_group_name = f"group_{str(int(max(physical_constants["groups"].keys()[6:])) + 1)}"
            physical_constants["groups"][new_group_name] = metadata

        with physical_constants_file.open("w") as f:
            json.dump(physical_constants, f, indent=4)
        solutions_data = {
            "good_proposals": [
                [body.to_dict() for body in proposal] for proposal in good_proposals
            ],
            "bad_proposals": [
                [body.to_dict() for body in proposal] for proposal in bad_proposals
            ],
        }

        with (solutions_path / "solutions.json").open("w") as f:
            json.dump(solutions_data, f, indent=4)
