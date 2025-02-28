"""
4_incorrect_proposals_identification.py

Script that:
1. Connects to MongoDB and retrieves puzzles with correct proposals
2. For each puzzle, attempts to find incorrect proposals of three difficulty levels:
   - EASY: Proposals close to the target objects
   - MEDIUM: Proposals at medium distance from targets
   - HARD: Proposals far from the targets
3. Stores the proposals in the database with appropriate difficulty markers
4. Saves screenshots of the simulation for each proposal type

Usage:
  python 4_incorrect_proposals_identification.py \
      --db_name physiq_db \
      --visualize \
      --iterations 5 \
      --num_proposals 3 \
      --seed 42
"""

import copy
import math
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
from src.utils.db_schemas import ProposalData, ProposalSchema, PuzzleSchema


def get_random_position(
    center: tuple[float, float], min_radius: float, max_radius: float
) -> tuple[float, float]:
    """
    Returns a random position (x, y) that is between the given min_radius and max_radius from the center.
    The position is guaranteed to be within the scene boundaries.

    Returns:
        tuple: A tuple (x, y) representing the random position within scene boundaries.
    """
    if min_radius > max_radius:
        raise ValueError("min_radius cannot be greater than max_radius")

    for _ in range(MAX_ATTEMPTS):
        # Generate a random angle between 0 and 2*pi
        angle = random.uniform(0, 2 * math.pi)

        # To ensure uniform distribution in the area, select the radius in proportion to the area
        # This is achieved by sampling the squared radius uniformly.
        r = math.sqrt(random.uniform(min_radius**2, max_radius**2))

        # Calculate the new position using the polar to Cartesian conversion
        x = center[0] + r * math.cos(angle)
        y = center[1] + r * math.sin(angle)

        # Check if the position is within scene boundaries
        if (
            0 + r <= x <= SCENE_DIMENSIONS[0] - r
            and 0 + r <= y <= SCENE_DIMENSIONS[1] - r
        ):
            return (x, y)

    # If we couldn't find a valid position after MAX_ATTEMPTS, use clamped values
    x = max(0, min(x, SCENE_DIMENSIONS[0]))  # type: ignore
    y = max(0, min(y, SCENE_DIMENSIONS[1]))  # type: ignore
    return (x, y)


def create_proposals_docs(proposals: list[ProposalData], difficulty: str) -> list[dict]:
    """Create proposal documents from the given proposals."""
    new_proposals = []
    for proposal in proposals:
        if difficulty == "HARD":
            min_radius = 0.0
            max_radius = proposal.radius
        elif difficulty == "MEDIUM":
            min_radius = proposal.radius
            max_radius = proposal.radius * 2
        else:
            min_radius = proposal.radius * 2
            max_radius = proposal.radius * 4
        new_position = get_random_position(
            (proposal.position[0], proposal.position[1]),
            min_radius,
            max_radius,
        )
        new_radius = random.uniform(
            max(MIN_RADIUS, proposal.radius / 2),
            min(MAX_RADIUS, proposal.radius * 2),
        )
        proposal_doc = {
            "body_type": 1,
            "position": new_position,
            "angle": 0.0,
            "color": 0,
            "shape_type": 1,
            "radius": new_radius,
            "proposal": True,
        }
        new_proposals.append(proposal_doc)
    return new_proposals


def find_incorrect_proposals(
    db_manager: MongoDBManager,
    simulation_manager: SimulationManager,
    screenshot_manager: ScreenshotManager,
    puzzle: PuzzleSchema,
    correct_proposal: ProposalSchema,
    difficulty: str,
    visualize: bool,
    save_proposals: bool = True,
) -> int:
    """Find incorrect proposals for a specific difficulty level."""
    attempts = 0
    pbar = tqdm(
        total=MAX_ATTEMPTS,
        desc=f"Puzzle {puzzle.id} - {difficulty}",
        leave=False,
    )

    while attempts < MAX_ATTEMPTS:
        ball_docs = create_proposals_docs(correct_proposal.proposals, difficulty)

        tmp_puzzle_doc = copy.deepcopy(puzzle.model_dump())
        tmp_puzzle_doc["bodies"].extend(ball_docs)

        try:
            goal_reached, _ = simulation_manager.run_simulation(
                puzzle=tmp_puzzle_doc, visualize=False, num_screenshots=0
            )
        except ValueError:
            continue

        attempts += 1
        pbar.update(1)

        if not goal_reached:  # We found an incorrect proposal
            _, screenshots = simulation_manager.run_simulation(
                puzzle=tmp_puzzle_doc,
                visualize=visualize,
                num_screenshots=3,
            )

            if save_proposals and screenshots:
                screenshots_path = screenshot_manager.save_screenshots(
                    screenshots,
                    tmp_puzzle_doc["id"].replace(":", "_"),
                )
                proposals = [ProposalData(**ball_doc) for ball_doc in ball_docs]
                proposal_data = ProposalSchema(
                    id=tmp_puzzle_doc["id"],
                    attempt=attempts,
                    proposals=proposals,
                    image_path=screenshots_path.as_posix(),
                    tier=f"INCORRECT_{difficulty}",
                )
                db_manager.insert_proposal(proposal_data)
            break

    pbar.close()
    return attempts


def main() -> None:
    parser = ArgparseManager(
        "Incorrect proposals identification for puzzles in MongoDB."
    )
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    parser.add_seed_args()
    args = parser.parse_args()

    random.seed(args.seed)

    db_manager = MongoDBManager(db_name=args.db_name)
    simulation_manager = SimulationManager()

    # Create screenshot managers for each difficulty
    screenshot_managers = {
        "EASY": ScreenshotManager(subfolder="incorrect_proposals_easy"),
        "MEDIUM": ScreenshotManager(subfolder="incorrect_proposals_medium"),
        "HARD": ScreenshotManager(subfolder="incorrect_proposals_hard"),
    }

    # First, retrieve all correct proposals
    correct_proposals = db_manager.get_all_correct_proposals(
        start_template=args.start_template,
        stop_template=args.stop_template,
        start_iteration=args.start_iteration,
        type=args.templates_type,
    )

    logger.info(f"Found {len(correct_proposals)} correct proposals to process")

    # Process each correct proposal to find incorrect proposals
    for correct_proposal in tqdm(
        correct_proposals,
        desc="Processing correct proposals",
        total=len(correct_proposals),
    ):
        puzzle_id = correct_proposal.id
        puzzle = db_manager.get_puzzle_by_id(puzzle_id)

        if not puzzle:
            logger.warning(f"Puzzle not found for proposal {puzzle_id}, skipping")
            continue

        if not puzzle.metadata.testable:
            logger.debug(f"Puzzle {puzzle_id} is not testable, skipping")
            continue

        for difficulty in ["EASY", "MEDIUM", "HARD"]:
            n_attempts = find_incorrect_proposals(
                db_manager=db_manager,
                simulation_manager=simulation_manager,
                screenshot_manager=screenshot_managers[difficulty],
                puzzle=puzzle,
                correct_proposal=correct_proposal,
                difficulty=difficulty,
                visualize=args.visualize,
                save_proposals=args.save_to_db,
            )
            logger.debug(
                f"Puzzle {puzzle_id}: Found {difficulty} incorrect proposal in {n_attempts} attempts."
            )

    db_manager.close_connection()
    logger.info("Done identifying incorrect proposals!")


if __name__ == "__main__":
    main()
