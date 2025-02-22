"""
1_move_to_db.py

Script that:
1. Connects to a local MongoDB database (db_name specified as argument)
2. Reads all JSON files from the puzzle_jsons directory
3. Converts each JSON file to a puzzle document
4. Inserts each puzzle into the 'puzzles' collection

Usage:
  python 1_move_to_db.py <db_name> [--input-dir INPUT_DIR]

Example:
  python 1_move_to_db.py physiq_db --input-dir puzzle_jsons
"""

import json
from pathlib import Path

from loguru import logger
from tqdm import tqdm

from src.managers import ArgparseManager, MongoDBManager
from src.utils.db_schemas import (
    BodyData,
    MetadataData,
    PuzzleSchema,
    RelationshipData,
    ShapeData,
)


def load_puzzle_from_json(json_path: Path) -> dict:
    """Load and parse a puzzle JSON file."""
    with open(json_path) as f:
        puzzle_dict = json.load(f)

    # Add puzzle_id from filename
    puzzle_id = json_path.stem.replace("_", ":")
    puzzle_dict["id"] = puzzle_id

    puzzle_dict["metadata"]["type"] = "PHYRE"

    # Add puzzle_type from metadata tier
    puzzle_dict["metadata"]["tier"] = ["BALL", "TWO_BALLS"][
        puzzle_dict["metadata"]["tier"]
    ]

    return puzzle_dict


def main() -> None:
    parser = ArgparseManager("Create a MongoDB database from JSON puzzle files.")
    parser.add_common_db_args()
    parser.add_io_args(input_folder="puzzle_jsons")
    args = parser.parse_args()
    input_dir = Path(args.input_dir)

    if not input_dir.exists():
        logger.error(f"Input directory '{input_dir}' does not exist!")
        return

    # Initialize DB Manager
    db_manager = MongoDBManager(db_name=args.db_name)

    # Get all JSON files
    json_files = list(input_dir.glob("*.json"))
    logger.info(f"Found {len(json_files)} JSON files in {input_dir}")

    # Process each JSON file
    inserted_count = 0
    for json_path in tqdm(json_files, desc="Processing puzzles"):
        try:
            puzzle_dict = load_puzzle_from_json(json_path)

            # Convert to Pydantic objects
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
                        position=bd.get("position"),
                        body_type=bd.get("bodyType"),
                        angle=bd.get("angle"),
                        color=bd.get("color"),
                        shape_type=bd.get("shapeType"),
                        vertices=bd.get("vertices"),
                        diameter=bd.get("diameter"),
                        radius=bd.get("radius"),
                        shapes=shapes_data if shapes_data else None,
                    )
                )

            relationship_data = RelationshipData(**puzzle_dict["relationship"])
            metadata_data = MetadataData(**puzzle_dict["metadata"])

            puzzle_schema = PuzzleSchema(
                id=puzzle_dict["id"],
                bodies=bodies_data,
                relationship=relationship_data,
                metadata=metadata_data,
            )

            # Insert into database
            db_manager.insert_puzzle(puzzle_schema)
            inserted_count += 1

        except Exception as e:
            logger.error(f"Error processing {json_path.name}: {e}")

    logger.info(f"Inserted {inserted_count} puzzle documents into '{args.db_name}'.")
    db_manager.close_connection()


if __name__ == "__main__":
    main()
