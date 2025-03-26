from pathlib import Path

from loguru import logger
from tqdm import tqdm

<<<<<<< HEAD
from src.managers import (
    ArgparseManager,
    MongoDBManager,
    ScreenshotManager,
    SimulationManager,
)


def main() -> None:
    parser = ArgparseManager(
        "Run PyBox2D simulations on puzzle templates from MongoDB."
    )
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    args = parser.parse_args()
    # Connect to DB
=======
from src.managers.db_manager import MongoDBManager
from src.managers.simulation_manager import SimulationManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Pymunk simulations on puzzle templates from MongoDB."
    )
    parser.add_argument(
        "--start_template",
        type=int,
        default=0,
        help="Index of the first template to test",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of puzzle iterations to test per template",
    )
    parser.add_argument(
        "--db_name",
        type=str,
        default="physiq_db",
        help="Name of the MongoDB database to connect to",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Enable Pygame visualization of the simulation",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
>>>>>>> 52f9dd91f0793666f53bba46b9f9d22deff29724
    db_manager = MongoDBManager(db_name=args.db_name)
    grouped_templates = db_manager.get_grouped_templates(
        start_template=args.start_template,
        iterations=args.iterations,
    )

<<<<<<< HEAD
    grouped_templates = db_manager.get_grouped_templates(
        start_template=args.start_template,
        start_iteration=args.start_iteration,
        stop_template=args.stop_template,
        iterations=args.iterations,
        type=args.templates_type,
    )

    simulation_manager = SimulationManager()
    screenshot_manager = ScreenshotManager(subfolder="starting_configuration")
    total_puzzles = 0
    solutions_found = 0

    for template_id, puzzles in tqdm(
        grouped_templates.items(), desc="Simulation progress"
    ):
        for puzzle_doc in puzzles:
            total_puzzles += 1
            pid = puzzle_doc["id"]
            goal_reached, screenshots = simulation_manager.run_simulation(
                puzzle_doc, visualize=args.visualize, num_screenshots=1
            )
            if goal_reached:
                logger.warning(f"Goal reached without proposals for puzzle {pid}")
                solutions_found += 1
            if args.save_to_db:
                screen_path = screenshot_manager.save_screenshots(
                    screenshots, pid.replace(":", "_")
                )
                assert isinstance(screen_path, Path)
                db_manager.set_puzzle_screenshot(pid, screen_path)
                db_manager.set_puzzle_testability(pid, not goal_reached)

    db_manager.close_connection()
    logger.info("Done running simulations!")
    logger.info(f"Solutions found without proposals: [{solutions_found}]")
    logger.info(f"Total puzzles tested: [{total_puzzles}]")
=======
    simulation_manager = SimulationManager()

    for template_id, puzzles in grouped_templates.items():
        if not puzzles:
            logger.info(f"No tasks found for template {template_id}")
            continue

        logger.info(f"Simulating template {template_id} with {len(puzzles)} tasks")

        for puzzle_doc in puzzles:
            pid = puzzle_doc["id"]
            collided, _ = simulation_manager.run_simulation(
                puzzle_doc, visualize=args.visualize, get_screenshot=False
            )
            logger.info(f"Puzzle {pid} => Collided? {collided}")

    db_manager.close_connection()
    logger.info("Done running Pymunk simulations!")
>>>>>>> 52f9dd91f0793666f53bba46b9f9d22deff29724


if __name__ == "__main__":
    args = parse_args()
    main(args)
