import base64
from typing import Any

from src.utils.const import (
    COLORS,
    MAX_BODIES_TO_DESCRIBE,
    PROMPT_COT,
    PROMPT_DETAILED,
    PROMPT_DIRECT,
    STATIC_BODY,
)
from src.utils.db_schemas import SampleData
from src.utils.prompts import SYSTEM_TEMPLATE, USER_TEMPLATES


class PromptManager:
    """
    This manager creates system + user prompt messages by substituting placeholders
    in a provided template with puzzle/proposal data.

    Usage:
      1. Provide a template with placeholders (e.g. "{{RADIUS}}" or "<POS_X>")
      2. Provide a dictionary with values to fill in.
      3. Build the final system message, user message, or both.
    """

    def __init__(
        self,
        system_template: str = SYSTEM_TEMPLATE,
        user_template: str | None = None,
        prompt_type: str = PROMPT_DIRECT,
    ) -> None:
        """
        Args:
            system_template: The system-level template string. E.g. "You are a physics solver..."
            user_template:   The user prompt template string.
            prompt_type:     The type of prompt to use (DIRECT, DETAILED, or COT)
        """
        self.system_template = system_template
        self.prompt_type = prompt_type

        # Use provided user_template if given, otherwise select from built-in templates
        if user_template:
            self.user_template = user_template
        else:
            self.user_template = USER_TEMPLATES.get(
                prompt_type, USER_TEMPLATES[PROMPT_DIRECT]
            )

    def build_prompt(
        self,
        sample: SampleData,
        insert_few_shot: bool = False,
        prompt_type: str | None = None,
    ) -> dict[str, str]:
        """
        Builds the final prompt (system + user) given a SampleData object.

        Args:
            sample: SampleData object containing puzzle, proposal, images and optional few-shots.
            insert_few_shot: Whether to include few-shot examples in the prompt.
            prompt_type: Override the default prompt type (DIRECT, DETAILED, or COT)

        Returns:
            {
              "system": <final system message str>,
              "user":   <final user message str>
            }
        """
        current_prompt_type = prompt_type or self.prompt_type
        user_template = USER_TEMPLATES.get(current_prompt_type, self.user_template)

        # Build dictionary of known placeholders
        fill_dict = self._extract_values(
            sample.puzzle.dict(), sample.proposal.dict(), sample.images
        )

        # Handle few-shot examples
        few_shot_str = ""
        if insert_few_shot and sample.few_shot:
            few_shot_str = self._build_few_shot_string(
                [fs.dict() for fs in sample.few_shot], current_prompt_type
            )

        # Fill templates
        filled_system = self._fill_template(
            self.system_template, fill_dict, few_shot_str
        )
        filled_user = self._fill_template(user_template, fill_dict, few_shot_str)

        return {"system": filled_system, "user": filled_user}

    def build_openai_messages(
        self,
        sample: SampleData,
        insert_few_shot: bool = False,
        prompt_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Builds the final prompt as a list of OpenAI API-compatible messages.

        Args:
            sample: SampleData object containing puzzle, proposal, images and optional few-shots.
            insert_few_shot: Whether to include few-shot examples in the prompt.
            prompt_type: Override the default prompt type (DIRECT, DETAILED, or COT)

        Returns:
            A list of message dictionaries compatible with OpenAI API format.
        """
        prompt = self.build_prompt(sample, insert_few_shot, prompt_type)

        messages = [{"role": "system", "content": prompt["system"]}]

        # Handle images in the user message
        user_content = []

        # Add text content
        user_content.append({"type": "text", "text": prompt["user"]})

        # Add images if available as base64
        for image_path in sample.images:
            with open(image_path, "rb") as f:
                img_data = f.read()
                encoded_img = base64.b64encode(img_data).decode("utf-8")
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded_img}",
                            "detail": "high",
                        },
                    }
                )

        messages.append({"role": "user", "content": user_content})
        return messages

    def _extract_values(
        self,
        puzzle_data: dict[str, Any],
        proposal_data: dict[str, Any],
        images: list[str],
    ) -> dict[str, str]:
        """
        Extract values from puzzle and proposal data to fill template placeholders.
        """
        fill_values = {}

        # Process images
        if images:
            fill_values["IMAGES"] = ", ".join(images)
        else:
            fill_values["IMAGES"] = "No images found"

        # Extract relationship information to identify target objects
        if "relationship" in puzzle_data and "bodies" in puzzle_data:
            rel = puzzle_data["relationship"]
            bodies = puzzle_data["bodies"]

            # Get the two objects that should come into contact
            if len(bodies) > rel["bodyId1"] and len(bodies) > rel["bodyId2"]:
                obj1 = bodies[rel["bodyId1"]]
                obj2 = bodies[rel["bodyId2"]]

                obj1_type = self._get_object_type(obj1)
                obj2_type = self._get_object_type(obj2)

                obj1_color = COLORS.get(obj1.get("color", 0), "unknown color")
                obj2_color = COLORS.get(obj2.get("color", 0), "unknown color")

                fill_values["TARGET_OBJ1"] = f"{obj1_color} {obj1_type}"
                fill_values["TARGET_OBJ2"] = f"{obj2_color} {obj2_type}"
                fill_values["RELATION"] = "come into contact"

        # Create a custom description based on metadata or generate one
        if "metadata" in puzzle_data and puzzle_data["metadata"].get("description"):
            fill_values["CUSTOM_DESCRIPTION"] = puzzle_data["metadata"]["description"]
        else:
            fill_values["CUSTOM_DESCRIPTION"] = self._generate_description(puzzle_data)

        return fill_values

    def _get_object_type(self, obj_data: dict) -> str:
        """Determine object type based on its properties"""
        if obj_data.get("shape_type") == 1:  # Circle
            return "ball"
        elif obj_data.get("shape_type") == 0:  # Polygon
            # Simplistic rectangle detection - could be enhanced
            return "rectangle"
        elif obj_data.get("shape_type") == 3:  # Custom shape
            return "object"
        else:
            return "object"

    def _generate_description(self, puzzle_data: dict) -> str:
        """Generate a description of the puzzle if none is provided"""
        if "metadata" not in puzzle_data or "bodies" not in puzzle_data:
            return "A physics puzzle with multiple objects."

        bodies = puzzle_data["bodies"]
        static_count = sum(1 for b in bodies if b.get("body_type") == STATIC_BODY)
        dynamic_count = len(bodies) - static_count

        description = f"The scene contains {len(bodies)} objects: {static_count} static and {dynamic_count} dynamic."

        # Add more details for small number of bodies
        if len(bodies) <= MAX_BODIES_TO_DESCRIBE:
            details = []
            for i, body in enumerate(bodies[:MAX_BODIES_TO_DESCRIBE]):
                body_type = (
                    "static" if body.get("body_type") == STATIC_BODY else "dynamic"
                )
                shape_type = self._get_object_type(body)
                color = COLORS.get(body.get("color", 0), "unknown color")
                details.append(f"Object {i+1}: A {color} {shape_type} ({body_type})")

            description += " " + " ".join(details)

        return description

    def _build_few_shot_string(
        self, few_shot_examples: list[dict[str, Any]], prompt_type: str = PROMPT_DIRECT
    ) -> str:
        """
        Convert the list of few-shot exemplars to a textual snippet.
        Format depends on the prompt type for consistent examples.
        """
        if not few_shot_examples:
            return ""

        lines = ["### Examples:"]

        for i, ex in enumerate(few_shot_examples, start=1):
            puzzle = ex.get("puzzle", {})
            proposal = ex.get("proposal", {})
            images = ex.get("images", [])

            # Create a description based on the prompt type
            if prompt_type == PROMPT_COT:
                # For CoT, include detailed reasoning
                lines.append(f"Example {i}:")
                lines.append(
                    f"Puzzle description: {puzzle.get('metadata', {}).get('description', 'A physics puzzle.')}"
                )
                lines.append(f"Images: {', '.join(images) if images else 'No images'}")
                lines.append(
                    f"Analysis: {proposal.get('reasoning', 'No reasoning provided')}"
                )
                lines.append(
                    f"Prediction: {'Success' if proposal.get('is_successful', False) else 'Failure'}"
                )
                lines.append(
                    f"Explanation: {proposal.get('explanation', 'No explanation provided')}"
                )
            elif prompt_type == PROMPT_DETAILED:
                # For detailed, include more context but less reasoning
                lines.append(f"Example {i}:")
                lines.append(
                    f"Puzzle description: {puzzle.get('metadata', {}).get('description', 'A physics puzzle.')}"
                )
                lines.append(f"Images: {', '.join(images) if images else 'No images'}")
                lines.append(
                    f"Prediction: {'Success' if proposal.get('is_successful', False) else 'Failure'}"
                )
                lines.append(
                    f"Reason: {proposal.get('explanation', 'No explanation provided')}"
                )
            else:
                # For direct, just include minimal information
                lines.append(f"Example {i}:")
                lines.append(f"Images: {', '.join(images) if images else 'No images'}")
                lines.append(
                    f"Prediction: {'Success' if proposal.get('is_successful', False) else 'Failure'}"
                )

        return "\n".join(lines)

    def _fill_template(
        self, template_str: str, fill_dict: dict[str, str], few_shot_str: str
    ) -> str:
        """
        Simple placeholder substitution.
        This example looks for <PLACEHOLDER> or {{PLACEHOLDER}}.
        """
        filled = template_str

        # 1) Insert the main placeholders
        for key, val in fill_dict.items():
            filled = filled.replace(f"<{key}>", str(val))
            filled = filled.replace(f"{{{{{key}}}}}", str(val))

        # 2) Insert few_shot_str if there's a placeholder for it
        if "<FEW_SHOT>" in filled:
            filled = filled.replace("<FEW_SHOT>", few_shot_str)
        elif "{{FEW_SHOT}}" in filled:
            filled = filled.replace("{{FEW_SHOT}}", few_shot_str)
        elif few_shot_str:
            # If no placeholder exists but we have few shot examples, append them
            filled = f"{filled}\n\n{few_shot_str}"

        return filled
