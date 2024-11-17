from itakello_logging import ItakelloLogging

from src.managers import SimulationManager, TemplateManager

logger = ItakelloLogging(
    debug=False, excluded_modules=["pymunk.space", "pymunk.shapes", "pymunk.body"]
).get_logger(__name__)


def main() -> None:
    simulation_manager = SimulationManager(show_visualization=False)
    template_manager = TemplateManager()
    tasks = template_manager.get_templates_first_tasks(starting_level="00000")

    for task in tasks:
        simulation_manager.load_task(task)
        simulation_manager.find_proposals()
        # simulation_manager.test_goal()


if __name__ == "__main__":
    main()
