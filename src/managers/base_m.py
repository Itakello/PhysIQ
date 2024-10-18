from dataclasses import dataclass, field

from itakello_logging import ItakelloLogging

logger = ItakelloLogging().get_logger(__name__)


@dataclass
class BaseManager:
    name: str = field(init=False)

    def __post_init__(self) -> None:
        self.name = self.__class__.__name__
        logger.debug(f"Initialized {self.name} manager")
