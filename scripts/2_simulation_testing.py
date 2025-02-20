import argparse

from loguru import logger

from src.managers.db_manager import MongoDBManager
from src.utils.box2d_runner import run_simulation


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

    # Retrieve all puzzles, sort them by puzzle_id
    # puzzle_id typically looks like "00000:0" - we can parse the prefix as int
    puzzles_coll = db_manager.db["puzzles"]
    all_puzzles = list(puzzles_coll.find({}))

    # Sort by the integer part of puzzle_id before the colon
    def parse_template_id(pid: str) -> tuple[int, int]:
        # handle "00012:34" -> returns (12, 34)
        main_part, iteration_part = pid.split(":")
        return (int(main_part), int(iteration_part))

    all_puzzles.sort(key=lambda p: parse_template_id(p["puzzle_id"]))

    # Group by template_id
    grouped = {}
    for p in all_puzzles:
        template_part, _ = parse_template_id(p["puzzle_id"])
        if template_part not in grouped:
            grouped[template_part] = []
        grouped[template_part].append(p)

    # Now iterate over template_part starting from start_template
    template_keys = sorted(list(grouped.keys()))
    for template_id in template_keys:
        if template_id < args.start_template:
            continue

        # We'll take up to "iterations" iterations from this template
        iterations = grouped[template_id][: args.iterations]
        if not iterations:
            logger.warning(f"No iterations found for template {template_id}")
            continue

        logger.info(
            f"Simulating template {template_id} with {len(iterations)} iterations"
        )

        for puzzle_doc in iterations:
            run_simulation(puzzle_doc, visualize=args.visualize)

    db_manager.close_connection()
    logger.info("Done running PyBox2D simulations!")


if __name__ == "__main__":
    args = parse_args()
    main(args)
