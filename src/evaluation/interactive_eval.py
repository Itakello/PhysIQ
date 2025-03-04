"""
Module for evaluating interactive ball placement responses from the LLM.
"""

import copy
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from src.managers import SimulationManager
from src.utils.const import MAX_RADIUS, MIN_RADIUS, SCENE_DIMENSIONS
from src.utils.prompts import INTERACTIVE_RESPONSE_TEMPLATES


@dataclass
class InteractiveEvalResult:
    """Result of an interactive evaluation."""

    status: str
    message: str
    ball_data: dict | None = None
    screenshots: list[str] | None = None  # Changed to list of file paths


def extract_json_from_response(response: str) -> dict | None:
    """
    Extract JSON object from model response text.

    Args:
        response: Model response text that may contain JSON

    Returns:
        Parsed JSON object or None if extraction fails
    """
    # Try to extract JSON using regex pattern
    json_pattern = r"```(?:json)?\s*({[\s\S]*?})\s*```"
    match = re.search(json_pattern, response)

    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from extracted string: {json_str}")
            return None

    # If no JSON code block, try parsing the whole response as JSON
    try:
        # Remove any markdown formatting that might interfere
        cleaned = re.sub(r"[\s\S]*?({[\s\S]*?})[\s\S]*", r"\1", response)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Could not extract valid JSON from the response")
        return None


def validate_ball_position(ball_data: dict) -> tuple[bool, str]:
    """
    Check if the ball position and radius are valid within the scene boundaries.

    Args:
        ball_data: Dictionary containing x, y position and radius

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Convert possible string values to float
        x = float(ball_data.get("x", -1))
        y = float(ball_data.get("y", -1))
        radius = float(ball_data.get("radius", -1))

        # Check if values are within bounds
        if radius < MIN_RADIUS or radius > MAX_RADIUS:
            return (
                False,
                f"Radius {radius} is out of bounds [{MIN_RADIUS}, {MAX_RADIUS}]",
            )

        # Check if ball is fully inside the scene
        if (
            x - radius < 0
            or x + radius > SCENE_DIMENSIONS[0]
            or y - radius < 0
            or y + radius > SCENE_DIMENSIONS[1]
        ):
            return (
                False,
                f"Ball position ({x}, {y}) with radius {radius} is outside scene boundaries",
            )

        return True, ""
    except ValueError:
        return False, "Invalid numerical values in ball data"


def create_ball_proposal(ball_data: dict) -> dict:
    """
    Create a ball proposal document to be added to the puzzle.

    Args:
        ball_data: Dictionary containing x, y position and radius

    Returns:
        Ball document compatible with the puzzle schema
    """
    x = float(ball_data.get("x", 0))
    y = float(ball_data.get("y", 0))
    radius = float(ball_data.get("radius", MIN_RADIUS))

    return {
        "body_type": 1,  # dynamic
        "position": [x, y],
        "angle": 0.0,
        "color": 0,  # color index for red
        "shape_type": 1,  # circle
        "radius": radius,
        "proposal": True,
    }


def evaluate_interactive_response(
    response: str, puzzle: dict, visualize: bool = False, num_screenshots: int = 0
) -> InteractiveEvalResult:
    """
    Evaluate an LLM's interactive response by extracting the ball placement,
    validating it, and running a simulation.

    Args:
        response: Model's response text
        puzzle: Original puzzle document
        visualize: Whether to show visualization
        num_screenshots: Number of screenshots to take

    Returns:
        InteractiveEvalResult with status and additional information
    """
    # Extract ball data from response
    ball_data = extract_json_from_response(response)

    if ball_data is None:
        return InteractiveEvalResult(
            status="GOAL_NOT_REACHED",
            message="Failed to extract valid JSON ball data from response",
        )

    # Validate ball position
    is_valid, error_message = validate_ball_position(ball_data)
    if not is_valid:
        return InteractiveEvalResult(
            status="OUTSIDE_BOUNDARIES",
            message=error_message,
            ball_data=ball_data,
        )

    # Create ball proposal and add to puzzle
    ball_doc = create_ball_proposal(ball_data)

    # Create a deep copy of the puzzle to avoid modifying the original
    tmp_puzzle = copy.deepcopy(puzzle)
    tmp_puzzle["bodies"].append(ball_doc)

    # Run simulation
    simulation_manager = SimulationManager()

    try:
        goal_reached, pil_screenshots = simulation_manager.run_simulation(
            puzzle=tmp_puzzle, visualize=visualize, num_screenshots=num_screenshots
        )
    except ValueError as e:
        # Overlapping objects cause ValueError
        return InteractiveEvalResult(
            status="OVERLAPPING",
            message=f"Ball overlaps with existing objects: {str(e)}",
            ball_data=ball_data,
        )

    # Convert PIL images to file paths by saving them to disk
    screenshot_paths = []
    if pil_screenshots:
        # Create a temporary directory for screenshots if it doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "physiq_screenshots"
        os.makedirs(temp_dir, exist_ok=True)

        # Save each screenshot to disk
        for i, img in enumerate(pil_screenshots):
            file_path = temp_dir / f"screenshot_{puzzle.get('id', 'unknown')}_{i}.png"
            img.save(file_path)
            screenshot_paths.append(str(file_path))

    # Return result based on goal achievement
    if goal_reached:
        return InteractiveEvalResult(
            status="GOAL_REACHED",
            message="Goal successfully reached",
            ball_data=ball_data,
            screenshots=screenshot_paths,
        )
    else:
        return InteractiveEvalResult(
            status="GOAL_NOT_REACHED",
            message="Goal not reached with the proposed ball placement",
            ball_data=ball_data,
            screenshots=screenshot_paths,
        )


def generate_feedback_message(status: str, attempt_number: int) -> str:
    """
    Generate feedback message for interactive LLM responses based on status.

    Args:
        status: The evaluation status (GOAL_REACHED, GOAL_NOT_REACHED, etc.)
        attempt_number: Current attempt number (1-5)

    Returns:
        Formatted feedback message
    """
    template = INTERACTIVE_RESPONSE_TEMPLATES.get(status, "Unknown status. Try again.")
    next_attempt = min(attempt_number + 1, 5)

    # For successful attempts, no need to include attempt number
    if status == "GOAL_REACHED":
        return template

    # Debug: Print the template and next attempt
    # print(f"DEBUG - Template for {status}: {template}")
    # print(f"DEBUG - Next attempt: {next_attempt}")

    # For other statuses, just replace the attempt placeholder
    formatted_message = template.format(attempt=next_attempt)

    # Debug: Print the formatted message
    # print(f"DEBUG - Formatted message: {formatted_message}")

    return formatted_message
