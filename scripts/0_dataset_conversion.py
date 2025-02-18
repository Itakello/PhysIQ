"""
0_dataset_conversion.py

Script that:
1. Connects to a local MongoDB database (db_name specified as single argument).
2. Loads all tasks from phyre.loader.
3. Converts each task to a puzzle dict (similar to extract_jsons.py).
4. Inserts each puzzle into the 'puzzles' collection in the specified database.

Usage:
  python 0_dataset_conversion.py <db_name>

Example:
  python 0_dataset_conversion.py physiq_db
"""

import argparse

import phyre.loader
from loguru import logger

from src.managers.db_manager import MongoDBManager
from src.utils.db_schemas import (
    BodyData,
    MetadataData,
    PuzzleSchema,
    RelationshipData,
    ShapeData,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create a MongoDB database and insert puzzle data from PhyRE tasks."
    )
    parser.add_argument(
        "db_name", type=str, help="Name of the MongoDB database to be created/used."
    )
    return parser.parse_args()


def convert_task_to_json(task) -> dict:
    """
    Converts a PhyRE task to a JSON-like dict with all relevant fields.
    Similar to the old extract_jsons.py logic.
    """

    if task is None or task.scene is None:
        return {}

    scene_width = task.scene.width
    scene_height = task.scene.height

    # Bodies
    bodies = []
    for body in task.scene.bodies:
        body_info = {
            "position": [body.position.x, scene_height - body.position.y],
            "bodyType": body.bodyType - 1,  # Adjusting index from phyre
            "angle": body.angle,
            "color": body.color,
            "shapeType": body.shapeType,
            "diameter": body.diameter,
        }

        # Polygons
        if body.shapeType in [0, 2] and hasattr(body, "shapes"):
            # Typically shapeType=0 or 2 => polygons
            polygon_vertices = []
            if getattr(body, "shapes"):
                shape = body.shapes[0]
                if getattr(shape, "polygon", None):
                    polygon_vertices = [[v.x, v.y] for v in shape.polygon.vertices]
            body_info["vertices"] = polygon_vertices

        # Circles
        if body.shapeType == 1 and hasattr(body, "shapes"):
            # shapeType=1 => circle
            if body.shapes and body.shapes[0].circle:
                body_info["radius"] = body.shapes[0].circle.radius

        # Compound
        if body.shapeType in [3, 4] and hasattr(body, "shapes"):
            shape_list = []
            for shp in body.shapes:
                if shp.polygon:
                    shape_list.append(
                        {
                            "type": "polygon",
                            "vertices": [[v.x, v.y] for v in shp.polygon.vertices],
                        }
                    )
            body_info["shapes"] = shape_list

        bodies.append(body_info)

    # Relationship
    relationship = {
        "bodyId1": task.bodyId1,
        "bodyId2": task.bodyId2,
        "relationships": [(r - 6) for r in task.relationships],
    }

    # Basic tier mapping as example
    tier_mapping = {"BALL": 0, "TWO_BALLS": 1}
    if task.tier not in tier_mapping:
        # If a tier isn't recognized, skip
        # or set a default?
        pass

    # Metadata
    metadata = {
        "description": task.description,
        "tier": tier_mapping.get(task.tier, -1),
    }

    puzzle_data = {
        "puzzle_id": task.taskId,
        "scene_dimensions": [scene_width, scene_height],
        "bodies": bodies,
        "relationship": relationship,
        "metadata": metadata,
        # Additional example fields
        "puzzle_type": task.tier,
        "extra_info": {},
    }
    return puzzle_data


def main() -> None:
    # 1) Parse arguments
    args = parse_args()

    # 2) Initialize DB Manager
    db_manager = MongoDBManager(db_name=args.db_name)

    # 3) Load tasks
    all_tasks = phyre.loader.load_compiled_task_dict()
    logger.info(f"Total tasks in PhyRE: {len(all_tasks)}")

    # 4) Convert and insert each puzzle
    inserted_count = 0
    for task_id, task in all_tasks.items():
        try:
            puzzle_dict = convert_task_to_json(task)
            if not puzzle_dict:
                # Skip if empty or invalid
                logger.warning(f"Skipping task {task_id} due to invalid data.")
                continue

            # Build Pydantic object
            # Convert each body to BodyData, shapes if any, etc.
            bodies_data = []
            for bd in puzzle_dict["bodies"]:
                shapes_data = []
                if bd.get("shapes"):
                    for shp in bd["shapes"]:
                        shapes_data.append(
                            ShapeData(type=shp["type"], vertices=shp["vertices"])
                        )

                bodies_data.append(
                    BodyData(
                        position=bd["position"],
                        bodyType=bd["bodyType"],
                        angle=bd["angle"],
                        color=bd["color"],
                        shapeType=bd["shapeType"],
                        diameter=bd.get("diameter"),
                        radius=bd.get("radius"),
                        shapes=shapes_data if shapes_data else None,
                    )
                )

            relationship_data = RelationshipData(**puzzle_dict["relationship"])
            metadata_data = MetadataData(**puzzle_dict["metadata"])

            puzzle_schema = PuzzleSchema(
                puzzle_id=puzzle_dict["puzzle_id"],
                scene_dimensions=puzzle_dict["scene_dimensions"],
                bodies=bodies_data,
                relationship=relationship_data,
                metadata=metadata_data,
                puzzle_type=puzzle_dict.get("puzzle_type"),
                extra_info=puzzle_dict.get("extra_info"),
            )

            # Insert
            db_manager.insert_puzzle(puzzle_schema)
            inserted_count += 1

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")

    logger.info(f"Inserted {inserted_count} puzzle documents into '{args.db_name}'.")
    db_manager.close_connection()


if __name__ == "__main__":
    main()
