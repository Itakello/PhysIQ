
from dataclasses import dataclass, field
from pathlib import Path


from ..classes.task import Task
from ..classes.template import Template
from .base_manager import BaseManager


@dataclass
class TemplateManager(BaseManager):
    run_config: dict
    templates: dict[str, Template] = field(default_factory=dict)

    def load_templates(self) -> None:
        template_path = Path("data") / "templates"
        categories = [d.name for d in template_path.iterdir() if d.is_dir()]
        for category in categories:
            levels = [
                d.name for d in sorted((template_path / category).iterdir()) if d.is_dir()
            ]
            for level in levels:
                self.templates[level] = Template(
                    id=level,
                    category=category,
                    run_config=self.run_config,
                )

    def get_templates_first_tasks(self, starting_level: str = "00000") -> list[Task]:
        return [
            level.get_first_task()
            for name, level in self.templates.items()
            if name >= starting_level
        ]

    def get_templates_tasks(
        self, limit: int, starting_level: str = "00000"
    ) -> list[Task]:
        tasks = []
        for level in self.templates.values():
            if level.id >= starting_level:
                tasks.extend(level.get_tasks(limit=limit))
        return tasks
