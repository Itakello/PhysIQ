"""
0_extract_jsons.py

Script that:
1. Loads all tasks from phyre.loader
2. Creates a 'task_jsons' directory if it doesn't exist
3. Converts each task to a JSON file and saves it
4. Provides progress feedback and error reporting

Usage:
  python 0_extract_jsons.py [--output-dir OUTPUT_DIR]

Example:
  python 0_extract_jsons.py --output-dir custom_output
"""

import argparse
import json
from pathlib import Path
from typing import Union

import phyre.loader
from loguru import logger
from tqdm import tqdm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract PhyRE tasks to individual JSON files."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="task_jsons",
        help="Directory where JSON files will be saved (default: task_jsons)",
    )
    return parser.parse_args()


def convert_task_to_json(task) -> Union[dict, None]:
    """Convert a PhyRE task to a JSON-compatible dictionary."""
    if task is None or task.scene is None:
        return None

    scene_width = task.scene.width
    scene_height = task.scene.height

    # Bodies
    bodies = []
    for body in task.scene.bodies:
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
        "bodyId1": task.bodyId1,
        "bodyId2": task.bodyId2,
        "relationships": [(r - 6) for r in task.relationships],
    }

    # Basic tier mapping
    tier_mapping = {"BALL": 0, "TWO_BALLS": 1}
    if task.tier not in tier_mapping:
        return None

    # Metadata
    metadata = {
        "description": task.description,
        "tier": tier_mapping[task.tier],
    }

    return {
        "scene_dimensions": [scene_width, scene_height],
        "bodies": bodies,
        "relationship": relationship,
        "metadata": metadata,
    }


def save_task_json(task_data: dict, task_id: str, output_dir: Path) -> None:
    """Save task data to a JSON file."""
    filename = f"{task_id.replace(':', '_')}.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(task_data, f, indent=2)


def main() -> None:
    # Parse arguments
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Load all tasks
    logger.info("Loading PhyRE tasks...")
    all_tasks = phyre.loader.load_compiled_task_dict()
    logger.info(f"Loaded {len(all_tasks)} tasks")

    # Process tasks
    processed = 0
    skipped = 0
    errors = 0

    for task_id, task in tqdm(all_tasks.items(), desc="Processing tasks"):
        try:
            task_data = convert_task_to_json(task)
            if task_data is None:
                skipped += 1
                continue

            save_task_json(task_data, task_id, output_dir)
            processed += 1

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            errors += 1

    # Report results
    logger.info(f"Processing complete:")
    logger.info(f"- Processed: {processed}")
    logger.info(f"- Skipped: {skipped}")
    logger.info(f"- Errors: {errors}")
    logger.info(f"JSON files saved to '{output_dir}'")


if __name__ == "__main__":
    main()
