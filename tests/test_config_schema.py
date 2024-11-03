import json
import unittest

from jsonschema import ValidationError, validate

from src.config.config_schema import CONFIG_SCHEMA


class TestConfigSchema(unittest.TestCase):

    def test_valid_config(self) -> None:
        with open("configurations/gravity_1.json", "r") as f:
            valid_config = json.load(f)
        try:
            validate(instance=valid_config, schema=CONFIG_SCHEMA)
        except ValidationError:
            self.fail("Valid configuration failed schema validation")

    def test_invalid_level(self) -> None:
        invalid_config = {
            "level": 0,  # Invalid: minimum is 1
            "category": "gravity",
            "screen_size": {"width": 600, "height": 600},
            "constants": {
                "main_shape": "circle",
                "obstacles": [[50, 200, 100, 200]],
                "gravity": 9.81,
            },
            "variables": [
                {
                    "interested_object": {
                        "type": "circle",
                        "position": {"x": 100, "y": 300},
                        "size": 10,
                    },
                    "moving_objects": [],
                    "goal_area": {
                        "type": "container",
                        "position": {"x": 200, "y": 50},
                        "dimensions": {"width": 30, "height": 30},
                    },
                }
            ],
        }
        with self.assertRaises(ValidationError):
            validate(instance=invalid_config, schema=CONFIG_SCHEMA)

    def test_invalid_screen_size(self):
        invalid_config = {
            "level": 1,
            "category": "gravity",
            "screen_size": {"width": 1001, "height": 600},  # Invalid: width > 1000
            "constants": {
                "main_shape": "circle",
                "obstacles": [[50, 200, 100, 200]],
                "gravity": 9.81,
            },
            "variables": [
                {
                    "interested_object": {
                        "type": "circle",
                        "position": {"x": 100, "y": 300},
                        "size": 10,
                    },
                    "moving_objects": [],
                    "goal_area": {
                        "type": "container",
                        "position": {"x": 200, "y": 50},
                        "dimensions": {"width": 30, "height": 30},
                    },
                }
            ],
        }
        with self.assertRaises(ValidationError):
            validate(instance=invalid_config, schema=CONFIG_SCHEMA)

    def test_invalid_obstacle(self):
        invalid_config = {
            "level": 1,
            "category": "gravity",
            "screen_size": {"width": 600, "height": 600},
            "constants": {
                "main_shape": "circle",
                "obstacles": [[50, 200, 100]],  # Invalid: should have 4 items
                "gravity": 9.81,
            },
            "variables": [
                {
                    "interested_object": {
                        "type": "circle",
                        "position": {"x": 100, "y": 300},
                        "size": 10,
                    },
                    "moving_objects": [],
                    "goal_area": {
                        "type": "container",
                        "position": {"x": 200, "y": 50},
                        "dimensions": {"width": 30, "height": 30},
                    },
                }
            ],
        }
        with self.assertRaises(ValidationError):
            validate(instance=invalid_config, schema=CONFIG_SCHEMA)

    def test_invalid_position(self):
        invalid_config = {
            "level": 1,
            "category": "gravity",
            "screen_size": {"width": 600, "height": 600},
            "constants": {
                "main_shape": "circle",
                "obstacles": [[50, 200, 100, 200]],
                "gravity": 9.81,
            },
            "variables": [
                {
                    "interested_object": {
                        "type": "circle",
                        "position": {"x": 601, "y": 300},  # Invalid: x > screen width
                        "size": 10,
                    },
                    "moving_objects": [],
                    "goal_area": {
                        "type": "container",
                        "position": {"x": 200, "y": 50},
                        "dimensions": {"width": 30, "height": 30},
                    },
                }
            ],
        }
        with self.assertRaises(ValidationError):
            validate(instance=invalid_config, schema=CONFIG_SCHEMA)


if __name__ == "__main__":
    unittest.main()
    unittest.main()
