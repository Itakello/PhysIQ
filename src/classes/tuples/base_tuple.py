from dataclasses import asdict, dataclass
from typing import Tuple


@dataclass(frozen=True)
class BaseTuple:

    def to_tuple(self) -> Tuple:
        return tuple(asdict(self).values())
