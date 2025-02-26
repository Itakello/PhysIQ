from pathlib import Path

from loguru import logger
from tqdm import tqdm

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
    db_manager = MongoDBManager(db_name=args.db_name)

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


if __name__ == "__main__":
    main()
