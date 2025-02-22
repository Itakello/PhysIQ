from loguru import logger
from tqdm import tqdm

from src.managers import ArgparseManager, MongoDBManager, SimulationManager


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
        args.start_template, args.iterations
    )

    simulation_manager = SimulationManager()
    total_puzzles = 0
    solutions_found = 0

    for template_id, puzzles in tqdm(
        grouped_templates.items(), desc="Simulation progress"
    ):
        for puzzle_doc in puzzles:
            total_puzzles += 1
            pid = puzzle_doc["id"]
            goal_reached, _ = simulation_manager.run_simulation(
                puzzle_doc, visualize=args.visualize, get_screenshot=False
            )
            if goal_reached:
                logger.info(f"Goal reached without proposals for puzzle {pid}")
                solutions_found += 1

    db_manager.close_connection()
    logger.info("Done running simulations!")
    logger.info(f"Solutions found without proposals: [{solutions_found}]")
    logger.info(f"Total puzzles tested: [{total_puzzles}]")


if __name__ == "__main__":
    main()
