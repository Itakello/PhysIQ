# Add global constants and helper functions for model colors
import re
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Tuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from src.managers import ArgparseManager, MongoDBManager
from src.utils.db_schemas import EvaluationResultSchema

# Colors for models based on VLMClient providers
MODEL_COLORS: dict[str, str] = {
    "openai/gpt-4o": "#0f9d7a",
    "google/gemini-2.0-flash-001": "#4a90e8",
    "qwen/qwen2.5-vl-72b-instruct": "#5844d0",
    "anthropic/claude-3.5-sonnet": "#d17151",
}
DEFAULT_MODEL_COLOR: str = "#7f7f7f"


def get_model_color(model: str) -> str:
    """Return a consistent color for the given model name using the global MODEL_COLORS."""
    simple_model = model.split(":")[-1].strip().lower()
    return MODEL_COLORS.get(simple_model, DEFAULT_MODEL_COLOR)


def adjust_color_brightness(hex_color: str, factor: float) -> str:
    """
    Adjust the brightness of a hex color.
    A factor > 1.0 lightens the color, while a factor < 1.0 darkens it.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = min(max(int(r * factor), 0), 255)
    g = min(max(int(g * factor), 0), 255)
    b = min(max(int(b * factor), 0), 255)
    return f"#{r:02X}{g:02X}{b:02X}"


# Common class for evaluation plotting
class EvaluationPlotter:
    """
    A common class for plotting evaluation results.
    It takes an evaluation_type and mongodb_manager as inputs, sets up a directory based
    on the evaluation type, and provides utility methods for building queries and saving plots.
    """

    def __init__(
        self,
        evaluation_type: str,
        mongodb_manager: MongoDBManager,
        only_selected_models: bool = True,
    ) -> None:
        self.evaluation_type = evaluation_type
        self.mongodb_manager = mongodb_manager
        self.only_selected_models = only_selected_models
        self.base_dir = Path("plots") / evaluation_type
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _build_query(self, extra_filters: dict | None = None) -> dict:
        query: dict[str, Any] = {"evaluation_type": self.evaluation_type}
        if extra_filters:
            query.update(extra_filters)
        if self.only_selected_models:
            query["model_name"] = {"$in": list(MODEL_COLORS.keys())}
        return query

    def save_plot(self, plt_obj, filename: str) -> None:
        plot_path = self.base_dir / filename
        plt_obj.savefig(plot_path)
        print(f"Plot saved to: {plot_path}")

    def get_grouped_evaluation_results(
        self, extra_filters: dict | None = None
    ) -> dict[str, list[EvaluationResultSchema]]:
        """Retrieve evaluation results grouped by model using the MongoDBManager.
        The results are returned in EvaluationResultSchema format.
        """
        query = self._build_query(extra_filters)
        return self.mongodb_manager.get_evaluation_results_grouped_by_model(query)


# --- General ---
def plot_mean_attempts_per_template(db_manager: MongoDBManager) -> dict[str, list[int]]:
    """Plots a bar chart of mean attempts of correct proposals for each template.

    For each template, the mean is calculated as:
       (sum(attempts) + 10000 * (# missing iterations)) / (max_iteration + 1)
    where # missing iterations = (max_iteration + 1) - number of proposals found.
    This function orders the templates in ascending order of the calculated mean.
    Two dashed vertical lines are drawn to divide the sorted templates into three groups of nearly equal size.
    Text labels 'easy', 'medium', and 'hard' are added above the respective groups.

    Returns:
        A dictionary with keys "easy", "medium", "hard" and values as lists of template IDs in each group.
    """
    # Retrieve all correct proposals
    proposals = db_manager.get_all_correct_proposals()

    # Group proposals by template and gather attempts and iteration indices
    template_data: dict[int, list[tuple[int, int]]] = {}
    # Each entry will be a tuple (iteration, attempt)
    for proposal in proposals:
        try:
            template_str, iter_str = proposal.id.split(":")
            template = int(template_str)
            iteration = int(iter_str)
        except (ValueError, AttributeError):
            continue
        if template not in template_data:
            template_data[template] = []
        template_data[template].append((iteration, proposal.attempt))

    # Compute overall mean for each template considering skipped iterations
    templates = list(template_data.keys())
    data = []  # list of tuples: (template, mean, color)
    for t in templates:
        entries = template_data[t]
        max_iter = max(e[0] for e in entries)  # maximum iteration found
        count = len(entries)
        missing = (max_iter + 1) - count
        total_attempts = sum(e[1] for e in entries) + 10000 * missing
        mean_val = total_attempts / (max_iter + 1) if (max_iter + 1) > 0 else 0
        # Determine color based on template number (blue if < 100, orange otherwise)
        color = "blue" if t < 100 else "orange"
        data.append((t, mean_val, color))

    # Sort by mean in ascending order
    data.sort(key=lambda x: x[1])
    sorted_templates = [d[0] for d in data]
    sorted_means = [d[1] for d in data]
    sorted_colors = [d[2] for d in data]

    total = len(sorted_templates)
    # Determine group sizes for 3 groups nearly equal in size
    # We'll distribute the remainder from division evenly from the first groups
    group_size = total // 3
    remainder = total % 3
    group1 = group_size + (1 if remainder > 0 else 0)
    group2 = group_size + (1 if remainder > 1 else 0)
    group3 = total - group1 - group2

    groups = {
        "easy": sorted_templates[:group1],
        "medium": sorted_templates[group1 : group1 + group2],
        "hard": sorted_templates[group1 + group2 :],
    }

    plt.figure(figsize=(14, 6))
    x = list(range(total))
    plt.bar(
        x, sorted_means, tick_label=sorted_templates, width=0.7, color=sorted_colors
    )

    # Adjust x-axis limits to use the full width
    plt.xlim(-0.5, total - 0.5)  # Set limits from -0.5 to total-0.5 to use full width

    plt.xticks(rotation=45)
    plt.xlabel("Template")
    plt.ylabel("Mean Attempts")
    plt.title("Mean Correct Proposal Generation Attempts by Template")

    # Draw two dashed vertical lines at the group boundaries
    boundary1 = group1 - 0.5
    boundary2 = group1 + group2 - 0.5
    plt.axvline(x=boundary1, color="black", linestyle="--")
    plt.axvline(x=boundary2, color="black", linestyle="--")

    # Add text labels for the three groups
    max_mean = max(sorted_means) if sorted_means else 0
    y_text = max_mean * 0.95
    group1_center = (0 + group1 - 1) / 2 if group1 > 0 else 0
    group2_center = (group1 + (group1 + group2 - 1)) / 2 if group2 > 0 else 0
    group3_center = (group1 + group2 + (total - 1)) / 2 if group3 > 0 else 0
    plt.text(group1_center, y_text, "easy", ha="center", va="bottom", fontsize=12)
    plt.text(group2_center, y_text, "medium", ha="center", va="bottom", fontsize=12)
    plt.text(group3_center, y_text, "hard", ha="center", va="bottom", fontsize=12)

    # Add legend for the ball types (color division remains as before)
    import matplotlib.patches as mpatches

    patch1 = mpatches.Patch(color="blue", label="1_ball")
    patch2 = mpatches.Patch(color="orange", label="2_ball")
    plt.legend(handles=[patch1, patch2])

    plt.tight_layout()
    plotter = EvaluationPlotter("general", db_manager)
    plotter.save_plot(plt, "mean_attempts_by_template.png")
    plt.close()
    return groups


# --- Sanity check ---
def plot_sanity_check_results(db_manager: MongoDBManager) -> None:
    """Plot evaluation results for sanity check.
    Horizontal bar chart displaying correct, incorrect, and total counts per model using green, red, and grey colors respectively.
    Model names (shortened to remove provider) are displayed on the y-axis.
    Also prints to terminal the total number of correct predictions for each model.
    The x-axis is labeled 'Accuracy'.
    """
    # Use EvaluationPlotter to retrieve grouped evaluation results
    eval_plotter = EvaluationPlotter("sanity_check", db_manager, False)
    grouped_results = eval_plotter.get_grouped_evaluation_results(
        extra_filters={"few_shot_count": 0}
    )

    # Group results by model: model -> { 'correct': int, 'incorrect': int }
    results: dict[str, dict[str, int]] = {}
    for model, eval_list in grouped_results.items():
        results[model] = {"correct": 0, "incorrect": 0, "invalid": 0}
        for res in eval_list:
            tier = res.sample.proposal.tier
            response = res.response[:5].strip().lower()
            if res.ground_truth in response:
                if tier == "CORRECT":
                    results[model]["correct"] += 1
                else:
                    results[model]["incorrect"] += 1
            elif "yes" not in response and "no" not in response:
                results[model]["invalid"] += 1

    if not results:
        return

    # Sort models alphabetically for consistent display
    models = sorted(list(results.keys()))
    # Create shortened model names by keeping only the part after '/' if present
    model_labels = [m.split("/")[-1] if "/" in m else m for m in models]

    correct_counts = [results[m]["correct"] for m in models]
    incorrect_counts = [results[m]["incorrect"] for m in models]
    invalid_counts = [results[m]["invalid"] for m in models]
    total_counts = [correct_counts[i] + incorrect_counts[i] for i in range(len(models))]

    # Increase spacing between model groups
    bar_spacing = 1.0  # Increased for better separation
    y = np.arange(len(models)) * bar_spacing
    bar_height = 0.15  # Bar height

    # Adjust figure height based on number of models
    fig_height = max(8, len(models) * 1.0)
    plt.figure(figsize=(12, fig_height))

    # Define bar types in the order they should appear (from top to bottom within each model group)
    bar_types = [
        {"name": "Total", "color": "grey", "offset": 0.3},
        {"name": "Correct", "color": "green", "offset": 0.1},
        {"name": "Incorrect", "color": "red", "offset": -0.1},
        {"name": "Invalid", "color": "purple", "offset": -0.3},
    ]

    # Create empty handles for legend
    legend_handles = []

    # Plot horizontal bars with consistent ordering for each model
    for i in range(len(models)):
        for bar_type in bar_types:
            if bar_type["name"] == "Total":
                value = total_counts[i]
            elif bar_type["name"] == "Correct":
                value = correct_counts[i]
            elif bar_type["name"] == "Incorrect":
                value = incorrect_counts[i]
            else:  # Invalid
                value = invalid_counts[i]

            # Only add to legend for the first model
            label = bar_type["name"] if i == 0 else ""

            # Calculate position with explicit offset
            position = y[i] + bar_type["offset"]

            bar = plt.barh(
                position,
                value,
                bar_height,
                color=bar_type["color"],
                label=label,
            )

            # Store handle for the first model only (for legend)
            if i == 0:
                legend_handles.append(bar)

    plt.xlabel("Accuracy")
    plt.ylabel("Model")
    plt.title("Sanity Check Evaluation")
    plt.yticks(y, model_labels)

    # Create legend with the correct order
    plt.legend(handles=legend_handles)
    plt.tight_layout()

    plotter = EvaluationPlotter("sanity_check", db_manager)
    plotter.save_plot(plt, "accuracy_per_model.png")
    plt.close()


# --- Confidence ---
def plot_confidence_violin_by_proposal_type(db_manager: MongoDBManager) -> None:
    """
    Generate and save a plot with 4 subplots (2 rows x 2 columns), one for each proposal type, showing violin plots of the confidence distributions for each model (excluding meta-llama models).
    Each subplot corresponds to one proposal type: 'correct', 'incorrect_easy', 'incorrect_medium', 'incorrect_hard'.
    The violin plots display the distribution of individual confidence values for each model with distinct colors, and a global legend is added.
    """

    # Define the proposal types
    proposal_types = ["correct", "incorrect_easy", "incorrect_medium", "incorrect_hard"]

    # Use EvaluationPlotter to retrieve grouped evaluation results for 'confidence'
    plotter = EvaluationPlotter("confidence", db_manager)
    grouped_results = plotter.get_grouped_evaluation_results()

    # Prepare data dictionary to hold records per proposal type
    data: dict[str, list[dict[str, object]]] = {ptype: [] for ptype in proposal_types}

    # Iterate over grouped evaluation results
    for model, results in grouped_results.items():
        # Exclude models containing 'meta-llama'
        for result in results:
            try:
                response: str = str(result.response)
                match = re.search(r"\b(\d{1,3})\b", response)
                if not match:
                    continue
                confidence: int = int(match.group(1))
                # Get proposal tier from result.sample.proposal.tier
                tier: str = str(result.sample.proposal.tier).lower()
                if tier not in proposal_types:
                    continue
                data[tier].append({"model": model, "confidence": confidence})
            except Exception:
                continue

    # Build global set of models for consistent color mapping
    global_models: set[str] = set()
    for records in data.values():
        for rec in records:
            global_models.add(str(rec["model"]))
    sorted_global_models = sorted(global_models, key=str)
    model_to_color = {model: get_model_color(model) for model in sorted_global_models}

    # Set up subplots: 2 rows x 2 columns
    fig, axes = plt.subplots(2, 2, figsize=(12, 12), sharey=True)
    axes = axes.flatten()

    for idx, ptype in enumerate(proposal_types):
        ax = axes[idx]
        records = data[ptype]
        if not records:
            ax.set_title(f"{ptype.replace('_', ' ').title()} (No Data)")
            continue

        # Group the records by model
        model_groups: dict[str, list[int]] = {}
        for rec in records:
            # Ensure the model key is a string
            model_key: str = str(rec["model"])
            conf = int(
                str(rec["confidence"])
            )  # cast to str first to satisfy type checker
            model_groups.setdefault(model_key, []).append(conf)

        # Determine models for this subplot sorted by global order
        models = sorted(
            model_groups.keys(), key=lambda m: sorted_global_models.index(m)
        )
        violin_data = [model_groups[m] for m in models]
        positions = list(np.arange(1, len(models) + 1))

        parts = ax.violinplot(
            violin_data, positions=positions, showmeans=True, showmedians=False
        )
        # Set individual colors for each violin body using correct model colors
        for i, body in enumerate(parts["bodies"]):
            model = models[i]
            body.set_facecolor(model_to_color.get(model, "#7f7f7f"))
            body.set_edgecolor("black")
            body.set_alpha(0.7)

        ax.set_xticks(positions)
        ax.set_title(ptype.replace("_", " ").title())
        if idx % 2 == 0:
            ax.set_ylabel("Confidence (%)")
        ax.grid(True)

    # Remove any unused subplot axes if there are fewer than 4
    for j in range(len(proposal_types), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle("Confidence Violin Plots by Proposal Type", fontsize=16)

    # Create a global legend for models
    legend_handles = [
        mpatches.Patch(
            facecolor=model_to_color[m], edgecolor="black", label=m.split("/")[-1]
        )
        for m in sorted_global_models
    ]
    fig.legend(
        handles=legend_handles, loc="upper right", bbox_to_anchor=(0.99, 1.00), ncol=1
    )

    plt.tight_layout(rect=(0, 0, 1, 0.95))

    # Save the plot using EvaluationPlotter
    plotter.save_plot(plt, "confidence_violin_by_proposal_type.png")
    plt.close()
    print(
        f"Confidence violin plot saved to: {plotter.base_dir / 'confidence_violin.png'}"
    )


def plot_confidence_violin_by_both(
    db_manager: MongoDBManager, grouped_templates: dict[str, list[int]]
) -> None:
    """Generate and save a plot with 6 subplots (2 rows, 3 columns), each for a template difficulty group,
    showing violin plots of confidence distributions for each model from 'confidence' evaluation results.
    The template difficulty is determined by the grouped_templates dictionary returned from plot_mean_attempts_per_template.
    The plots are divided into two rows: top row for correct proposals and bottom row for incorrect proposals.
    """

    # Retrieve confidence evaluation results using the existing EvaluationPlotter
    plotter = EvaluationPlotter("confidence", db_manager)
    grouped_results = plotter.get_grouped_evaluation_results()

    # Define the difficulty groups
    difficulties = ["easy", "medium", "hard"]
    # Define correctness categories
    correctness = ["correct", "incorrect"]

    # Initialize a dictionary to store confidence values by difficulty, correctness, and model
    data: dict[str, dict[str, dict[str, list[int]]]] = {
        diff: {corr: {} for corr in correctness} for diff in difficulties
    }

    # Iterate over the evaluation results
    for model, results in grouped_results.items():
        for result in results:
            try:
                response = str(result.response)
                match = re.search(r"\b(\d{1,3})\b", response)
                if not match:
                    continue
                confidence = int(match.group(1))

                # Extract template ID from sample.puzzle.id (assumes format 'template:iteration')
                sample = result.sample
                puzzle_id = str(sample.puzzle.id)
                if ":" not in puzzle_id:
                    continue
                template_str, _ = puzzle_id.split(":", 1)
                template_id = int(template_str)

                # Get proposal tier to determine if correct or incorrect
                tier = str(result.sample.proposal.tier).lower()
                is_correct = tier == "correct"
                corr_category = "correct" if is_correct else "incorrect"
                # if tier not in ["correct", "incorrect_easy"]:
                # continue

                # Determine which difficulty group this template belongs to
                for diff in difficulties:
                    if template_id in grouped_templates.get(diff, []):
                        data[diff][corr_category].setdefault(model, []).append(
                            confidence
                        )
                        break
            except Exception:
                continue

    # Determine global sorted list of models across all difficulties for consistent ordering
    global_models = sorted(
        {
            model
            for diff in difficulties
            for corr in correctness
            for model in data[diff][corr].keys()
        }
    )
    model_to_color = {model: get_model_color(model) for model in global_models}

    # Set up subplots: 2 rows x 3 columns
    fig, axes = plt.subplots(2, 3, figsize=(18, 12), sharey=True)

    for row_idx, corr in enumerate(correctness):
        for col_idx, diff in enumerate(difficulties):
            ax = axes[row_idx, col_idx]
            violin_data = []
            positions = []
            labels = []

            for i, model in enumerate(global_models):
                confidences = data[diff][corr].get(model, [])
                violin_data.append(confidences)
                positions.append(i + 1)
                labels.append(model.split("/")[-1])

            if violin_data and any(len(v) > 0 for v in violin_data):
                parts = ax.violinplot(
                    violin_data, positions=positions, showmeans=True, showmedians=False
                )
                # Set each violin's color based on model
                for i, body in enumerate(parts["bodies"]):
                    if i < len(global_models):  # Safety check
                        model = global_models[i]
                        body.set_facecolor(model_to_color.get(model, "#7f7f7f"))
                        body.set_edgecolor("black")
                        body.set_alpha(0.7)

            ax.set_xticks(positions)
            ax.set_title(
                f"{diff.capitalize()} Templates - {corr.capitalize()} Proposals"
            )

            # Only add x-axis label to bottom row
            if row_idx == 1:
                ax.set_xlabel("Model")

            # Only add y-axis label to leftmost column
            if col_idx == 0:
                ax.set_ylabel("Confidence (%)")

            ax.grid(True)

    fig.suptitle(
        "Confidence Violin Plots by Template Difficulty and Correctness", fontsize=16
    )

    legend_handles = [
        mpatches.Patch(
            facecolor=model_to_color[model],
            edgecolor="black",
            label=model.split("/")[-1],
        )
        for model in global_models
    ]

    fig.legend(
        handles=legend_handles, loc="upper right", bbox_to_anchor=(0.99, 1.0), ncol=1
    )

    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plotter.save_plot(plt, "confidence_violin_by_template_both.png")
    plt.close()
    print(
        f"Confidence violin plots by template both and correctness saved to: {plotter.base_dir / 'confidence_violin_by_template_both.png'}"
    )


def plot_confidence_by_model(db_manager: MongoDBManager) -> None:
    valid_tiers = {"correct", "incorrect_hard", "incorrect_medium", "incorrect_easy"}

    # Use EvaluationPlotter to retrieve evaluation results with evaluation_type 'confidence'
    plotter = EvaluationPlotter("confidence", db_manager)
    grouped_results = plotter.get_grouped_evaluation_results()

    # Structure to hold confidence values grouped by model, tier, and template id
    model_data: dict[str, dict[str, dict[int, list[int]]]] = {}
    for model, results in grouped_results.items():
        for result in results:
            # Get proposal tier from the sample and normalize case
            tier_raw = result.sample.proposal.tier
            if not tier_raw:
                continue
            tier = tier_raw.lower()
            if tier not in valid_tiers:
                continue

            m = re.search(r"\b(\d{1,3})\b", str(result.response))
            if not m:
                continue
            try:
                conf_value = int(m.group(1))
            except ValueError:
                continue

            # Extract template id from sample.puzzle.id (expects format 'template:iteration')
            puzzle_id = str(result.sample.puzzle.id)
            if ":" not in puzzle_id:
                continue
            try:
                template_str, _ = puzzle_id.split(":", 1)
                template_id = int(template_str)
            except ValueError:
                continue

            if model not in model_data:
                model_data[model] = {t: {} for t in valid_tiers}
            if template_id not in model_data[model][tier]:
                model_data[model][tier][template_id] = []
            model_data[model][tier][template_id].append(conf_value)

    color_map = {
        "correct": "green",
        "incorrect_hard": "yellow",
        "incorrect_medium": "orange",
        "incorrect_easy": "red",
    }

    # For each model, create a plot of mean confidence per template for each proposal tier
    for model, tier_dict in model_data.items():
        plt.figure(figsize=(10, 6))
        # Get the union of template IDs across all tiers
        all_templates: set[int] = set()
        for tier in valid_tiers:
            all_templates.update(tier_dict[tier].keys())
        if not all_templates:
            print(f"No valid templates for model: {model}")
            continue
        sorted_templates = sorted(all_templates)
        x_positions = list(range(len(sorted_templates)))
        plotted = False
        for tier in ["correct", "incorrect_hard", "incorrect_medium", "incorrect_easy"]:
            x_vals = []
            y_vals = []
            for i, temp in enumerate(sorted_templates):
                if temp in tier_dict[tier] and tier_dict[tier][temp]:
                    try:
                        avg_val = mean(tier_dict[tier][temp])
                    except Exception:
                        continue
                    x_vals.append(i)
                    y_vals.append(avg_val)
            if x_vals:
                plotted = True
                plt.plot(x_vals, y_vals, marker="o", color=color_map[tier], label=tier)
        if not plotted:
            print(f"No valid confidence data for model: {model}")
            continue

        plt.xlabel("Template Index")
        plt.ylabel("Mean Confidence (%)")
        plt.title(f"Confidence Averages for Model: {model.split('/')[-1]}")
        plt.xticks(x_positions, [str(t) for t in sorted_templates], rotation=45)
        plt.legend()
        plt.grid(True)

        # Use EvaluationPlotter with type 'confidence_by_model' to save the plot
        simple_model = model.split(":")[-1].strip()
        sanitized_model = "".join(
            [
                c if c.isalnum() or c in ("_", "-") else "_"
                for c in simple_model.split("/")[-1]
            ]
        )
        plt.tight_layout()
        plotter.save_plot(plt, f"confidence_{sanitized_model}.png")
        plt.close()
        print(f"Confidence plot for model '{model}' saved.")


# --- Ranking ---
def print_ranking_statistics(db_manager: MongoDBManager) -> None:
    """Generate and save plots showing how well models rank proposals compared to ground truth.

    For each few_shot_count (0, 1, 2), create plots showing:
    1. The percentage of times models correctly identified the position of each proposal type
    2. The overall accuracy of each model across different shot counts

    The correct proposal positions are determined by comparing the model's response
    with the ground truth ranking from the evaluation results.
    """
    # Regex pattern to validate and extract responses
    pattern = re.compile(r"^\s*\[?\s*(\d+(?:\s*,\s*\d+)*)\s*\]?\s*.*$", re.DOTALL)

    # Dictionary to store statistics for position accuracy
    # {few_shot_count: {model: {position_in_ground_truth: {correct_position_count, total_count}}}}
    position_stats: dict[int, dict[str, dict[int, dict[str, int]]]] = {}

    # Dictionary to store overall accuracy statistics
    # {model: {few_shot_count: {correct_count, total_count}}}
    accuracy_stats: dict[str, dict[int, dict[str, int]]] = {}

    shot_values = [0, 1, 2]
    position_labels = ["First", "Second", "Third", "Fourth"]

    # Use EvaluationPlotter for ranking evaluations
    plotter = EvaluationPlotter("ranking", db_manager)

    # Process all evaluation results
    for shot in shot_values:
        extra_filters = {"few_shot_count": shot}
        grouped_results = plotter.get_grouped_evaluation_results(extra_filters)

        # Initialize stats for this shot count
        position_stats[shot] = {}

        for model, results in grouped_results.items():
            # Initialize model stats if not already present
            if model not in accuracy_stats:
                accuracy_stats[model] = {}
            accuracy_stats[model][shot] = {"correct": 0, "total": 0}
            position_stats[shot][model] = {}

            # Initialize position stats for each model (positions 0 to 3)
            for pos in range(4):
                position_stats[shot][model][pos] = {"correct": 0, "total": 0}

            # Track invalid responses under key -1
            position_stats[shot][model][-1] = {"count": 0}

            # Process each evaluation result
            for result in results:
                # Get the ground truth ranking (1-indexed)
                ground_truth = result.ground_truth

                # Skip if ground truth is not available or not a list
                if not isinstance(ground_truth, list) or not ground_truth:
                    continue

                # Parse the model's response
                response_str = str(result.response)
                match = pattern.search(response_str)

                if match:
                    numbers_str = match.group(1)
                    try:
                        # Extract the ranking from the response
                        model_ranking = [
                            int(x.strip())
                            for x in numbers_str.split(",")
                            if x.strip() != ""
                        ]

                        # Check if the response has at least 4 numbers
                        if len(model_ranking) == 4:

                            # Check if the entire ranking is correct
                            if model_ranking == ground_truth:
                                accuracy_stats[model][shot]["correct"] += 1

                            # The model's #1 choice is the first element in model_ranking:
                            chosen_proposal_id = model_ranking[0]
                            # Now find *where* that ID is in ground_truth:
                            gt_position = ground_truth.index(chosen_proposal_id)

                            position_stats[shot][model][gt_position]["total"] += 1

                        else:
                            position_stats[shot][model][-1]["count"] += 1
                    except ValueError:
                        position_stats[shot][model][-1]["count"] += 1
                else:
                    position_stats[shot][model][-1]["count"] += 1

                # Increment total count for accuracy stats
                accuracy_stats[model][shot]["total"] += 1

    # --- Combined Position Accuracy Plot ---
    # Instead of separate plots for each shot, create a single figure with subplots for 0-shot, 1-shot, and 2-shot
    fig, axes = plt.subplots(
        1, len(shot_values), figsize=(24, 8), constrained_layout=True
    )
    if not isinstance(axes, (list, np.ndarray)):
        axes = [axes]
    for ax, shot in zip(axes, shot_values):
        stats_for_shot = position_stats.get(shot, {})
        if not stats_for_shot:
            ax.text(0.5, 0.5, f"No data for {shot}-shot", ha="center", va="center")
            ax.set_title(f"{shot}-shot")
            ax.axis("off")
            continue
        models = sorted(stats_for_shot.keys())
        num_positions = len(position_labels)
        group_width = 0.8
        bar_width = group_width / len(models) if models else group_width
        colors = [get_model_color(model) for model in models]
        for pos_idx, pos_label in enumerate(position_labels):
            for model_idx, model in enumerate(models):
                x_pos = pos_idx + (model_idx - len(models) / 2 + 0.5) * bar_width
                pos_stats = stats_for_shot[model].get(
                    pos_idx, {"correct": 0, "total": 0}
                )
                total_responses = accuracy_stats[model][shot]["total"]
                percentage = (
                    (pos_stats["total"] / total_responses * 100)
                    if total_responses > 0
                    else 0
                )
                ax.bar(x_pos, percentage, width=bar_width, color=colors[model_idx])
                if percentage > 0:
                    ax.text(
                        x_pos,
                        percentage + 0.5,
                        f"{percentage:.1f}%",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )
        ax.set_xlabel("Position in Ground Truth Ranking")
        if ax == axes[0]:
            ax.set_ylabel("Percentage (%)")
        ax.set_title(f"Distribution of Correct Proposal Position ({shot}-shot)")
        ax.set_xticks(range(num_positions))
        ax.set_xticklabels(position_labels)
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        # Set y-axis limit to ensure consistent scale across subplots
        ax.set_ylim(0, 40)

    # Create a global legend for models
    union_models: set[str] = set()
    for shot in shot_values:
        stats_for_shot = position_stats.get(shot, {})
        union_models.update(stats_for_shot.keys())
    union_models_list: list[str] = sorted(list(union_models))
    legend_handles = [
        mpatches.Patch(color=get_model_color(m), label=m.split("/")[-1])
        for m in union_models_list
    ]
    plt.legend(handles=legend_handles, loc="upper right", title="Models")
    plotter.save_plot(plt, "position_accuracy_combined.png")
    plt.close()

    # --- Overall Accuracy Plot ---
    # Create a plot showing model accuracies across different shot counts
    plt.figure(figsize=(12, 8))
    all_models = sorted(accuracy_stats.keys())
    if not all_models:
        print("No models found for accuracy plot")
        return
    num_shots = len(shot_values)
    group_width = 0.8
    bar_width = group_width / len(all_models) if all_models else group_width
    colors = [get_model_color(model) for model in all_models]
    for shot_idx, shot in enumerate(shot_values):
        for model_idx, model in enumerate(all_models):
            x_pos = shot_idx + (model_idx - len(all_models) / 2 + 0.5) * bar_width
            if shot in accuracy_stats[model]:
                correct = accuracy_stats[model][shot].get("correct", 0)
                total = accuracy_stats[model][shot].get("total", 0)
                accuracy = (correct / total * 100) if total > 0 else 0
                plt.bar(
                    x_pos,
                    accuracy,
                    width=bar_width,
                    color=colors[model_idx],
                    label=model.split("/")[-1] if shot_idx == 0 else "",
                )
                if accuracy > 0:
                    plt.text(
                        x_pos,
                        accuracy + 0.5,
                        f"{accuracy:.1f}%",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                    )
    plt.xlabel("Few-Shot Count")
    plt.ylabel("Accuracy (%)")
    plt.title("Model Accuracy Across Different Few-Shot Counts")
    plt.xticks(range(num_shots), [f"{shot}-shot" for shot in shot_values])
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.legend(title="Models", loc="upper right")
    plt.tight_layout()
    plotter.save_plot(plt, "model_accuracy_by_shot_count.png")
    plt.close()

    # Print invalid proposals statistics
    for shot in shot_values:
        print(f"\nInvalid Proposal Statistics for {shot}-shot:")
        models = sorted(position_stats.get(shot, {}).keys())
        for model in models:
            total_responses = accuracy_stats[model][shot]["total"]
            invalid = position_stats[shot][model].get(-1, {}).get("count", 0)
            invalid_percentage = (
                (invalid / total_responses * 100) if total_responses > 0 else 0
            )
            print(
                f"  Model: {model} - Invalid: {invalid} ({invalid_percentage:.1f}% of {total_responses} total)"
            )


# --- Binary ---
def verify_binary_responses(db_manager: MongoDBManager) -> None:
    """Print binary evaluation response validity: For each model, count and display valid responses ('yes' or 'no') versus total responses."""
    # Instantiate EvaluationPlotter for binary evaluations with only_selected_models=False to include all models
    eval_plotter = EvaluationPlotter("binary", db_manager)

    # Retrieve grouped evaluation results using the plotter
    grouped_results = eval_plotter.get_grouped_evaluation_results()

    stats: dict[str, dict[str, int]] = {}
    for model, results in grouped_results.items():
        stats[model] = {"valid": 0, "invalid": 0}
        for result in results:
            response: str = str(result.response).strip()
            if response.lower() in ["yes", "no", "n"]:
                stats[model]["valid"] += 1
            else:
                stats[model]["invalid"] += 1

    print("Binary Evaluation Response Validity:")
    for model, counts in stats.items():
        total: int = counts["valid"] + counts["invalid"]
        print(
            f"Model: {model} - Valid Responses: {counts['valid']} / Total Responses: {total}"
        )


def plot_binary_accuracy_by_proposal_type(db_manager: MongoDBManager) -> None:
    """Generates and saves a single plot of binary response accuracy for valid samples,
    grouped by proposal type and model, for different few-shot configurations.

    The plot is organized as a 3x2 grid:
    - Top-middle: 2-shot with 1 frame
    - Top-right: 4-shot with 1 frame
    - Bottom-left: 0-shot
    - Bottom-middle: 2-shot with 2 frames
    - Bottom-right: 4-shot with 2 frames
    (Top-left is empty to make space for the legend)

    Each subplot has the y-axis as accuracy (%) and columns organized into 4 groups corresponding to proposal types
    (CORRECT, INCORRECT_HARD, INCORRECT_MEDIUM, INCORRECT_EASY). Each group contains bars for each model (colored by model).

    Only valid binary responses are considered.
    The expected binary answer is 'yes' if the proposal type is CORRECT, else 'no'.
    """
    # Create an EvaluationPlotter instance for binary evaluation
    plotter = EvaluationPlotter("binary", db_manager)

    # Data structure: {few_shot_count: {few_shot_frames: {proposal_type: {model: (correct_count, total_count)}}}}
    from typing import Dict, Tuple

    accuracy_data: Dict[int, Dict[int, Dict[str, Dict[str, Tuple[int, int]]]]] = {
        0: {1: {}},  # 0-shot has 1 frames
        2: {1: {}, 2: {}},  # 2-shot with 1 or 2 frames
        4: {1: {}, 2: {}},  # 4-shot with 1 or 2 frames
    }

    # Get evaluation results for all configurations
    for few_shot_count in [0, 2, 4]:
        # For 0-shot, we only have 1 frame
        frames_to_check = [1] if few_shot_count == 0 else [1, 2]

        for few_shot_frames in frames_to_check:
            extra_filters = {
                "few_shot_count": few_shot_count,
                "few_shot_frames": few_shot_frames,
            }
            grouped_results = plotter.get_grouped_evaluation_results(extra_filters)

            for model, results in grouped_results.items():
                for doc in results:
                    response: str = str(doc.response).strip().lower()
                    if response not in ["yes", "no", "n"]:
                        continue
                    if response == "n":  # gemini sometimes has only n instead of no
                        response = "no"

                    # Get proposal tier and standardize to uppercase
                    tier: str = str(doc.sample.proposal.tier).upper()
                    if tier not in {
                        "CORRECT",
                        "INCORRECT_HARD",
                        "INCORRECT_MEDIUM",
                        "INCORRECT_EASY",
                    }:
                        continue

                    expected = "yes" if tier == "CORRECT" else "no"
                    is_correct = 1 if response == expected else 0

                    if tier not in accuracy_data[few_shot_count][few_shot_frames]:
                        accuracy_data[few_shot_count][few_shot_frames][tier] = {}
                    if (
                        model
                        not in accuracy_data[few_shot_count][few_shot_frames][tier]
                    ):
                        accuracy_data[few_shot_count][few_shot_frames][tier][model] = (
                            0,
                            0,
                        )

                    prev_correct, prev_total = accuracy_data[few_shot_count][
                        few_shot_frames
                    ][tier][model]
                    accuracy_data[few_shot_count][few_shot_frames][tier][model] = (
                        prev_correct + is_correct,
                        prev_total + 1,
                    )

    # Determine union of models across all configurations for consistent coloring
    union_models: set[str] = set()
    for shot_count in accuracy_data:
        for frames in accuracy_data[shot_count]:
            for tier_data in accuracy_data[shot_count][frames].values():
                union_models.update(tier_data.keys())
    sorted_union_models = sorted(union_models)
    model_to_color = {model: get_model_color(model) for model in sorted_union_models}

    proposal_types = ["CORRECT", "INCORRECT_HARD", "INCORRECT_MEDIUM", "INCORRECT_EASY"]

    # Create a single figure with a 3x2 grid layout
    fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(18, 12), sharey=True)

    # Define the subplot positions for each configuration
    # Format: (few_shot_count, few_shot_frames): (row, column, label)
    subplot_positions = {
        (2, 1): (0, 1, "2-shot 1 frame"),
        (4, 1): (0, 2, "4-shot 1 frame"),
        (0, 1): (0, 0, "0-shot"),  # 0-shot in bottom-left position
        (2, 2): (1, 1, "2-shot 2 frames"),
        (4, 2): (1, 2, "4-shot 2 frames"),
    }

    # Remove the top-left subplot (not used, space for legend)
    fig.delaxes(axes[1, 0])

    # Use union_models for consistent ordering in all subplots
    n_models = len(union_models)
    bar_width = 0.8 / n_models if n_models > 0 else 0.8
    x_groups = np.arange(len(proposal_types))  # one per proposal type

    for (shot_count, frame_count), (row, col, label) in subplot_positions.items():
        ax = axes[row, col]

        for i, tier in enumerate(proposal_types):
            for j, model in enumerate(sorted_union_models):
                correct, total = (
                    accuracy_data[shot_count][frame_count]
                    .get(tier, {})
                    .get(model, (0, 0))
                )
                acc = (correct / total * 100) if total > 0 else 0
                # Calculate bar position within the group
                x = x_groups[i] + (j - (n_models - 1) / 2) * bar_width
                ax.bar(x, acc, width=bar_width, color=model_to_color[model])

        ax.set_xticks(x_groups)
        ax.set_xticklabels(proposal_types, rotation=45, ha="right")
        ax.set_title(label)
        ax.grid(axis="y")
        ax.set_ylim(0, 100)

        # Add x-label only to bottom row
        if row == 1:
            ax.set_xlabel("Proposal Type")

        # Add y-label only to leftmost column of each row
        if col == 0:
            ax.set_ylabel("Accuracy (%)")

    # Create a global legend for models
    legend_handles = [
        Rectangle((0, 0), 1, 1, color=model_to_color[m]) for m in sorted_union_models
    ]
    # Position the legend above the 0-shot plot (bottom-left)
    fig.legend(
        handles=legend_handles,
        labels=[m.split("/")[-1] for m in sorted_union_models],
        loc="upper center",
        bbox_to_anchor=(0.17, 0.40),  # Position above the 0-shot plot (bottom-left)
        ncol=1,  # Limit columns for better readability
        title="Models",
    )

    plt.suptitle(
        "Binary Accuracy by Proposal Type and Few-Shot Configuration", fontsize=16
    )
    plt.tight_layout(rect=(0, 0, 1, 0.95))  # Using tuple to fix linter error
    plotter.save_plot(plt, "accuracy_by_proposal_type_combined.png")
    plt.close()


# --- Interactive ---


def main() -> None:
    parser = ArgparseManager("Plot statistics from MongoDB.")
    parser.add_common_db_args()
    args = parser.parse_args()

    db_manager = MongoDBManager(db_name=args.db_name)

    # Uncomment the plot function you want to run
    # grouped_templates = plot_mean_attempts_per_template(db_manager)

    # plot_sanity_check_results(db_manager)

    # plot_confidence_violin_by_proposal_type(db_manager)
    # plot_confidence_violin_by_both(db_manager, grouped_templates)
    # plot_confidence_by_model(db_manager)

    # print_ranking_statistics(db_manager)

    # verify_binary_responses(db_manager)
    plot_binary_accuracy_by_proposal_type(db_manager)

    db_manager.close_connection()


if __name__ == "__main__":
    main()
