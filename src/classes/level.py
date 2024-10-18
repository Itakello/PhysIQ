from dataclasses import dataclass, field


@dataclass
class Level:
    id: str
    _iterations: list[str] = field(default_factory=list)
    _current_iteration: str = field(init=False)

    def get_next_iteration(self) -> str | None:
        if not self._iterations:
            return None
        self._current_iteration = self._iterations.pop(0)
        return self._current_iteration

    def add_iteration(self, iteration: str) -> None:
        if iteration not in self._iterations:
            self._iterations.append(iteration)
            self._iterations.sort()

    def has_more_iterations(self) -> bool:
        return bool(self._iterations)
