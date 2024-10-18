from dataclasses import dataclass, field

from src.classes.level import Level
from src.config.config import CONFIG_DIR

from .base_m import BaseManager


@dataclass
class LevelManager(BaseManager):
    levels: dict[str, Level] = field(default_factory=dict)
    current_level: Level | None = None

    def load_levels(self) -> None:
        config_files = CONFIG_DIR.glob("*.json")
        for config_file in config_files:
            level_id, iteration = self._parse_config_filename(config_file.name)
            if level_id not in self.levels:
                self.levels[level_id] = Level(id=level_id)
            self.levels[level_id].add_iteration(iteration)

    def get_next_level(self) -> Level | None:
        if not self.levels:
            return None
        level_id = next(iter(self.levels))
        self.current_level = self.levels.pop(level_id)
        return self.current_level

    def get_current_config_filename(self) -> str | None:
        if not self.current_level:
            return None
        iteration = self.current_level.get_next_iteration()
        if not iteration:
            return None
        return f"{self.current_level.id}_{iteration}.json"

    def has_more_levels(self) -> bool:
        return bool(self.levels)

    @staticmethod
    def _parse_config_filename(filename: str) -> tuple[str, str]:
        parts = filename.split("_")
        return parts[0], parts[1].split(".")[0]
