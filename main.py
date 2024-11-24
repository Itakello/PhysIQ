import argparse
import json
from pathlib import Path

from itakello_logging import ItakelloLogging
from tqdm import tqdm

import wandb
from src.config import const
from src.managers import SimulationManager, TemplateManager

ATTEMPTS_PER_TASK = 5
MAX_FAILURES = 3

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


def initialize_wandb(config_name: str, config: dict) -> None:
    wandb.init(
        name=config_name,
        project="physiq-dataset-creation",
        config={
            "max_attempts": const.MAX_ATTEMPTS,
            "good_examples_per_task": const.NUMBER_OF_GOOD_CANDIDATES,
            "bad_examples_per_task": const.NUMBER_OF_BAD_CANDIDATES,
            "config": config,
        },
    )


def main(args: argparse.Namespace) -> None:
    run_config = get_config(config_name=args.config)
    initialize_wandb(config_name=args.config, config=run_config)

    simulation_manager = SimulationManager(
        run_config=run_config, show_visualization=False
    )
    template_manager = TemplateManager(run_config=run_config)

    template_manager.load_templates()
    template_manager.iterate_templates(
        simulation_manager=simulation_manager,
        config_name=args.config,
        attempts_per_task=ATTEMPTS_PER_TASK,
        max_failures=MAX_FAILURES,
    )


if __name__ == "__main__":
    args = parse_args()
    main(args)
