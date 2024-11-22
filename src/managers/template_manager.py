import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..classes.custom_dict import CustomDict
from ..classes.task import Task
from ..classes.template import Template
from ..config import config
from .base_manager import BaseManager


@dataclass
class TemplateManager(BaseManager):
    templates: dict[str, Template] = field(default_factory=dict)
    runs_configurations: CustomDict = field(init=False)

    def __post_init__(self) -> None:
        self.runs_configurations = CustomDict(
            file_name="runs_configuration.json", position=Path("data")
        )

    def load_templates(self, run_config_name: str) -> None:
        template_path = Path("data") / "templates"
        categories = [d.name for d in template_path.iterdir() if d.is_dir()]
        for category in categories:
            levels = [
                d.name for d in (template_path / category).iterdir() if d.is_dir()
            ]
            for level in levels:
                self.templates[level] = Template(
                    id=level,
                    category=category,
                    run_config=self.runs_configurations["runs"][run_config_name],
                )

    def get_templates_first_tasks(self, starting_level: str = "00000") -> list[Task]:
        return [
            level.get_first_iteration()
            for name, level in self.templates.items()
            if name >= starting_level
        ]

    def get_templates_tasks(self, limit: int) -> list[Task]:
        tasks = []
        for level in self.templates.values():
            tasks.extend(level.get_iterations(limit=limit))
        return tasks

    def add_run_configuration(self) -> str:
        metadata = {
            "density": config.DEFAULT_DENSITY,
            "friction": config.DEFAULT_FRICTION,
            "elasticity": config.DEFAULT_ELASTICITY,
        }

        if self.runs_configurations:
            next_idx = int(max(self.runs_configurations["runs"].keys())[-3:]) + 1
            new_group_name = f"run_{next_idx:03d}"
        else:
            self.runs_configurations["runs"] = {}
            new_group_name = "run_001"

        self.runs_configurations["runs"][new_group_name] = metadata

        self.runs_configurations.save()

        return new_group_name
