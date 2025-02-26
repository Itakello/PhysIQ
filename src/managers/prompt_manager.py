import base64
from typing import Any

from src.utils.const import (
    COLORS,
    DYNAMIC_BODY,
    MAX_BODIES_TO_DESCRIBE,
    PROMPT_COT,
    PROMPT_DETAILED,
    PROMPT_DIRECT,
    STATIC_BODY,
)
from src.utils.db_schemas import SampleData
from src.utils.prompts import (
    FLAT_USER_TEMPLATES,
    SYSTEM_TEMPLATE,
    SYSTEM_TEMPLATES,
    USER_TEMPLATES,
)


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
            prompt_type:     The type of prompt to use (DIRECT, DETAILED, COT, or SANITY_CHECK)
        """
        self.system_template = system_template
        self.prompt_type = prompt_type
        # Use provided user_template if given, otherwise select from built-in templates
        if user_template:
            self.user_template = user_template
        else:
            self.user_template = FLAT_USER_TEMPLATES.get(
                prompt_type, FLAT_USER_TEMPLATES[PROMPT_DIRECT]
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
            { "system": <final system message str>,
              "user":   <final user message str>
            }
        """
        current_prompt_type = prompt_type or self.prompt_type
        user_template = FLAT_USER_TEMPLATES.get(current_prompt_type, self.user_template)

        # Build dictionary of known placeholders
        fill_dict = self._extract_values(
            sample.puzzle.model_dump(), sample.proposal.model_dump(), sample.images
        )

        # Few-shot handling - removing from templates, will be handled separately
        few_shot_str = ""
        if insert_few_shot and sample.few_shot:
            few_shot_str = self._build_few_shot_string(
                [fs.model_dump() for fs in sample.few_shot], current_prompt_type
            )

        # Fill templates - don't include few_shot_str in system message
        filled_system = self._fill_template(self.system_template, fill_dict, "")
        filled_user = self._fill_template(user_template, fill_dict, few_shot_str)

        # Remove the few-shot placeholder from user template
        filled_user = filled_user.replace("<FEW_SHOT>", "")
        filled_user = filled_user.replace("{{FEW_SHOT}}", "")

        return {"system": filled_system, "user": filled_user}

    def build_openai_messages(
        self,
        sample: SampleData,
        insert_few_shot: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Builds the final prompt as a list of OpenAI API-compatible messages following:
        1. System message with instructions
        2. User message with task description and physics details
        3. Few-shot examples (if requested)
        4. Final user message with specific question and image

        Args:
            sample: SampleData object containing puzzle, proposal, images and optional few-shots.
            insert_few_shot: Whether to include few-shot examples in the prompt.
            use_images_paths: Whether to use image placeholders in the prompt.

        Returns:
            A list of message dictionaries compatible with OpenAI API format.
        """
        current_prompt_type = self.prompt_type
        template = USER_TEMPLATES.get(
            current_prompt_type, USER_TEMPLATES[PROMPT_DIRECT]
        )

        # Build dictionary of values to substitute in the templates
        fill_dict = self._extract_values(
            sample.puzzle.model_dump(), sample.proposal.model_dump(), sample.images
        )

        # 1. System message with instructions
        messages = [
            {
                "role": "system",
                "content": self._fill_template(self.system_template, fill_dict, ""),
            }
        ]

        # 2. User message with task description and physics details
        description = self._fill_template(template["description"], fill_dict, "")
        messages.append({"role": "user", "content": description})

        # 3. Add few-shot examples if requested
        if insert_few_shot and sample.few_shot:
            for fs_example in sample.few_shot:
                few_shot_messages = self._create_few_shot_messages(
                    fs_example.model_dump(), self.prompt_type
                )
                messages.extend(few_shot_messages)

        # 4. Final user message with the specific question and image
        question = self._fill_template(template["question"], fill_dict, "")
        user_content = [{"type": "text", "text": question}]

        # Add the main sample images
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
                    }  # type: ignore
                )

        messages.append({"role": "user", "content": user_content})
        return messages

    def _create_few_shot_messages(
        self, few_shot: dict[str, Any], prompt_type: str
    ) -> list[dict[str, Any]]:
        """
        Create assistant and user messages for a single few-shot example.

        Args:
            few_shot: Dictionary containing the few-shot example data
            prompt_type: The type of prompt being used

        Returns:
            A list of message dictionaries for this few-shot example
        """
        messages = []

        # Extract data
        puzzle = few_shot.get("puzzle", {})
        proposal = few_shot.get("proposal", {})
        images = few_shot.get("images", [])
        success_status = "Yes" if proposal.get("is_successful", False) else "No"

        # First create user message with example images if available
        user_content = []

        # Add text description
        user_content.append(
            {"type": "text", "text": "Here is another physics simulation to analyze:"}
        )

        # Add images
        for image_path in images:
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

        # Then create assistant message with the example solution
        if prompt_type == PROMPT_COT:
            reasoning = proposal.get("reasoning", "No reasoning provided")
            assistant_content = (
                f"Step-by-step analysis:\n{reasoning}\n\nAnswer: {success_status}"
            )
        elif prompt_type == PROMPT_DETAILED:
            assistant_content = f"{success_status}"
        elif prompt_type == "sanity_check":
            assistant_content = success_status
        else:  # PROMPT_DIRECT
            assistant_content = success_status

        messages.append({"role": "assistant", "content": assistant_content})

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

                # Add object type information - only specify if static, as dynamic is implied
                obj1_body_type = (
                    "static" if obj1.get("body_type") == STATIC_BODY else ""
                )
                obj2_body_type = (
                    "static" if obj2.get("body_type") == STATIC_BODY else ""
                )
                fill_values["OBJ1_TYPE"] = obj1_body_type
                fill_values["OBJ2_TYPE"] = obj2_body_type

                # Set ADDITIONAL_OBJECTS to empty string to avoid adding it to any prompt
                fill_values["ADDITIONAL_OBJECTS"] = ""

        # Create a description based on metadata or generate one
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
        elif obj_data.get("shape_type") in [2, 3]:  # Custom shape
            return "bar"
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

        lines = ["Here are examples of similar physics simulations:"]

        for i, ex in enumerate(few_shot_examples, start=1):
            puzzle = ex.get("puzzle", {})
            proposal = ex.get("proposal", {})
            images = ex.get("images", [])

            # Determine success status - use Yes/No instead of Success/Failure
            success_status = "Yes" if proposal.get("is_successful", False) else "No"
            goal_status = (
                "Goal reached"
                if proposal.get("is_successful", False)
                else "Goal not reached"
            )

            # Get initial and final state images if available
            initial_image = "initial state image"
            final_image = "final state image"
            if len(images) >= 2:
                initial_image = images[0]
                final_image = images[-1]
            elif images:
                initial_image = images[0]
                final_image = images[0]

            # Extract puzzle description information
            description = ""
            if "metadata" in puzzle and puzzle["metadata"].get("description"):
                description = f"\nDescription: {puzzle['metadata']['description']}"
            elif "bodies" in puzzle:
                # Create a brief description of the scenario
                bodies = puzzle["bodies"]
                static_count = sum(
                    1 for b in bodies if b.get("body_type") == STATIC_BODY
                )
                dynamic_count = len(bodies) - static_count
                description = f"\nScenario: Contains {len(bodies)} objects ({static_count} static, {dynamic_count} dynamic)"

            # Basic description for all example types
            lines.append(f"\nExample {i}: {goal_status} - {description}")
            lines.append(f"Initial state: [Image: {initial_image}]")
            lines.append(f"Final state: [Image: {final_image}]")

            # Additional details based on prompt type
            if prompt_type == PROMPT_COT:
                lines.append("Step-by-step analysis:")
                lines.append(f"{proposal.get('reasoning', 'No reasoning provided')}")
                lines.append(f"Answer: {success_status}")
            else:  # All other prompts just have Yes/No
                lines.append(f"Answer: {success_status}")

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
