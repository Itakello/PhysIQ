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

from src.managers.db_manager import MongoDBManager
from src.utils.box2d_runner import run_simulation
from src.utils.collision_listener import CollisionListener
from src.utils.const import MAX_ATTEMPTS, MAX_RADIUS, MIN_RADIUS, SCENE_DIMENSIONS
from src.utils.db_schemas import ProposalSchema


def parse_template_id(puzzle_id: str) -> tuple[int, int]:
    """
    Convert puzzle_id (like '00000:0') into two ints (template_part, iteration_part).
    Used to group puzzles by template and sort.
    """
    main_part, iteration_part = puzzle_id.split(":")
    return int(main_part), int(iteration_part)


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
                collision_listener=CollisionListener(),
            )
        except ValueError as e:
            logger.warning(f"Skipping proposal due to overlapping bodies: {e}")
            continue

        # 3) Insert into DB
        #   (But only if it meets the needed type)
        if is_good and good_found < num_proposals:
            good_found += 1
            _, screenshot = run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=visualize,
                collision_listener=CollisionListener(),
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
                collision_listener=CollisionListener(),
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
        f"Puzzle {puzzle_id} => Good: {good_found}, Bad: {bad_found}, Attempts: {attempts}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Brute-force proposals identification for puzzles in MongoDB."
    )
    parser.add_argument(
        "--start_template",
        type=int,
        default=0,
        help="Index of the first template to test",
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
        help="Enable PyGame window rendering",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of puzzle iterations to process per template",
    )
    parser.add_argument(
        "--num_proposals",
        type=int,
        default=3,
        help="How many good and bad proposals to gather for each puzzle",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible position/radius generation",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:

    # Set random seed
    random.seed(args.seed)

    # Prepare output folder for images
    images_dir = Path("images")
    images_dir.mkdir(exist_ok=True)

    # Connect to DB
    db_manager = MongoDBManager(db_name=args.db_name)
    puzzles_coll = db_manager.db["puzzles"]

    # Retrieve all puzzles from DB
    all_puzzles = list(puzzles_coll.find({}))
    # Sort them by the integer part of puzzle_id
    all_puzzles.sort(key=lambda p: parse_template_id(p["puzzle_id"]))

    # Group them by template
    grouped = {}
    for puzzle in all_puzzles:
        tpl_id, itn_id = parse_template_id(puzzle["puzzle_id"])
        if tpl_id not in grouped:
            grouped[tpl_id] = []
        grouped[tpl_id].append(puzzle)

    # We'll iterate over all template_keys
    template_keys = sorted(grouped.keys())

    # Create a single progress bar for the entire run
    total_puzzles = sum(len(grouped[tid]) for tid in template_keys)
    pbar = tqdm(
        total=total_puzzles, desc="Proposals Identification", dynamic_ncols=True
    )

    for template_id in template_keys:
        if template_id < args.start_template:
            continue
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
