from itakello_logging import ItakelloLogging
from tqdm import tqdm

from src.managers import SimulationManager, TemplateManager

logger = ItakelloLogging(
    debug=False, excluded_modules=["pymunk.space", "pymunk.shapes", "pymunk.body"]
).get_logger(__name__)

ATTEMPTS_PER_TASK = 5


def main() -> None:
    simulation_manager = SimulationManager(show_visualization=False)
    config_names = simulation_manager.get_run_config_names()
    template_manager = TemplateManager()

    for config_name in tqdm(
        config_names, desc="Iterating over run configs", leave=False, dynamic_ncols=True
    ):
        template_manager.load_templates(run_config_name=config_name)
        tasks = template_manager.get_templates_tasks(
            limit=ATTEMPTS_PER_TASK, starting_level="00000"
        )

        for task in tqdm(
            tasks,
            desc=f"[{config_name}] Iterating over tasks",
            leave=False,
            dynamic_ncols=True,
        ):
            simulation_manager.load_task(task)
            simulation_manager.find_proposals(
                run_config_name=config_name, save_screenshots=True
            )


if __name__ == "__main__":
    main()
