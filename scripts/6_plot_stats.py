# Add global constants and helper functions for model colors
import re
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Tuple

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
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

            # Only add y-axis label to leftmost column of each row
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
    """Generates and saves a plot of binary accuracy by proposal type and few-shot config.

    The plot shows accuracy rates for different models across proposal types.
    Each subplot represents a different few-shot configuration.
    """
    # Create an EvaluationPlotter instance for binary evaluation
    plotter = EvaluationPlotter("binary", db_manager)

    # Data structure: {few_shot_count: {few_shot_frames: {proposal_type: {model: (correct_count, total_count)}}}}
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
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plotter.save_plot(plt, "accuracy_by_proposal_type_combined.png")
    plt.close()


def plot_binary_accuracy_by_template_difficulty(
    db_manager: MongoDBManager, grouped_templates: dict[str, list[int]]
) -> None:
    """Generates and saves a comparison plot of binary target accuracy by template difficulty
    for two settings: 0-shot and 4-shot 1 frame.

    For each configuration, all responses are aggregated and accuracy is computed as the percentage of correct responses.
    Correct responses are further broken down by whether they come from correct proposals (tier 'CORRECT') or incorrect proposals.
    The resulting plot consists of two horizontally arranged subplots (one per configuration) where each stacked bar shows:
    - The dark grey segment (color '#555555') representing correct responses from incorrect proposals,
    - The light grey segment (color '#BBBBBB') representing correct responses from correct proposals.

    Args:
        db_manager: The MongoDB manager instance.
        grouped_templates: Dictionary with keys "easy", "medium", "hard" and values as lists of template IDs.
    """
    # Define configurations to compare
    configs = [
        {"label": "0-shot", "few_shot_count": 0, "few_shot_frames": 1},
        {"label": "2-shot 1 frame", "few_shot_count": 2, "few_shot_frames": 1},
        {"label": "4-shot 1 frame", "few_shot_count": 4, "few_shot_frames": 1},
    ]

    difficulties = ["easy", "medium", "hard"]
    config_results: dict[str, dict[str, dict[str, dict[str, dict[str, int]]]]] = {}

    # Process each configuration
    for conf in configs:
        label = conf["label"]
        few_shot_count = conf["few_shot_count"]
        few_shot_frames = conf["few_shot_frames"]

        # Create an EvaluationPlotter instance for binary evaluation
        plotter = EvaluationPlotter("binary", db_manager)
        extra_filters = {
            "few_shot_count": few_shot_count,
            "few_shot_frames": few_shot_frames,
        }
        grouped_results = plotter.get_grouped_evaluation_results(extra_filters)

        # Initialize results for this configuration
        conf_data: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
        for model, results in grouped_results.items():
            if model not in conf_data:
                conf_data[model] = {
                    diff: {
                        "target": {"correct": 0, "total": 0},
                        "non_target": {"correct": 0, "total": 0},
                    }
                    for diff in difficulties
                }
            for doc in results:
                response = str(doc.response).strip().lower()
                if response not in ["yes", "no", "n"]:
                    continue
                if response == "n":
                    response = "no"
                tier = str(doc.sample.proposal.tier).upper()
                try:
                    template_str = str(doc.sample.puzzle.id).split(":")[0]
                    template_id = int(template_str)
                except (AttributeError, IndexError, ValueError):
                    continue
                diff_found = None
                for diff, templates in grouped_templates.items():
                    if template_id in templates:
                        diff_found = diff
                        break
                if diff_found is None:
                    continue
                if tier == "CORRECT":
                    conf_data[model][diff_found]["target"]["total"] += 1
                    if response == "yes":
                        conf_data[model][diff_found]["target"]["correct"] += 1
                else:
                    conf_data[model][diff_found]["non_target"]["total"] += 1
                    if response == "no":
                        conf_data[model][diff_found]["non_target"]["correct"] += 1

        config_results[label] = conf_data

    # --- New plotting section: Binary Accuracy by Model ---
    # Filter configurations to include 0-shot, 2-shot 1 frame, and 4-shot 1 frame as required
    configs_to_plot = [
        conf
        for conf in configs
        if conf["label"] in {"0-shot", "2-shot 1 frame", "4-shot 1 frame"}
    ]
    fig, axes = plt.subplots(
        1, len(configs_to_plot), figsize=(6 * len(configs_to_plot), 6), sharey=True
    )
    if len(configs_to_plot) == 1:
        axes = [axes]

    for idx, conf in enumerate(configs_to_plot):
        label = conf["label"]
        conf_data = config_results.get(label, {})
        # Aggregate responses per model by summing over difficulties
        aggregated: dict[str, dict[str, float]] = {}
        for model, m_data in conf_data.items():
            target_total = sum(
                m_data.get(diff, {}).get("target", {}).get("total", 0)
                for diff in difficulties
            )
            target_correct = sum(
                m_data.get(diff, {}).get("target", {}).get("correct", 0)
                for diff in difficulties
            )
            nt_total = sum(
                m_data.get(diff, {}).get("non_target", {}).get("total", 0)
                for diff in difficulties
            )
            nt_correct = sum(
                m_data.get(diff, {}).get("non_target", {}).get("correct", 0)
                for diff in difficulties
            )
            total = target_total + nt_total
            if total > 0:
                target_perc = (target_correct / total) * 100
                nt_perc = (nt_correct / total) * 100
            else:
                target_perc = 0.0
                nt_perc = 0.0
            aggregated[model] = {
                "target": target_perc,
                "non_target": nt_perc,
                "total": target_perc + nt_perc,
            }

        # Sort models alphabetically for consistent ordering
        models = sorted(aggregated.keys())
        x_positions = np.arange(len(models))
        ax = axes[idx]
        bar_width = 0.5
        for i, model in enumerate(models):
            base_color = get_model_color(model)
            bright_color = adjust_color_brightness(
                base_color, 1.1
            )  # Brighter for correct (target)
            dark_color = adjust_color_brightness(
                base_color, 0.9
            )  # Darker for incorrect (non_target)
            model_data = aggregated[model]
            # Plot the non_target (incorrect) part on bottom
            ax.bar(
                x_positions[i],
                model_data["non_target"],
                width=bar_width,
                color=dark_color,
            )
            # Stack the target (correct) part on top
            ax.bar(
                x_positions[i],
                model_data["target"],
                width=bar_width,
                bottom=model_data["non_target"],
                color=bright_color,
            )
            ax.text(
                x_positions[i],
                model_data["total"] + 1,
                f"{model_data['total']:.1f}%",
                ha="center",
                va="bottom",
                fontsize=10,
            )
        ax.set_xticks(x_positions)
        # ax.set_xticklabels([model.split("/")[-1] for model in models], rotation=45)
        ax.set_xlabel("Model")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", linestyle="--", alpha=0.7)
        ax.set_title(f"Binary Accuracy ({label})")
        if idx == 0:
            ax.set_ylabel("Accuracy (%)")

    # Add global legend for models and dark/bright explanation
    from matplotlib.patches import Patch

    all_models = set()
    for conf in configs_to_plot:
        label = conf["label"]
        conf_data = config_results.get(label, {})
        for model in conf_data.keys():
            all_models.add(model)
    sorted_models_global = sorted(all_models)
    model_handles = [
        Patch(facecolor=get_model_color(model), label=model.split("/")[-1])
        for model in sorted_models_global
    ]
    dark_patch = Patch(facecolor="#555555", label="Incorrect Proposals")
    bright_patch = Patch(facecolor="#BBBBBB", label="Correct Proposals")
    combined_handles = model_handles + [bright_patch, dark_patch]
    fig.legend(
        handles=combined_handles,
        loc="upper left",
        title="Legend",
        title_fontsize=12,
        fontsize=10,
    )

    plt.suptitle(
        "Binary Accuracy by Model",
        fontsize=16,
    )
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plotter = EvaluationPlotter("binary", db_manager)
    plotter.save_plot(plt, "binary_accuracy_by_model_comparison.png")
    plt.close()

    # --- Interactive ---


def plot_interactive_stats(db_manager: MongoDBManager) -> None:
    """Generates and saves a visualization of interactive evaluation statuses.

    Visualizes the distribution of all 4 relevant statuses (GOAL_REACHED, GOAL_NOT_REACHED,
    OUTSIDE_BOUNDARIES, OVERLAPPING) across templates and models.
    Each template is identified by the first part of the ID before ':'.

    Creates a heatmap visualization that shows:
    1. The distribution of statuses per template and model
    2. The frequency of each status type
    3. A comparative view between models
    """
    # Create an EvaluationPlotter instance for interactive evaluation
    plotter = EvaluationPlotter("interactive", db_manager)

    # Get evaluation results for all models
    grouped_results = plotter.get_grouped_evaluation_results()

    # Define the possible statuses (order matters for visualization)
    # Remove JSON_INCORRECT_FORMAT as it's always 0
    statuses = [
        "GOAL_REACHED",
        "GOAL_NOT_REACHED",
        "OUTSIDE_BOUNDARIES",
        "OVERLAPPING",
    ]

    # Data structures to hold status counts by template and model
    # Structure: {model: {template_id: {status: count}}}
    status_data: dict[str, dict[str, dict[str, int]]] = {}

    # Set to collect all unique template IDs (without version part)
    template_base_ids = set()

    # Process the results
    for model, results in grouped_results.items():
        status_data[model] = {}

        for doc in results:
            # Extract the template ID (part before ':')
            full_template_id = doc.sample.puzzle.id
            template_base_id = full_template_id.split(":")[0]
            template_base_ids.add(template_base_id)

            # Initialize the template data if not present
            if template_base_id not in status_data[model]:
                status_data[model][template_base_id] = {
                    status: 0 for status in statuses
                }

            # Count occurrences of each status in interactive_results
            if doc.interactive_results:
                for result in doc.interactive_results:
                    status = result.status
                    if status in statuses:
                        status_data[model][template_base_id][status] += 1

    # Sort template IDs for consistent display
    sorted_template_ids = sorted(template_base_ids)

    # Sort models for consistent display
    sorted_models = sorted(status_data.keys())

    # Get model colors for consistent display across plots
    model_to_color = {model: get_model_color(model) for model in sorted_models}

    # Calculate the number of subplots needed (one per model)
    num_models = len(sorted_models)

    # Create a figure with a grid of heatmaps (one per model)
    # Adjust figure width for better centering
    fig, axs = plt.subplots(
        num_models,
        1,
        figsize=(len(sorted_template_ids) * 0.7, 4.5 * num_models),
        # gridspec_kw={"hspace": 0.5},
    )

    # Handle the case with only one model
    if num_models == 1:
        axs = [axs]

    # Dictionary to store overall status counts for the pie chart
    overall_counts = {
        model: {status: 0 for status in statuses} for model in sorted_models
    }

    # Create a heatmap for each model
    for i, model in enumerate(sorted_models):
        # Create data for this model's heatmap
        # One row per status, one column per template
        data = np.zeros((len(statuses), len(sorted_template_ids)))

        for j, status in enumerate(statuses):
            for k, template_id in enumerate(sorted_template_ids):
                if template_id in status_data[model]:
                    count = status_data[model][template_id].get(status, 0)
                    data[j, k] = count
                    overall_counts[model][status] += count

        # Use a custom colormap starting with the model's color for zero values
        # and transitioning to deeper red for higher values

        model_cmap = LinearSegmentedColormap.from_list(
            f"model_cmap_{i}",
            [
                adjust_color_brightness(model_to_color[model], 1.5),
                adjust_color_brightness(model_to_color[model], 1.4),
                adjust_color_brightness(model_to_color[model], 1.3),
                adjust_color_brightness(model_to_color[model], 1.2),
                adjust_color_brightness(model_to_color[model], 1.1),
                adjust_color_brightness(model_to_color[model], 1.0),
            ],
        )

        # Plot the heatmap
        im = axs[i].imshow(data, cmap=model_cmap, aspect="auto")

        # Add colorbar
        cbar = fig.colorbar(im, ax=axs[i])
        cbar.set_label("Count")

        # Set axis labels with better positioning
        axs[i].set_yticks(np.arange(len(statuses)))
        axs[i].set_yticklabels(statuses)

        # Set and style x-axis labels horizontally
        axs[i].set_xticks(np.arange(len(sorted_template_ids)))
        axs[i].set_xticklabels(
            [id[-2:] for id in sorted_template_ids], rotation=0, ha="center"
        )

        # Set title for this subplot
        model_display = model.split("/")[-1]
        axs[i].set_title(f"Status Distribution for {model_display}")

        # Add text annotations on the heatmap
        for j in range(len(statuses)):
            for k in range(len(sorted_template_ids)):
                if data[j, k] > 0:
                    text_color = "white" if data[j, k] > 2 else "black"
                    axs[i].text(
                        k,
                        j,
                        f"{int(data[j, k])}",
                        ha="center",
                        va="center",
                        color=text_color,
                    )

    # Set the overall title
    plt.suptitle(
        "Interactive Evaluation Status Distribution by Template and Model", fontsize=16
    )

    # Adjust layout to reduce white space on left and right
    plt.tight_layout(rect=(0.02, 0, 1.05, 0.95))

    # Save the heatmap figure
    plotter.save_plot(plt, "interactive_status_distribution_heatmap.png")
    plt.close()

    # Create a second figure with pie charts for overall status distribution
    # Adjust figure size for better centering
    fig, axs = plt.subplots(1, num_models, figsize=(5 * num_models, 6))

    # Handle the case with only one model
    if num_models == 1:
        axs = [axs]

    # Custom colors for different statuses
    status_colors = {
        "GOAL_REACHED": "#2ca02c",  # Green
        "GOAL_NOT_REACHED": "#ff7f0e",  # Orange
        "OUTSIDE_BOUNDARIES": "#d62728",  # Red
        "OVERLAPPING": "#1f77b4",  # Blue
    }

    # Variable to store wedges for the legend
    legend_wedges = None
    has_data = False

    # Create a pie chart for each model
    for i, model in enumerate(sorted_models):
        model_display = model.split("/")[-1]

        # Extract the counts and calculate percentages
        status_counts = [overall_counts[model][status] for status in statuses]
        total = sum(status_counts)

        # Skip if no data
        if total == 0:
            axs[i].text(
                0.5, 0.5, "No data available", ha="center", va="center", fontsize=14
            )
            axs[i].axis("off")
            continue

        has_data = True

        # Create the pie chart without labels
        wedges, _, _ = axs[i].pie(
            status_counts,
            labels=None,  # Remove labels
            autopct="%1.1f%%",
            startangle=90,
            colors=[status_colors[status] for status in statuses],
            wedgeprops={"edgecolor": "w", "linewidth": 1},
        )

        # Set the title
        axs[i].set_title(
            f"Status Distribution for {model_display}\nTotal Interactions: {total}"
        )

        # Store wedges for the combined legend
        if i == 0:  # Only need to store once
            legend_wedges = wedges

    # Create a single legend for all pie charts in the top right
    if has_data and legend_wedges is not None:
        fig.legend(
            legend_wedges,
            statuses,
            title="Status Types",
            loc="lower right",  # Changed to bottom right
            bbox_to_anchor=(0.99, 0.01),  # Adjusted bbox_to_anchor for bottom right
        )

    # Set the figure title
    plt.suptitle("Overall Interactive Status Distribution by Model", fontsize=16)

    # Adjust layout to center content and accommodate the single legend
    plt.tight_layout(rect=(0, 0, 1, 0.9))

    # Save the pie chart figure
    plotter.save_plot(plt, "interactive_status_distribution_pie.png")

    # Close the figures
    plt.close("all")

    # Print a summary of the results
    print("\n=== Interactive Evaluation Status Summary ===")
    for model in sorted_models:
        model_display = model.split("/")[-1]
        print(f"\n{model_display}:")

        for status in statuses:
            count = overall_counts[model][status]
            print(f"  - {status}: {count}")


def plot_interactive_status_by_attempt(db_manager: MongoDBManager) -> None:
    """
    Analyzes and visualizes at which attempt number each status
    (GOAL_REACHED, OVERLAPPING, OUTSIDE_BOUNDARIES) occurred.
    """
    plotter = EvaluationPlotter("interactive", db_manager)

    # Get results grouped by model
    results_by_model = plotter.get_grouped_evaluation_results()

    statuses_of_interest = ["GOAL_REACHED", "OVERLAPPING", "OUTSIDE_BOUNDARIES"]
    status_colors = {
        "GOAL_REACHED": "#2ca02c",  # Green
        "OVERLAPPING": "#1f77b4",  # Blue
        "OUTSIDE_BOUNDARIES": "#d62728",  # Red
    }

    # Create a figure with subplots for each model
    num_models = len(results_by_model)
    fig, axes = plt.subplots(num_models, 1, figsize=(12, 4 * num_models), sharex=True)

    # If there's only one model, convert axes to list for consistent indexing
    if num_models == 1:
        axes = [axes]

    # For each model
    for i, (model, results) in enumerate(results_by_model.items()):
        model_color = get_model_color(model)

        # Initialize data structure to hold attempt counts for each status
        status_attempts = {
            status: {1: 0, 2: 0, 3: 0, 4: 0, 5: 0} for status in statuses_of_interest
        }

        # Process results for this model
        for result in results:
            # Access interactive_results to find statuses
            if result.interactive_results:
                for attempt_idx, interactive_result in enumerate(
                    result.interactive_results, 1
                ):
                    # Only consider up to 5 attempts
                    if attempt_idx > 5:
                        break

                    if interactive_result.status in statuses_of_interest:
                        status_attempts[interactive_result.status][attempt_idx] += 1

        # Create the subplot for this model
        ax = axes[i]

        # Set up bar positions
        bar_width = 0.25
        attempt_positions = np.arange(1, 6)

        # Plot bars for each status
        for j, status in enumerate(statuses_of_interest):
            values = [status_attempts[status][attempt] for attempt in range(1, 6)]
            position = attempt_positions + (j - 1) * bar_width
            bars = ax.bar(
                position,
                values,
                width=bar_width,
                label=status,
                color=status_colors[status],
                alpha=0.8,
            )

            # Add the count numbers on top of each bar
            for bar, value in zip(bars, values):
                if value > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.5,
                        str(value),
                        ha="center",
                        va="bottom",
                    )

        # Set subplot title and labels
        ax.set_title(
            f"Status Distribution by Attempt for {model.split('/')[-1]}", fontsize=14
        )
        ax.set_xticks(attempt_positions)
        ax.set_xticklabels([f"Attempt {i}" for i in range(1, 6)])
        ax.set_ylabel("Count", fontsize=12)
        if i == 1:
            ax.legend(title="Status", loc="upper right")
        ax.grid(axis="y", linestyle="--", alpha=0.7)

        # Ensure y-axis starts at 0
        ax.set_ylim(bottom=0)

    plt.suptitle("Distribution of Statuses by Attempt Number", fontsize=16)
    plt.tight_layout(rect=(0, 0, 1, 0.96))

    # Save the figure
    plotter.save_plot(plt, "interactive_status_by_attempt.png")
    plt.close()


def plot_interactive_proposal_differences(db_manager: MongoDBManager) -> None:
    """
    Analyzes and visualizes how models adjust their proposals between consecutive attempts.

    This function examines:
    1. Changes in absolute distance between consecutive attempts
    2. Changes in absolute radius between consecutive attempts

    For each model, it creates visualizations showing how proposals are refined based on feedback.
    """
    plotter = EvaluationPlotter("interactive", db_manager)

    # Get results grouped by model
    results_by_model = plotter.get_grouped_evaluation_results()

    # Create figure with 2 rows (absolute distance, absolute radius) and 1 column per model
    num_models = len(results_by_model)
    fig, axes = plt.subplots(2, num_models, figsize=(6 * num_models, 7), sharex="col")

    # If there's only one model, reshape axes for consistent indexing
    if num_models == 1:
        axes = axes.reshape(2, 1)

    # For each model
    for model_idx, (model, results) in enumerate(results_by_model.items()):
        model_color = get_model_color(model)

        # Data structures to store differences by attempt
        distance_diffs_by_attempt = {
            2: [],
            3: [],
            4: [],
            5: [],
        }  # absolute distance differences
        r_abs_diffs_by_attempt = {
            2: [],
            3: [],
            4: [],
            5: [],
        }  # absolute radius differences

        # Process each evaluation result
        for result in results:
            # Skip if no interactive results
            if not result.interactive_results or len(result.interactive_results) < 2:
                continue

            # Process consecutive attempts
            for i in range(1, len(result.interactive_results)):
                prev_attempt = result.interactive_results[i - 1]
                curr_attempt = result.interactive_results[i]

                # Current attempt number (1-based)
                attempt_num = i + 1

                # Skip if invalid data or JSON_INCORRECT_FORMAT
                if (
                    prev_attempt.status == "JSON_INCORRECT_FORMAT"
                    or curr_attempt.status == "JSON_INCORRECT_FORMAT"
                ):
                    continue

                # Extract proposal data
                try:
                    prev_props = prev_attempt.ball_data
                    curr_props = curr_attempt.ball_data

                    # Skip if any data is None
                    if prev_props is None or curr_props is None:
                        continue

                    # Handle both single ball and multi-ball scenarios
                    # For simplicity, we'll focus on the first ball if multiple
                    if isinstance(prev_props, list):
                        prev_props = prev_props[0]
                    if isinstance(curr_props, list):
                        curr_props = curr_props[0]

                    # Calculate absolute distance difference using Euclidean distance
                    prev_x = float(prev_props.get("x", 0))
                    prev_y = float(prev_props.get("y", 0))
                    curr_x = float(curr_props.get("x", 0))
                    curr_y = float(curr_props.get("y", 0))

                    # Calculate Euclidean distance between points
                    distance_diff = (
                        (curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2
                    ) ** 0.5

                    # Calculate absolute radius difference
                    r_diff = abs(
                        float(curr_props.get("radius", 0))
                        - float(prev_props.get("radius", 0))
                    )

                    # Store differences by attempt number
                    if attempt_num in distance_diffs_by_attempt:
                        distance_diffs_by_attempt[attempt_num].append(distance_diff)
                        r_abs_diffs_by_attempt[attempt_num].append(r_diff)

                except (KeyError, TypeError, ValueError) as e:
                    # Skip this pair if there's a data issue
                    continue

        # Plot absolute distance differences as violin plots
        ax_dist = axes[0, model_idx]

        # Prepare data for violin plots
        distance_data = [distance_diffs_by_attempt[i] for i in range(2, 6)]
        positions = list(range(2, 6))

        # Create violin plots for distance differences
        violin_parts = ax_dist.violinplot(
            distance_data,
            positions=positions,
            showmeans=True,
            showmedians=True,
            widths=0.7,
        )

        # Set violin colors to model color
        for pc in violin_parts["bodies"]:
            pc.set_facecolor(model_color)
            pc.set_alpha(0.7)

        # Customize violin plot appearance
        for partname in ["cmeans", "cmedians", "cbars", "cmins", "cmaxes"]:
            if partname in violin_parts:
                violin_parts[partname].set_edgecolor("black")

        ax_dist.set_title(
            f"{model.split('/')[-1]} - Position Distance Adjustments", fontsize=12
        )
        ax_dist.set_ylabel("Absolute Distance Difference")
        ax_dist.grid(True, alpha=0.3)

        # Plot absolute radius differences as violin plots
        ax_r = axes[1, model_idx]

        # Prepare data for violin plots
        radius_data = [r_abs_diffs_by_attempt[i] for i in range(2, 6)]

        # Create violin plots for radius differences
        violin_parts = ax_r.violinplot(
            radius_data,
            positions=positions,
            showmeans=True,
            showmedians=True,
            widths=0.7,
        )

        # Set violin colors to model color
        for pc in violin_parts["bodies"]:
            pc.set_facecolor(model_color)
            pc.set_alpha(0.7)

        # Customize violin plot appearance
        for partname in ["cmeans", "cmedians", "cbars", "cmins", "cmaxes"]:
            if partname in violin_parts:
                violin_parts[partname].set_edgecolor("black")

        ax_r.set_title(f"{model.split('/')[-1]} - Radius Adjustments", fontsize=12)
        ax_r.set_xlabel("Attempt")
        ax_r.set_ylabel("Absolute Radius Difference")
        ax_r.grid(True, alpha=0.3)

        # Set shared x-axis labels
        ax_r.set_xticks(range(2, 6))  # Attempts 2-5 (pairs 1-2, 2-3, 3-4, 4-5)
        ax_r.set_xticklabels([f"Attempt {i}" for i in range(2, 6)])

    plt.suptitle("Changes in Ball Proposals Between Consecutive Attempts", fontsize=16)
    plt.tight_layout(rect=(0, 0, 1, 0.97))

    # Save the figure
    plotter.save_plot(plt, "interactive_proposal_differences.png")
    plt.close()


def plot_interactive_success_rates(db_manager: MongoDBManager) -> None:
    """
    Creates a bar chart visualization showing the success rates for each model in interactive evaluation.
    Success rate is defined as the percentage of puzzles where the model reached the goal (GOAL_REACHED status).

    The chart displays:
    1. Success rate percentage for each model
    2. Absolute numbers (successful puzzles / total puzzles)
    3. Model names displayed horizontally under each bar
    """
    # Create an EvaluationPlotter instance for interactive evaluation
    plotter = EvaluationPlotter("interactive", db_manager)

    # Get evaluation results for all models
    grouped_results = plotter.get_grouped_evaluation_results()

    # Calculate success rates for each model
    model_success_data = {}
    for model, results in grouped_results.items():
        total_puzzles = len(results)
        successful_puzzles = sum(
            1
            for doc in results
            if doc.interactive_results
            and any(
                result.status == "GOAL_REACHED" for result in doc.interactive_results
            )
        )
        success_rate = (
            (successful_puzzles / total_puzzles) * 100 if total_puzzles > 0 else 0
        )
        model_success_data[model] = {
            "success_rate": success_rate,
            "successful_puzzles": successful_puzzles,
            "total_puzzles": total_puzzles,
        }

    # Sort models for consistent display
    sorted_models = sorted(model_success_data.keys())

    # Get model colors for consistent display across plots
    model_colors = {model: get_model_color(model) for model in sorted_models}

    # Create the figure
    plt.figure(figsize=(12, 4))

    # Plot the bars
    x_positions = np.arange(len(sorted_models))
    bars = plt.bar(
        x_positions,
        [model_success_data[model]["success_rate"] for model in sorted_models],
        color=[model_colors[model] for model in sorted_models],
        width=0.6,
    )

    # Add labels with the success rate percentage and counts
    for i, bar in enumerate(bars):
        model = sorted_models[i]
        data = model_success_data[model]
        success_rate = data["success_rate"]
        successful_puzzles = data["successful_puzzles"]
        total_puzzles = data["total_puzzles"]

        # Add percentage label above the bar
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,  # Position slightly above the bar
            f"{success_rate:.1f}%\n({successful_puzzles}/{total_puzzles})",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    # Set the x-axis labels to be the model names (displayed horizontally)
    plt.xticks(
        x_positions,
        [model.split("/")[-1] for model in sorted_models],
        rotation=0,  # Horizontal labels
        ha="center",
    )

    # Configure the plot
    plt.title("Interactive Evaluation Success Rates by Model", fontsize=16)
    plt.ylabel("Success Rate (%)", fontsize=12)
    plt.ylim(0, 100)  # Set y-axis from 0 to 100%
    plt.grid(axis="y", linestyle="--", alpha=0.3)

    # Add horizontal lines at key percentage points
    for percentage in [20, 40, 60, 80, 100]:
        plt.axhline(y=percentage, color="gray", linestyle="-", alpha=0.3)

    # Adjust layout
    plt.tight_layout()

    # Save the figure
    plotter.save_plot(plt, "interactive_success_rates.png")
    plt.close()


def main() -> None:
    """Main function that runs all the plotting functions."""
    parser = ArgparseManager("Plot statistics from MongoDB.")
    parser.add_common_db_args()
    args = parser.parse_args()

    db_manager = MongoDBManager(db_name=args.db_name)

    # Get the grouped templates for the confidence plots
    grouped_templates = plot_mean_attempts_per_template(db_manager)

    # Run all plotting functions
    # plot_sanity_check_results(db_manager)
    # plot_confidence_violin_by_proposal_type(db_manager)
    # plot_confidence_violin_by_both(db_manager, grouped_templates)
    # plot_confidence_by_model(db_manager)
    # print_ranking_statistics(db_manager)
    # verify_binary_responses(db_manager)
    # plot_binary_accuracy_by_proposal_type(db_manager)
    # plot_interactive_stats(db_manager)
    # plot_interactive_status_by_attempt(db_manager)
    # plot_interactive_proposal_differences(db_manager)
    # plot_interactive_success_rates(db_manager)
    plot_binary_accuracy_by_template_difficulty(db_manager, grouped_templates)

    # Close the MongoDB connection
    db_manager.close_connection()


if __name__ == "__main__":
    main()
