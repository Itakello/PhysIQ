import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config.config import CONFIG_DIR

from .base_m import BaseManager


@dataclass
class ConfigManager(BaseManager):
    config_dir: Path = CONFIG_DIR

    def load_config(self, config_filename: str) -> dict[str, Any]:
        config_path = CONFIG_DIR / config_filename
        try:
            with config_path.open("r") as f:
                config_data = json.load(f)
            return config_data
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except json.JSONDecodeError:
            raise json.JSONDecodeError(
                f"Invalid JSON in configuration file: {config_path}", doc="", pos=0
            )
