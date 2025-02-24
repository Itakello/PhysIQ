from typing import Any, Dict, List


class PromptManager:
    """
    This manager creates system + user prompt messages by substituting placeholders
    in a provided template with puzzle/proposal data.

    Usage:
      1. Provide a template with placeholders (e.g. "{{RADIUS}}" or "<POS_X>")
      2. Provide a dictionary with values to fill in.
      3. Build the final system message, user message, or both.
    """

    def __init__(self, system_template: str, user_template: str) -> None:
        """
        Args:
            system_template: The system-level template string. E.g. "You are a physics solver..."
            user_template:   The user prompt template string.
        """
        self.system_template = system_template
        self.user_template = user_template

    def build_prompt(
        self,
        puzzle_data: Dict[str, Any],
        proposal_data: Dict[str, Any],
        images: List[str],
        few_shot_examples: List[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Builds the final prompt (system + user) given puzzle + proposal + optional few-shot examples.

        Args:
            puzzle_data: Dict of puzzle fields (e.g. from the DB).
            proposal_data: Dict of proposal fields (id, attempt, proposals, image_path, tier).
            images: A list of image file paths relevant to the puzzle/proposal.
            few_shot_examples: (Optional) list of exemplars, each containing puzzle+proposal+images.

        Returns:
            {
              "system": <final system message str>,
              "user":   <final user message str>
            }
        """
        # 1) Build a dictionary of known placeholders
        fill_dict = self._extract_values(puzzle_data, proposal_data, images)

        # 2) If we have few-shot examples, we incorporate them into fill_dict
        #    or we can build a separate string that we append or nest in user/system.
        few_shot_str = (
            self._build_few_shot_string(few_shot_examples) if few_shot_examples else ""
        )

        # 3) Substituting placeholders in system and user templates
        #    For simplicity, we do simple str.replace() or a small regex approach.
        filled_system = self._fill_template(
            self.system_template, fill_dict, few_shot_str
        )
        filled_user = self._fill_template(self.user_template, fill_dict, few_shot_str)

        return {"system": filled_system, "user": filled_user}

    def _extract_values(
        self,
        puzzle_data: Dict[str, Any],
        proposal_data: Dict[str, Any],
        images: List[str],
    ) -> Dict[str, str]:
        """
        Inspect puzzle_data, proposal_data, and images; produce a dictionary { placeholder_name: value }.
        Adjust logic as needed to capture exactly which numeric or textual fields you want to insert.
        """
        # For demonstration, let's just pick out some puzzle data
        # (like the puzzle ID, puzzle's metadata description) and
        # from the proposal: the radius and x,y positions, etc.
        fill_values = {}
        fill_values["PUZZLE_ID"] = puzzle_data.get("id", "")
        fill_values["DESCRIPTION"] = puzzle_data.get("metadata", {}).get(
            "description", ""
        )
        fill_values["PROPOSAL_TIER"] = proposal_data.get("tier", "")

        # If the proposals field has multiple circles, let's just take the first for demonstration
        proposals_list = proposal_data.get("proposals", [])
        if proposals_list:
            first_prop = proposals_list[0]
            fill_values["PROP_RADIUS"] = f"{first_prop.get('radius', 0.0):.2f}"
            pos = first_prop.get("position", [0.0, 0.0])
            fill_values["PROP_POS_X"] = f"{pos[0]:.2f}"
            fill_values["PROP_POS_Y"] = f"{pos[1]:.2f}"
        else:
            fill_values["PROP_RADIUS"] = ""
            fill_values["PROP_POS_X"] = ""
            fill_values["PROP_POS_Y"] = ""

        # Maybe we want to display images
        # We'll create a simple comma-separated string of image filenames
        if images:
            fill_values["IMAGES"] = ", ".join(images)
        else:
            fill_values["IMAGES"] = "No images found"

        return fill_values

    def _build_few_shot_string(self, few_shot_examples: List[Dict[str, Any]]) -> str:
        """
        Convert the list of few-shot exemplars to a textual snippet.
        e.g. "Example 1: puzzle_id=..., outcome=..., Example 2: ..."
        You can be more creative or incorporate a mini template for each example.
        """
        lines = []
        for i, ex in enumerate(few_shot_examples, start=1):
            pid = ex["puzzle"].get("id", "unknown")
            tier = ex["proposal"].get("tier", "unknown")
            lines.append(f"Few-Shot Example {i} => Puzzle: {pid}, Tier: {tier}")
        return "\n".join(lines)

    def _fill_template(
        self, template_str: str, fill_dict: Dict[str, str], few_shot_str: str
    ) -> str:
        """
        Simple placeholder substitution.
        This example looks for <PLACEHOLDER> or {{PLACEHOLDER}}.
        You can refine or use a real template engine like Jinja2.
        Also appends the few-shot string at the bottom or top as you prefer.
        """
        filled = template_str

        # 1) Insert the main placeholders
        #    We'll do a naive approach with .replace
        for key, val in fill_dict.items():
            # Try both <KEY> and {{KEY}}
            filled = filled.replace(f"<{key}>", val)
            filled = filled.replace(f"{{{{{key}}}}}", val)

        # 2) Insert few_shot_str if there's a placeholder for it
        if "<FEW_SHOT>" in filled:
            filled = filled.replace("<FEW_SHOT>", few_shot_str)
        elif "{{FEW_SHOT}}" in filled:
            filled = filled.replace("{{FEW_SHOT}}", few_shot_str)
        else:
            # Or just append
            filled += f"\n\n{few_shot_str}"

        return filled
