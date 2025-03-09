"""
Module for evaluating interactive ball placement responses from the LLM.
"""

import copy
import json
import os
import re
import tempfile
from pathlib import Path

from loguru import logger

from src.managers import SimulationManager
from src.utils.const import MAX_RADIUS, MIN_RADIUS, SCENE_DIMENSIONS
from src.utils.db_schemas import InteractiveEvalResult
from src.utils.prompts import INTERACTIVE_RESPONSE_TEMPLATES


def extract_json_from_response(response: str) -> dict | list[dict] | None:
    """
    Extract JSON object or array from model response text.

    Args:
        response: Model response text that may contain JSON

    Returns:
        Parsed JSON object, array of objects, or None if extraction fails
    """
    # Try to extract JSON using regex pattern for both object and array
    json_pattern = r"```(?:json)?\s*([\[\{][\s\S]*?[\]\}])\s*```"
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
        cleaned = re.sub(r"[\s\S]*?([\[\{][\s\S]*?[\]\}])[\s\S]*", r"\1", response)
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Could not extract valid JSON from the response")
        return None


def validate_ball_position(ball_data: dict | list[dict]) -> tuple[bool, str]:
    """
    Check if the ball position and radius are valid within the scene boundaries.

    Args:
        ball_data: Dictionary containing x, y position and radius,
                  or a list of such dictionaries for multiple balls

    Returns:
        Tuple of (is_valid, error_message)
    """
    # If it's a list of balls, validate each one
    if isinstance(ball_data, list):
        for i, ball in enumerate(ball_data, 1):
            is_valid, error_message = validate_single_ball_position(ball)
            if not is_valid:
                return False, f"Ball {i}: {error_message}"

        # If we have 2 balls, check if they overlap with each other
        if len(ball_data) >= 2:
            for i in range(len(ball_data)):
                for j in range(i + 1, len(ball_data)):
                    ball1 = ball_data[i]
                    ball2 = ball_data[j]

                    x1 = float(ball1.get("x", -1))
                    y1 = float(ball1.get("y", -1))
                    r1 = float(ball1.get("radius", -1))

                    x2 = float(ball2.get("x", -1))
                    y2 = float(ball2.get("y", -1))
                    r2 = float(ball2.get("radius", -1))

                    # Check if balls overlap
                    distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                    if distance < (r1 + r2):
                        return False, f"Balls {i+1} and {j+1} overlap with each other"

        return True, ""
    else:
        # Single ball validation
        return validate_single_ball_position(ball_data)


def validate_single_ball_position(ball_data: dict) -> tuple[bool, str]:
    """
    Check if a single ball position and radius are valid within the scene boundaries.

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


def create_ball_proposal(ball_data: dict | list[dict]) -> dict | list[dict]:
    """
    Create a ball proposal document to be added to the puzzle.

    Args:
        ball_data: Dictionary containing x, y position and radius,
                  or a list of such dictionaries for multiple balls

    Returns:
        Ball document(s) compatible with the puzzle schema
    """
    if isinstance(ball_data, list):
        return [create_single_ball_proposal(ball) for ball in ball_data]
    else:
        return create_single_ball_proposal(ball_data)


def create_single_ball_proposal(ball_data: dict) -> dict:
    """
    Create a single ball proposal document.

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
    Evaluate an LLM's interactive response by extracting the ball placement(s),
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
        # Determine if this is a single or two-ball task based on metadata
        is_two_ball = puzzle.get("metadata", {}).get("tier", "").startswith("TWO_BALLS")
        status = (
            "JSON_INCORRECT_FORMAT_TWO_BALL" if is_two_ball else "JSON_INCORRECT_FORMAT"
        )

        return InteractiveEvalResult(
            status=status,
            message="Failed to extract valid JSON ball data from response",
        )

    # Check if we need a list for two-ball puzzles or a single dict for one-ball puzzles
    is_two_ball = puzzle.get("metadata", {}).get("tier", "").startswith("TWO_BALLS")
    is_list = isinstance(ball_data, list)

    if is_two_ball and not is_list:
        return InteractiveEvalResult(
            status="JSON_INCORRECT_FORMAT_TWO_BALL",
            message="Expected a list of two balls but received a single ball",
            ball_data=ball_data,
        )
    elif not is_two_ball and is_list:
        return InteractiveEvalResult(
            status="JSON_INCORRECT_FORMAT",
            message="Expected a single ball but received multiple balls",
            ball_data=ball_data,
        )

    # Validate ball position(s)
    is_valid, error_message = validate_ball_position(ball_data)
    if not is_valid:
        status = "OUTSIDE_BOUNDARIES_TWO_BALL" if is_two_ball else "OUTSIDE_BOUNDARIES"
        # Check if error message mentions overlap
        if "overlap" in error_message.lower():
            status = "OVERLAPPING_TWO_BALL" if is_two_ball else "OVERLAPPING"

        return InteractiveEvalResult(
            status=status,
            message=error_message,
            ball_data=ball_data,
        )

    # Create ball proposal(s) and add to puzzle
    ball_docs = create_ball_proposal(ball_data)

    # Create a deep copy of the puzzle to avoid modifying the original
    tmp_puzzle = copy.deepcopy(puzzle)

    # Add the ball(s) to the puzzle
    if isinstance(ball_docs, list):
        for ball_doc in ball_docs:
            tmp_puzzle["bodies"].append(ball_doc)
    else:
        tmp_puzzle["bodies"].append(ball_docs)

    # Run simulation
    simulation_manager = SimulationManager()

    try:
        goal_reached, pil_screenshots = simulation_manager.run_simulation(
            puzzle=tmp_puzzle, visualize=visualize, num_screenshots=num_screenshots
        )
    except ValueError as e:
        # Overlapping objects cause ValueError
        status = "OVERLAPPING_TWO_BALL" if is_two_ball else "OVERLAPPING"
        return InteractiveEvalResult(
            status=status,
            message=f"Ball{'s' if is_two_ball else ''} overlap{'s' if not is_two_ball else ''} with existing objects: {str(e)}",
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
            message=f"Goal not reached with the proposed ball placement{'s' if is_two_ball else ''}",
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

    # For other statuses, just replace the attempt placeholder
    formatted_message = template.format(attempt=next_attempt)

    return formatted_message
