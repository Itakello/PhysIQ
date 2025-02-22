"""
3_proposals_identification.py

Script that:
1. Connects to the same MongoDB database used before (db_name).
2. Retrieves puzzle entries from the 'puzzles' collection.
3. For each template (sorted by puzzle_id), processes up to `iterations` puzzle documents.
4. Attempts to find `num_proposals` good proposals and `num_proposals` bad proposals
   by inserting a red ball (color_map index 0) at random positions (and random radius).
5. Verifies via a collision listener if the goal is reached before MAX_SIMULATION_STEPS.
6. Stores each found proposal (good or bad) in the 'proposals' collection, along with a screenshot
   of the first frame of the simulation in the 'images' folder.
7. Stops searching once all required proposals are found OR `MAX_ATTEMPTS` is reached.
8. Logs the number of good/bad proposals found for each puzzle.

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
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from src.managers import ArgparseManager, MongoDBManager, SimulationManager
from src.utils.const import MAX_ATTEMPTS, MAX_RADIUS, MIN_RADIUS, SCENE_DIMENSIONS
from src.utils.db_schemas import ProposalData, ProposalSchema


def create_ball_doc(n_balls: int) -> list[dict]:
    assert n_balls > 0
    balls = []
    for _ in range(n_balls):
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
        balls.append(ball_doc)
    return balls


def find_good_proposals_for_puzzle(
    db_manager: MongoDBManager,
    simulation_manager: SimulationManager,
    puzzle_doc: dict,
    num_proposals: int,
    visualize: bool,
    images_dir: Path,
    save_proposals: bool = True,
) -> tuple[int, int]:
    """
    Try random positions/radii for the puzzle until:
      - We find num_proposals good, and num_proposals bad
      - Or we exceed MAX_ATTEMPTS

    Then log info and insert into 'proposals' collection in DB.
    """

    good_proposals = 0
    attempt = 0

    for attempt in tqdm(
        range(1, MAX_ATTEMPTS + 1),
        desc=f"Puzzle {puzzle_doc['id']}",
    ):
        if good_proposals >= num_proposals:
            break

        # 1) Generate random position & radius
        n_balls = 1 if puzzle_doc["metadata"]["tier"] == "BALL" else 2
        ball_docs = create_ball_doc(n_balls=n_balls)

        tmp_puzzle_doc = copy.deepcopy(puzzle_doc)
        tmp_puzzle_doc["bodies"].extend(ball_docs)

        # Check for overlapping
        try:
            goal_reached, _ = simulation_manager.run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=False,
            )
        except ValueError:
            continue

        # 3) Insert into DB
        #   (But only if it meets the needed type)
        if goal_reached and good_proposals < num_proposals:
            good_proposals += 1
            _, screenshot = simulation_manager.run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=visualize,
                get_screenshot=True,
            )
            screenshot_path = (
                images_dir / f"{puzzle_doc['id']}_good_{good_proposals}.png"
            )
            # Save screenshot in screenshot_path
            # Insert to DB
            proposals = [ProposalData(**ball_doc) for ball_doc in ball_docs]
            proposal_data = ProposalSchema(
                id=puzzle_doc["id"],
                is_good=True,
                attempt=attempt,
                proposals=proposals,
                image_path=screenshot_path.as_posix(),
                tier="GOOD",
            )
            if save_proposals:
                screenshot.save(screenshot_path)
                db_manager.insert_proposal(proposal_data)
    return good_proposals, attempt


def main() -> None:
    parser = ArgparseManager(
        "Brute-force proposals identification for puzzles in MongoDB."
    )
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    parser.add_proposal_args()
    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    # Prepare output folder for images
    images_dir = Path("images")
    images_dir.mkdir(exist_ok=True)

    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    grouped_templates = db_manager.get_grouped_templates(
        start_template=args.start_template,
        iterations=args.iterations,
        type=args.templates_type,
    )

    simulation_manager = SimulationManager()

    for template_id, puzzles in tqdm(
        grouped_templates.items(), desc="Good proposals identification progress"
    ):
        for puzzle_doc in puzzles:
            good_proposals, n_attempts = find_good_proposals_for_puzzle(
                db_manager=db_manager,
                simulation_manager=simulation_manager,
                puzzle_doc=puzzle_doc,
                num_proposals=args.num_proposals,
                visualize=args.visualize,
                images_dir=images_dir,
                save_proposals=args.save_to_db,
            )
            logger.info(
                f"Puzzle {puzzle_doc['id']}: Found {good_proposals} good proposals in {n_attempts} attempts."
            )
    db_manager.close_connection()
    logger.info("Done identifying proposals!")


if __name__ == "__main__":
    main()
