from dataclasses import dataclass, field
from pathlib import Path

from src.classes.level import Level
from src.classes.task import Task

from .base_manager import BaseManager


@dataclass
class LevelManager(BaseManager):
    levels: dict[str, Level] = field(default_factory=dict)
    current_level: Level | None = None

    def __post_init__(self) -> None:
        data_path = Path("data")
        categories = [d.name for d in data_path.iterdir() if d.is_dir()]
        for category in categories:
            levels = [d.name for d in (data_path / category).iterdir() if d.is_dir()]
            for level in levels:
                self.levels[level] = Level(id=level, category=category)

    def get_levels_first_tasks(self) -> list[Task]:
        return [level.get_first_iteration() for level in self.levels.values()]

    def get_levels_all_tasks(self) -> list[Task]:
        tasks = []
        for level in self.levels.values():
            tasks.extend(level.get_all_iterations())
        return tasks
