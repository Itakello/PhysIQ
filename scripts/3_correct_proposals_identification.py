"""
3_proposals_identification.py

Script that:
1. Connects to the same MongoDB database used before (db_name).
2. Retrieves puzzle entries from the 'puzzles' collection.
3. For each template (sorted by puzzle_id), processes up to `iterations` puzzle documents.
4. Attempts to find `num_proposals` correct proposals and `num_proposals` bad proposals
   by inserting a red ball (color_map index 0) at random positions (and random radius).
5. Verifies via a collision listener if the goal is reached before MAX_SIMULATION_STEPS.
6. Stores each found proposal (correct or bad) in the 'proposals' collection, along with a screenshot
   of the first frame of the simulation in the 'images' folder.
7. Stops searching once all required proposals are found OR `MAX_ATTEMPTS` is reached.
8. Logs the number of correct/bad proposals found for each puzzle.

Usage:
  python 3_proposals_identification.py \
      --db_name physiq_db \
      --visualize \
      --iterations 5 \
      --num_proposals 3 \
      --seed 42
"""

import copy
import random

from loguru import logger
from tqdm import tqdm

from src.managers import (
    ArgparseManager,
    MongoDBManager,
    ScreenshotManager,
    SimulationManager,
)
from src.utils.const import MAX_ATTEMPTS, MAX_RADIUS, MIN_RADIUS, SCENE_DIMENSIONS
from src.utils.db_schemas import ProposalData, ProposalSchema


def create_proposal_docs(n_proposals: int) -> list[dict]:
    assert n_proposals > 0
    proposals = []
    for _ in range(n_proposals):
        radius = random.uniform(MIN_RADIUS, MAX_RADIUS)
        x = random.uniform(radius, SCENE_DIMENSIONS[0] - radius)
        y = random.uniform(radius, SCENE_DIMENSIONS[1] - radius)
        ball_doc = {
            "body_type": 1,  # dynamic
            "position": [x, y],
            "angle": 0.0,
            "color": 0,  # color index for red
            "shape_type": 1,  # circle
            "radius": radius,
            "proposal": True,
        }
        proposals.append(ball_doc)
    return proposals


def find_correct_proposals_for_puzzle(
    db_manager: MongoDBManager,
    simulation_manager: SimulationManager,
    screenshot_manager: ScreenshotManager,
    puzzle_doc: dict,
    visualize: bool,
    save_proposals: bool = True,
) -> int:
    """
    Try random positions/radii for the puzzle until:
      - We find num_proposals correct, and num_proposals bad
      - Or we exceed MAX_ATTEMPTS

    Then log info and insert into 'proposals' collection in DB.
    """

    attempts = 0
    pbar = tqdm(
        total=MAX_ATTEMPTS,
        desc=f"Puzzle {puzzle_doc['id']}",
    )
    while attempts < MAX_ATTEMPTS:
        # 1) Generate random position & radius
        n_balls = 1 if puzzle_doc["metadata"]["tier"] == "BALL" else 2
        ball_docs = create_proposal_docs(n_proposals=n_balls)

        tmp_puzzle_doc = copy.deepcopy(puzzle_doc)
        tmp_puzzle_doc["bodies"].extend(ball_docs)

        # Check for overlapping
        try:
            goal_reached, _ = simulation_manager.run_simulation(
                puzzle=tmp_puzzle_doc, visualize=visualize, num_screenshots=0
            )
        except ValueError:
            continue

        attempts += 1
        pbar.update(1)

        if goal_reached:
            _, screenshots = simulation_manager.run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=visualize,
                num_screenshots=3,
            )

            if save_proposals and screenshots:
                screenshots_path = screenshot_manager.save_screenshots(
                    screenshots,
                    puzzle_doc["id"].replace(":", "_"),
                )
                proposals = [ProposalData(**ball_doc) for ball_doc in ball_docs]
                proposal_data = ProposalSchema(
                    id=puzzle_doc["id"],
                    attempt=attempts,
                    proposals=proposals,
                    image_path=screenshots_path.as_posix(),
                    tier="CORRECT",
                )
                db_manager.insert_proposal(proposal_data)
            break
    return attempts


def main() -> None:
    parser = ArgparseManager(
        "Brute-force proposals identification for puzzles in MongoDB."
    )
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    parser.add_seed_args()
    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    grouped_templates = db_manager.get_grouped_templates(
        start_template=args.start_template,
        stop_template=args.stop_template,
        start_iteration=args.start_iteration,
        iterations=args.iterations,
        type=args.templates_type,
    )

    # Prepare screenshot manager
    screenshot_manager = ScreenshotManager(subfolder="correct_proposals")

    simulation_manager = SimulationManager()

    max_solutions_to_find = 20

    for template_id, puzzles in tqdm(
        reversed(grouped_templates.items()),
        desc="Correct proposals identification progress",
    ):
        solutions_found = 0
        for puzzle_doc in puzzles:
            n_attempts = find_correct_proposals_for_puzzle(
                db_manager=db_manager,
                simulation_manager=simulation_manager,
                screenshot_manager=screenshot_manager,
                puzzle_doc=puzzle_doc,
                visualize=args.visualize,
                save_proposals=args.save_to_db,
            )
            logger.info(
                f"Puzzle {puzzle_doc['id']}: Found a correct proposals in {n_attempts} attempts."
            )
            if n_attempts < MAX_ATTEMPTS:
                solutions_found += 1
            if solutions_found >= max_solutions_to_find:
                break
        max_solutions_to_find = min(max_solutions_to_find, solutions_found)

    db_manager.close_connection()
    logger.info("Done identifying proposals!")


if __name__ == "__main__":
    main()
