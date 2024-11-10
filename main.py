from itakello_logging import ItakelloLogging

from src.managers import LevelManager, SimulationManager

logger = ItakelloLogging(
    debug=True,  # excluded_modules=["pymunk.space", "pymunk.shapes", "pymunk.body"]
).get_logger(__name__)


def main() -> None:
    simulation_manager = SimulationManager()
    level_manager = LevelManager()
    tasks = level_manager.get_levels_first_tasks()
    for task in tasks:
        simulation_manager.load_task(task)
        simulation_manager.test_goal()
        # simulation_manager.find_proposal()
        # simulation_manager.add_solution()
        # simulation_manager.run_simulation()


if __name__ == "__main__":
    main()
