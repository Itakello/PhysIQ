from itakello_logging import ItakelloLogging

from src.managers import LevelManager, SimulationManager

logger = ItakelloLogging(
    debug=True, excluded_modules=["pymunk.space", "pymunk.shapes", "pymunk.body"]
).get_logger(__name__)


def main() -> None:
    simulation_manager = SimulationManager()
    level_manager = LevelManager()
    level_manager.load_levels()
    simulation_manager.setup()
    simulation_manager.run()


if __name__ == "__main__":
    main()
