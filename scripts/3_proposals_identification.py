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

import argparse
import copy
import random
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from managers.mongodb_manager import MongoDBManager
from src.utils.const import MAX_ATTEMPTS, MAX_RADIUS, MIN_RADIUS, SCENE_DIMENSIONS
from src.utils.db_schemas import ProposalSchema


def find_proposals_for_puzzle(
    db_manager: MongoDBManager,
    puzzle_doc: dict,
    num_proposals: int,
    visualize: bool,
    images_dir: Path,
) -> None:
    """
    Try random positions/radii for the puzzle until:
      - We find num_proposals good, and num_proposals bad
      - Or we exceed MAX_ATTEMPTS

    Then log info and insert into 'proposals' collection in DB.
    """
    puzzle_id = puzzle_doc["puzzle_id"]

    good_found = 0
    bad_found = 0
    attempts = 0
    overlaps = 0

    proposals_coll = db_manager.db["proposals"]

    while attempts < MAX_ATTEMPTS:
        if good_found >= num_proposals and bad_found >= num_proposals:
            break
        attempts += 1

        # 1) Generate random position & radius
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
        tmp_puzzle_doc = copy.deepcopy(puzzle_doc)
        tmp_puzzle_doc["bodies"].append(ball_doc)

        # Check for overlapping
        try:
            is_good, _ = run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=False,
            )
        except ValueError:
            overlaps += 1
            attempts -= 1
            continue

        # 3) Insert into DB
        #   (But only if it meets the needed type)
        if is_good and good_found < num_proposals:
            good_found += 1
            _, screenshot = run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=visualize,
                get_screenshot=True,
            )
            screenshot_path = images_dir / f"{puzzle_id}_good_{good_found}.png"
            # Save screenshot in screenshot_path
            screenshot.save(screenshot_path)
            # Insert to DB
            proposal_data = ProposalSchema(
                puzzle_id=puzzle_id,
                is_good=True,
                attempt=attempts,
                radius=radius,
                position=[x, y],
                image_path=screenshot_path.as_posix(),
            )
            proposals_coll.insert_one(proposal_data.model_dump())
        elif (not is_good) and bad_found < num_proposals:
            bad_found += 1
            _, screenshot = run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=visualize,
                get_screenshot=True,
            )
            screenshot_path = images_dir / f"{puzzle_id}_bad_{bad_found}.png"
            # Save screenshot in screenshot_path
            screenshot.save(screenshot_path)
            # Insert to DB
            proposal_data = ProposalSchema(
                puzzle_id=puzzle_id,
                is_good=False,
                attempt=attempts,
                radius=radius,
                position=[x, y],
                image_path=screenshot_path.as_posix(),
            )
            proposals_coll.insert_one(proposal_data.model_dump())

    logger.info(
        f"Puzzle {puzzle_id} => Good: {good_found}, Bad: {bad_found}, Attempts: {attempts}, Overlaps: {overlaps}"
    )


def parse_args() -> argparse.Namespace:
    parser = ArgparseManager(
        "Brute-force proposals identification for puzzles in MongoDB."
    )
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    parser.add_proposal_args()
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:

    # Set random seed
    random.seed(args.seed)

    # Prepare output folder for images
    images_dir = Path("images")
    images_dir.mkdir(exist_ok=True)

    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)

    grouped_templates = db_manager.get_grouped_templates(
        args.start_template, args.iterations
    )

    simulation_manager = SimulationManager()

    pbar = tqdm(
        total=len(grouped_templates) * args.iterations,
        desc="Proposals Identification",
        dynamic_ncols=True,
    )

    for template_id in template_keys:
        # Up to 'iterations' tasks from this template
        tasks = grouped[template_id][: args.iterations]
        for puzzle_doc in tasks:
            # We'll handle logs with tqdm.write so the bar stays clean
            tqdm.write(f"Processing puzzle_id={puzzle_doc['puzzle_id']} ...")

            find_proposals_for_puzzle(
                db_manager=db_manager,
                puzzle_doc=puzzle_doc,
                num_proposals=args.num_proposals,
                visualize=args.visualize,
                images_dir=images_dir,
            )
            pbar.update(1)

    pbar.close()
    db_manager.close_connection()
    logger.info("Done identifying proposals!")


if __name__ == "__main__":
    args = parse_args()
    main(args)
