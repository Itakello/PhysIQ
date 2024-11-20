from itakello_logging import ItakelloLogging

from src.managers import SimulationManager, TemplateManager

logger = ItakelloLogging(
    debug=True, excluded_modules=["pymunk.space", "pymunk.shapes", "pymunk.body"]
).get_logger(__name__)


def main() -> None:
    simulation_manager = SimulationManager(show_visualization=True)
    template_manager = TemplateManager()
    # print(template_manager.add_configuration())
    template_manager.load_templates(run_configuration_name="standard")
    tasks = template_manager.get_templates_first_tasks(starting_level="00017")

    for task in tasks:
        simulation_manager.load_task(task)
        # simulation_manager.find_proposals(config_name="config_001")
        simulation_manager.test_goal(
            run_config_name="standard",
            require_end_screen=True,
            save_screenshots=True,
        )


if __name__ == "__main__":
    main()
