import argparse

from loguru import logger
from tqdm import tqdm

from src.managers import ArgparseManager, MongoDBManager, SimulationManager


def parse_args() -> argparse.Namespace:
    parser = ArgparseManager(
        "Run PyBox2D simulations on puzzle templates from MongoDB."
    )
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    grouped_templates = db_manager.get_grouped_templates(
        args.start_template, args.iterations
    )

    simulation_manager = SimulationManager()
    total_puzzles = 0
    solutions_found = 0

    for template_id, puzzles in tqdm(
        grouped_templates.items(), desc="Simulation progress"
    ):
        if not puzzles:
            logger.info(f"No tasks found for template {template_id}")
            continue

        for puzzle_doc in puzzles:
            total_puzzles += 1
            pid = puzzle_doc["id"]
            collided, _ = simulation_manager.run_simulation(
                puzzle_doc, visualize=args.visualize, get_screenshot=False
            )
            if collided:
                logger.info(f"Collision detected for puzzle {pid}")
                solutions_found += 1

    db_manager.close_connection()
    logger.info("Done running simulations!")
    logger.info(f"Solutions found without proposals: [{solutions_found}]")
    logger.info(f"Total puzzles tested: [{total_puzzles}]")


if __name__ == "__main__":
    args = parse_args()
    main(args)
