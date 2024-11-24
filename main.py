from pathlib import Path
from itakello_logging import ItakelloLogging
from tqdm import tqdm
import wandb
from .src.classes.custom_dict import CustomDict
from src.managers import SimulationManager, TemplateManager
import argparse
from config import const
import json
ATTEMPTS_PER_TASK = 5

logger = ItakelloLogging(
    debug=False, excluded_modules=["pymunk.space", "pymunk.shapes", "pymunk.body"]
).get_logger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Python project template.")
    parser.add_argument(
        "-c", "--config", type=str, required=True, help="Name of the configuration"
    )
    return parser.parse_args()

def get_config(config_name: str) -> dict:
    try:
        config = json.loads(Path("data/runs_configuration.json").read_text())
    except FileNotFoundError:
        logger.error("No configuration file found")
        raise SystemExit
    try:
        curr_config = config["runs"][config_name]
    except KeyError:
        logger.error(f"No configuration found for {config_name}")
        raise SystemExit
    return curr_config

def initialize_wandb(config: dict) -> None:
    wandb.init(
    project="physiq-dataset-creation",
    config={
        "max_attempts": const.MAX_ATTEMPTS,
        "good_examples_per_task": const.NUMBER_OF_GOOD_CANDIDATES,
        "bad_examples_per_task": const.NUMBER_OF_BAD_CANDIDATES,
        "config": config
    }
)

def main(args: argparse.Namespace) -> None:
    run_config = get_config(config_name=args.config)
    simulation_manager = SimulationManager(show_visualization=False)
    template_manager = TemplateManager()
    
    template_manager.load_templates(run_config_name=args.config)
    tasks = template_manager.get_templates_tasks(
        limit=ATTEMPTS_PER_TASK, starting_level="00000"
    )

    for task in tqdm(
        tasks,
        desc=f"[{args.config}] Iterating over tasks",
        leave=False,
        dynamic_ncols=True,
    ):
        simulation_manager.load_task(task)
        simulation_manager.find_proposals(
            run_config_name=args.config, save_screenshots=True
        )


if __name__ == "__main__":
    args = parse_args()
    main(args)
