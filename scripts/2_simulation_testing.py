import argparse

from loguru import logger

from src.managers import MongoDBManager, SimulationManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run PyBox2D simulations on puzzle templates from MongoDB."
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
    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    grouped_templates = db_manager.get_grouped_templates(
        args.start_template, args.iterations
    )

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
    logger.info("Done running simulations!")


if __name__ == "__main__":
    args = parse_args()
    main(args)
