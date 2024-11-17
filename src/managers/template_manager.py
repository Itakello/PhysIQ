from dataclasses import dataclass, field
from pathlib import Path

from classes.template import Template
from src.classes.task import Task

from .base_manager import BaseManager


@dataclass
class TemplateManager(BaseManager):
    templates: dict[str, Template] = field(default_factory=dict)

    def __post_init__(self) -> None:
        data_path = Path("data")
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
