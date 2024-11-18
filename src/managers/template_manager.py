import json
from dataclasses import dataclass, field
from pathlib import Path

from ..classes.task import Task
from ..classes.template import Template
from ..config import config
from .base_manager import BaseManager


@dataclass
class TemplateManager(BaseManager):
    templates: dict[str, Template] = field(default_factory=dict)

    def __post_init__(self) -> None:
        data_path = Path("data/templates")
        categories = [d.name for d in data_path.iterdir() if d.is_dir()]
        for category in categories:
            levels = [d.name for d in (data_path / category).iterdir() if d.is_dir()]
            for level in levels:
                self.templates[level] = Template(id=level, category=category)

    def get_templates_first_tasks(self, starting_level: str = "00000") -> list[Task]:
        return [
            level.get_first_iteration()
            for name, level in self.templates.items()
            if name >= starting_level
        ]

    def get_templates_all_tasks(self) -> list[Task]:
        tasks = []
        for level in self.templates.values():
            tasks.extend(level.get_all_iterations())
        return tasks

    def add_configuration(self) -> str:
        data_path = Path("data")

        physical_configurations_file = data_path / "physical_configurations.json"
        metadata = {
            "gravity": config.DEFAULT_GRAVITY,
            "density": config.DEFAULT_DENSITY,
            "friction": config.DEFAULT_FRICTION,
            "restitution": config.DEFAULT_RESTITUTION,
        }
        new_group_name = "config_001"

        if physical_configurations_file.exists():
            physical_constants = json.loads(physical_configurations_file.read_text())
            new_group_name = f"config_{(int(max(physical_constants['configurations'].keys())[-3:]) + 1):03d}"
        else:
            physical_constants = {"configurations": {}}
        physical_constants["configurations"][new_group_name] = metadata

        with physical_configurations_file.open("w") as f:
            json.dump(physical_constants, f, indent=4)

        return new_group_name
