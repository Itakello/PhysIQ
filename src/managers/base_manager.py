from dataclasses import dataclass, field

from loguru import logger


@dataclass
class BaseManager:
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = self.__class__.__name__
        logger.debug(f"Initialized {self.name} manager")
