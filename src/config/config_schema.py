import json
from pathlib import Path

from jsonschema import ValidationError, validate
from tqdm import tqdm

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "scene_dimensions": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0},
            "minItems": 2,
            "maxItems": 2,
        },
        "bodies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "bodyType": {"type": "integer", "minimum": 0, "maximum": 1},
                    "angle": {"type": "number"},
                    "color": {"type": "integer", "minimum": 0, "maximum": 6},
                    "shapeType": {"type": "integer", "minimum": 0, "maximum": 7},
                    "diameter": {"type": "number", "minimum": 0},
                    "vertices": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 2,
                            "maxItems": 2,
                        },
                    },
                    "radius": {"type": "number", "minimum": 0},
                },
                "required": ["position", "bodyType", "angle", "color", "shapeType"],
                "anyOf": [
                    {"required": ["diameter"]},
                    {"required": ["radius"]},
                    {"required": ["vertices"]},
                ],
            },
        },
        "relationship": {
            "type": "object",
            "properties": {
                "bodyId1": {"type": "integer", "minimum": 0},
                "bodyId2": {"type": "integer", "minimum": 0},
                "relationships": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 0, "maximum": 2},
                },
            },
            "required": ["bodyId1", "bodyId2", "relationships"],
        },
        "metadata": {
            "type": "object",
            "properties": {
                "description": {"type": "string"},
                "tier": {"type": "integer", "minimum": 0, "maximum": 3},
            },
            "required": ["description", "tier"],
        },
    },
    "required": ["scene_dimensions", "bodies", "relationship", "metadata"],
}


def validate_config(config) -> bool:
    try:
        validate(instance=config, schema=CONFIG_SCHEMA)
        return True
    except ValidationError:
        return False


# Main execution
if __name__ == "__main__":
    task_jsons_dir = Path("task_jsons")
    json_files = list(task_jsons_dir.glob("*.json"))

    for json_file in tqdm(json_files, desc="Validating JSON files"):
        with json_file.open() as f:
            config = json.load(f)

        if not validate_config(config):
            print(f"\nValidation failed for file: {json_file.name}")
            print("Stopping validation process.")
            break
    else:
        print("\nAll files passed validation successfully.")
        print("\nAll files passed validation successfully.")
