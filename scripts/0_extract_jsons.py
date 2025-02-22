"""
0_extract_jsons.py

Script that:
1. Loads all puzzles from phyre.loader
2. Creates a 'puzzle_jsons' directory if it doesn't exist
3. Converts each puzzle to a JSON file and saves it
4. Provides progress feedback and error reporting

Usage:
  python 0_extract_jsons.py [--output-dir OUTPUT_DIR]

Example:
  python 0_extract_jsons.py --output-dir custom_output
"""

import json
from pathlib import Path
from typing import Any, Union

import phyre.loader  # type: ignore
from loguru import logger
from tqdm import tqdm

from src.managers import ArgparseManager


def convert_puzzle_to_json(puzzle: Any) -> Union[dict, None]:
    """Convert a PhyRE puzzle to a JSON-compatible dictionary."""
    if puzzle is None or puzzle.scene is None:
        return None

    scene_width = puzzle.scene.width
    scene_height = puzzle.scene.height

    # Bodies
    bodies = []
    for body in puzzle.scene.bodies:
        body_info = {
            "position": [body.position.x, body.position.y],
            "bodyType": body.bodyType - 1,  # Adjusting index from phyre
            "angle": body.angle,
            "color": body.color,
            "shapeType": body.shapeType,
            "diameter": body.diameter,
        }

        if body.shapeType in [0, 2]:  # Polygon
            if hasattr(body, "shapes") and body.shapes[0].polygon:
                body_info["vertices"] = [
                    [v.x, v.y] for v in body.shapes[0].polygon.vertices
                ]
        elif body.shapeType == 1:  # Circle
            if hasattr(body, "shapes") and body.shapes[0].circle:
                body_info["radius"] = body.shapes[0].circle.radius
        elif body.shapeType in [3, 4]:  # Compound shape
            if hasattr(body, "shapes"):
                shapes = []
                for shape in body.shapes:
                    if shape.polygon:
                        shapes.append(
                            {
                                "type": "polygon",
                                "vertices": [
                                    [v.x, v.y] for v in shape.polygon.vertices
                                ],
                            }
                        )
                body_info["shapes"] = shapes
        else:
            logger.warning(f"Unexpected shapeType: {body.shapeType}")

        bodies.append(body_info)

    # Relationship
    relationship = {
        "bodyId1": puzzle.bodyId1,
        "bodyId2": puzzle.bodyId2,
        "relationships": [(r - 6) for r in puzzle.relationships],
    }

    # Basic tier mapping
    tier_mapping = {"BALL": 0, "TWO_BALLS": 1}
    if puzzle.tier not in tier_mapping:
        return None

    # Metadata
    metadata = {
        "description": puzzle.description,
        "tier": tier_mapping[puzzle.tier],
    }

    return {
        "scene_dimensions": [scene_width, scene_height],
        "bodies": bodies,
        "relationship": relationship,
        "metadata": metadata,
    }


def save_puzzle_json(puzzle_data: dict, puzzle_id: str, output_dir: Path) -> None:
    """Save puzzle data to a JSON file."""
    filename = f"{puzzle_id.replace(':', '_')}.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(puzzle_data, f, indent=2)


def main() -> None:
    # Parse arguments
    parser = ArgparseManager("Extract PhyRE puzzles to individual JSON files.")
    parser.add_io_args(output_folder="puzzle_jsons")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Load all puzzles
    logger.info("Loading PhyRE puzzles...")
    all_puzzles = phyre.loader.load_compiled_task_dict()
    logger.info(f"Loaded {len(all_puzzles)} puzzles")

    # Process puzzles
    processed = 0
    skipped = 0
    errors = 0

    for puzzle_id, puzzle in tqdm(all_puzzles.items(), desc="Processing puzzles"):
        try:
            puzzle_data = convert_puzzle_to_json(puzzle)
            if puzzle_data is None:
                skipped += 1
                continue

            save_puzzle_json(puzzle_data, puzzle_id, output_dir)
            processed += 1

        except Exception as e:
            logger.error(f"Error processing puzzle {puzzle_id}: {e}")
            errors += 1

    # Report results
    logger.info("Processing complete:")
    logger.info(f"- Processed: {processed}")
    logger.info(f"- Skipped: {skipped}")
    logger.info(f"- Errors: {errors}")
    logger.info(f"JSON files saved to '{output_dir}'")


if __name__ == "__main__":
    main()
