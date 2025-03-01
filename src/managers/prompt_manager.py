import base64
from typing import Any

from src.utils.const import COLORS, MAX_BODIES_TO_DESCRIBE, STATIC_BODY
from src.utils.db_schemas import (
    BodyData,
    FewShotData,
    PuzzleSchema,
    RankingFewShotData,
    SampleData,
    RankingSampleData,
)
from src.utils.prompts import SYSTEM_TEMPLATES, USER_TEMPLATES


class PromptManager:
    """
    This manager creates system + user prompt messages by substituting placeholders
    in a provided template with puzzle/proposal data.

    Usage:
      1. Provide a template with placeholders (e.g. "{{RADIUS}}" or "<POS_X>")
      2. Provide a dictionary with values to fill in.
      3. Build the final system message, user message, or both.
    """

    def __init__(self, prompt_type: str) -> None:
        """
        Args:
            system_template: The system-level template string. E.g. "You are a physics solver..."
            user_template:   The user prompt template string.
            prompt_type:     The type of prompt to use (defaults to BINARY)
        """
        self.prompt_type = prompt_type
        self.system_template = SYSTEM_TEMPLATES.get(prompt_type, "binary")
        self.user_template = USER_TEMPLATES.get(prompt_type, "binary")

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
            prompt_type: Override the default prompt type

        Returns:
            { "system": <final system message str>,
              "user":   <final user message str>
            }
        """
        current_prompt_type = prompt_type or self.prompt_type
        user_template = USER_TEMPLATES.get(current_prompt_type, self.user_template)

        # Build dictionary of known placeholders
        fill_dict = self._extract_values(sample.puzzle, sample.images)

        # Few-shot handling - removing from templates, will be handled separately
        few_shot_str = ""
        if insert_few_shot and sample.few_shot:
            few_shot_str = self._build_few_shot_string(
                [fs.model_dump() for fs in sample.few_shot]
            )

        # Fill templates - don't include few_shot_str in system message
        filled_system = self._fill_template(self.system_template, fill_dict, "")
        filled_user = self._fill_template(user_template, fill_dict, few_shot_str)

        return {"system": filled_system, "user": filled_user}

    def build_openai_messages(
        self,
        sample: SampleData,
        insert_few_shot: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Builds the final prompt as a list of OpenAI API-compatible messages following:
        1. System message with instructions
        2. Few-shot examples (if requested)
        3. Final user message with specific question and image

        Args:
            sample: SampleData object containing puzzle, proposal, images and optional few-shots.
            insert_few_shot: Whether to include few-shot examples in the prompt.

        Returns:
            A list of message dictionaries compatible with OpenAI API format.
        """

        # Build dictionary of values to substitute in the templates
        fill_dict = self._extract_values(sample.puzzle, sample.images)

        # 1. System message with instructions
        messages = [
            {
                "role": "system",
                "content": self._fill_template(self.system_template, fill_dict, ""),
            }
        ]

        # 2. Add few-shot examples if requested
        if insert_few_shot and sample.few_shot:
            for fs_example in sample.few_shot:
                few_shot_messages = self._create_few_shot_messages(fs_example)
                messages.extend(few_shot_messages)

        # 3. Final user message with the specific question and image
        question = self._fill_template(self.user_template, fill_dict, "")
        user_content = []

        if self.prompt_type == "ranking":
            # For ranking prompts, add multiple proposals

            # Check if we're using the new RankingSampleData structure
            if isinstance(sample, RankingSampleData) and hasattr(sample, "proposals"):
                # Add all proposals with their numbered labels first
                for i, proposal_item in enumerate(sample.proposals, 1):
                    user_content.append({"type": "text", "text": f"Proposal {i}:"})

                    # Add the proposal's image(s)
                    for image_path in proposal_item.images:
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

                # Add the question at the end after all proposals
                user_content.append({"type": "text", "text": question})
            else:
                # Fallback to old behavior - just add the regular images
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
                # Add the question after the images
                user_content.append({"type": "text", "text": question})
        else:
            # Regular prompt flow for non-ranking prompts
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
                        }
                    )

            # Add the question after the images
            user_content.append({"type": "text", "text": question})

        messages.append({"role": "user", "content": user_content})  # type: ignore
        return messages

    def _create_few_shot_messages(
        self,
        few_shot: FewShotData,
    ) -> list[dict[str, Any]]:
        """
        Create assistant and user messages for a single few-shot example.

        Args:
            few_shot: FewShotData object containing the few-shot example data

        Returns:
            A list of message dictionaries for this few-shot example
        """
        messages = []

        # Extract data directly from the FewShotData object
        puzzle = few_shot.puzzle
        proposal = few_shot.proposal
        images = few_shot.images

        # Handle ranking prompt type differently - check if we have a RankingFewShotData instance
        if self.prompt_type == "ranking" and isinstance(few_shot, RankingFewShotData):
            # Create user message with example number and proposals
            user_content = []
            example_prefix = f"Example {few_shot.index}:"
            user_content.append({"type": "text", "text": example_prefix})

            # Extract target objects from the puzzle data
            target_obj1 = "target object 1"
            target_obj2 = "target object 2"

            # Get target object information from the relationship in puzzle
            if puzzle.relationship and puzzle.bodies:
                rel = puzzle.relationship
                bodies = puzzle.bodies

                if len(bodies) > rel.bodyId1 and len(bodies) > rel.bodyId2:
                    obj1 = bodies[rel.bodyId1]
                    obj2 = bodies[rel.bodyId2]

                    obj1_type = self._get_object_type(obj1)
                    obj2_type = self._get_object_type(obj2)

                    obj1_color = COLORS.get(obj1.color, "unknown color")
                    obj2_color = COLORS.get(obj2.color, "unknown color")

                    target_obj1 = f"{obj1_color} {obj1_type}"
                    target_obj2 = f"{obj2_color} {obj2_type}"

            # Add all proposals with their numbered labels
            for i, (proposal, proposal_images) in enumerate(
                zip(few_shot.proposals, few_shot.images_list), 1
            ):
                user_content.append({"type": "text", "text": f"Proposal {i}:"})

                # Add the proposal's image(s)
                for image_path in proposal_images:
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

            # Add the question text at the end, after all proposals
            template = USER_TEMPLATES[self.prompt_type]
            question = template.replace("<TARGET_OBJ1>", target_obj1).replace(
                "<TARGET_OBJ2>", target_obj2
            )
            user_content.append({"type": "text", "text": question})

            messages.append({"role": "user", "content": user_content})

            # Create assistant message with the ranking answer as a list
            correct_ranking = few_shot.metadata.correct_ranking
            # Convert to 1-indexed for display (proposals are shown as 1, 2, 3, 4)
            ranking_display = [i + 1 for i in correct_ranking]
            messages.append({"role": "assistant", "content": f"{ranking_display}"})

        else:
            # Standard non-ranking few-shot handling
            # Determine success status - use Yes/No based on whether the proposal is CORRECT
            success_status = "Yes" if proposal.tier == "CORRECT" else "No"

            # Extract target objects from the puzzle data
            target_obj1 = "target object 1"
            target_obj2 = "target object 2"

            # Get target object information from the relationship in puzzle
            if puzzle.relationship and puzzle.bodies:
                rel = puzzle.relationship
                bodies = puzzle.bodies

                if len(bodies) > rel.bodyId1 and len(bodies) > rel.bodyId2:
                    obj1 = bodies[rel.bodyId1]
                    obj2 = bodies[rel.bodyId2]

                    obj1_type = self._get_object_type(obj1)
                    obj2_type = self._get_object_type(obj2)

                    obj1_color = COLORS.get(obj1.color, "unknown color")
                    obj2_color = COLORS.get(obj2.color, "unknown color")

                    target_obj1 = f"{obj1_color} {obj1_type}"
                    target_obj2 = f"{obj2_color} {obj2_type}"

            # Create user message with initial screenshot and question
            user_content = []

            # Add example number prefix to the message
            example_prefix = f"Example {few_shot.index}:"

            user_content.append({"type": "text", "text": example_prefix})

            # Add ALL available images instead of just the first one
            if images:
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

            # Format the question using the appropriate template from prompts.py
            full_question = ""

            template = USER_TEMPLATES[self.prompt_type]
            # Replace target object placeholders in the template
            full_question = template.replace("<TARGET_OBJ1>", target_obj1).replace(
                "<TARGET_OBJ2>", target_obj2
            )

            user_content.append({"type": "text", "text": full_question})

            messages.append({"role": "user", "content": user_content})

            # Create assistant message with the answer (Yes/No)
            messages.append({"role": "assistant", "content": success_status})

        return messages

    def _extract_values(
        self,
        puzzle_data: PuzzleSchema,
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
        if puzzle_data.relationship and puzzle_data.bodies:
            rel = puzzle_data.relationship
            bodies = puzzle_data.bodies

            # Get the two objects that should come into contact
            if len(bodies) > rel.bodyId1 and len(bodies) > rel.bodyId2:
                obj1 = bodies[rel.bodyId1]
                obj2 = bodies[rel.bodyId2]

                obj1_type = self._get_object_type(obj1)
                obj2_type = self._get_object_type(obj2)

                obj1_color = COLORS.get(obj1.color, "unknown color")
                obj2_color = COLORS.get(obj2.color, "unknown color")

                fill_values["TARGET_OBJ1"] = f"{obj1_color} {obj1_type}"
                fill_values["TARGET_OBJ2"] = f"{obj2_color} {obj2_type}"

        return fill_values

    def _get_object_type(self, obj_data: BodyData) -> str:
        """Determine object type based on its properties"""
        if obj_data.shape_type == 1:  # Circle
            return "ball"
        elif obj_data.shape_type == 0:  # Polygon
            # Simplistic rectangle detection - could be enhanced
            return "rectangle"
        elif obj_data.shape_type == 2:  # Custom shape
            return "bar"
        elif obj_data.shape_type == 3:
            return "bucket"
        else:
            return "object"

    def _generate_description(self, puzzle_data: PuzzleSchema) -> str:
        """Generate a description of the puzzle if none is provided"""
        if not puzzle_data.bodies:
            return "A physics puzzle with multiple objects."

        bodies = puzzle_data.bodies
        static_count = sum(1 for b in bodies if b.body_type == STATIC_BODY)
        dynamic_count = len(bodies) - static_count

        description = f"The scene contains {len(bodies)} objects: {static_count} static and {dynamic_count} dynamic."

        # Add more details for small number of bodies
        if len(bodies) <= MAX_BODIES_TO_DESCRIBE:
            details = []
            for i, body in enumerate(bodies[:MAX_BODIES_TO_DESCRIBE]):
                body_type = "static" if body.body_type == STATIC_BODY else "dynamic"
                shape_type = self._get_object_type(body)
                color = COLORS.get(body.color, "unknown color")
                details.append(f"Object {i+1}: A {color} {shape_type} ({body_type})")

            description += " " + " ".join(details)

        return description

    def _build_few_shot_string(
        self,
        few_shot_examples: list[dict[str, Any]],
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

            # Just the answer for all prompt types
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
