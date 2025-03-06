from pathlib import Path

import matplotlib.pyplot as plt

from src.managers import ArgparseManager, MongoDBManager


def plot_evaluation_results(db_manager: MongoDBManager, few_shot_count: int) -> None:
    """Plot evaluation results for a given few_shot_count (e.g., 0 or 2) and save the plot.
    The plot groups results by model and shows the count of correct vs incorrect predictions.
    Incorrect predictions are determined by sample.proposal.tier != 'CORRECT'.
    """
    # Query evaluation_results with evaluation_type 'sanity_check' and few_shot_count
    query = {"evaluation_type": "sanity_check", "few_shot_count": few_shot_count}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")

    # Group results by model: model -> { 'correct': int, 'incorrect': int }
    results: dict[str, dict[str, int]] = {}
    for doc in cursor:
        model = doc.get("model_name", "Unknown")
        # Access nested proposal tier from sample
        proposal = doc.get("sample", {}).get("proposal", {})
        tier = proposal.get("tier", "INCORRECT")
        if model not in results:
            results[model] = {"correct": 0, "incorrect": 0}
        if tier == "CORRECT":
            results[model]["correct"] += 1
        else:
            results[model]["incorrect"] += 1

    if not results:
        print(f"No evaluation results found for few_shot_count = {few_shot_count}.")
        return

    # Prepare data for plotting
    models = list(results.keys())
    correct_counts = [results[m]["correct"] for m in models]
    incorrect_counts = [results[m]["incorrect"] for m in models]
    x = range(len(models))
    width = 0.35

    plt.figure(figsize=(12, 6))
    plt.bar(
        [i - width / 2 for i in x],
        correct_counts,
        width,
        label="Correct",
        color="green",
    )
    plt.bar(
        [i + width / 2 for i in x],
        incorrect_counts,
        width,
        label="Incorrect",
        color="red",
    )

    plt.xlabel("Model")
    plt.ylabel("Number of Predictions")
    plt.title(f"Sanity Check Evaluation - {few_shot_count}-shot")
    plt.xticks(x, models, rotation=45)
    plt.legend()
    plt.tight_layout()

    plots_dir = Path("plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plots_dir / f"sanity_check_{few_shot_count}_shot.png"
    plt.savefig(plot_path)
    plt.close()
    print(f"Sanity check {few_shot_count}-shot evaluation plot saved to: {plot_path}")


def plot_mean_attempts_per_template(db_manager: MongoDBManager) -> None:
    """Plots a bar chart of mean attempts of correct proposals for each template.

    For each template, the mean is calculated as:
       (sum(attempts) + 10000 * (# missing iterations)) / (max_iteration + 1)
    where # missing iterations = (max_iteration + 1) - number of proposals found.
    This function orders the templates in ascending order of the calculated mean.
    Two dashed vertical lines are drawn to divide the sorted templates into three groups of nearly equal size.
    Text labels 'easy', 'medium', and 'hard' are added above the respective groups.
    The bars retain their colors: blue for templates < 100 ("1_ball") and orange for templates >= 100 ("2_ball").
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

    plt.figure(figsize=(14, 6))
    x = list(range(total))
    plt.bar(
        x, sorted_means, tick_label=sorted_templates, width=0.7, color=sorted_colors
    )
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
    plots_dir = Path("plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plots_dir / "mean_attempts_by_template.png"
    plt.savefig(plot_path)
    plt.close()
    print(f"Mean attempts plot saved to: {plot_path}")


def extract_confidence_responses(db_manager: MongoDBManager) -> None:
    """Extracts and prints the valid response counts for evaluation_type 'confidence'.
    A valid response must contain a number (1-3 digits).
    Results are grouped by model_name, showing the count of valid responses over total responses.
    """
    import re

    query = {"evaluation_type": "confidence"}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")
    stats: dict[str, dict[str, int]] = {}
    for doc in cursor:
        model = doc.get("model_name", "Unknown")
        response = str(doc.get("response", ""))
        stats.setdefault(model, {"valid": 0, "total": 0})
        stats[model]["total"] += 1
        if re.search(r"\b\d{1,3}\b", response):
            stats[model]["valid"] += 1
    print("Confidence Evaluation Response Validity:")
    for model, counts in stats.items():
        print(
            f"Model: {model} - Valid Responses: {counts['valid']} / Total Responses: {counts['total']}"
        )


def plot_confidence_by_proposal_type(db_manager: MongoDBManager) -> None:
    """
    Generate and save 4 separate plots for evaluation results with evaluation_type 'confidence'.
    Each plot corresponds to one proposal tier: 'correct', 'incorrect_easy', 'incorrect_medium', and 'incorrect_hard'.
    For each template (derived from sample.puzzle.id), the 3 confidence points (from different iterations) are shown.
    Different models are plotted using distinct colors.
    """
    import re

    # Define the proposal types to plot
    proposal_types = ["correct", "incorrect_easy", "incorrect_medium", "incorrect_hard"]

    # Query evaluation_results with evaluation_type 'confidence'
    query = {"evaluation_type": "confidence"}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")

    # Data structure: {proposal_type: list of records}
    # Each record: { 'model': str, 'template': int, 'iteration': int, 'confidence': int }
    data: dict[str, list[dict[str, object]]] = {ptype: [] for ptype in proposal_types}

    for doc in cursor:
        try:
            # Extract model name
            model: str = doc.get("model_name", "Unknown")
            # Extract response and use regex to extract confidence value
            response: str = str(doc.get("response", ""))
            match = re.search(r"\b(\d{1,3})\b", response)
            if not match:
                continue
            confidence: int = int(match.group(1))
            # Get proposal tier from sample.proposal.tier and convert to lowercase
            sample = doc.get("sample", {})
            proposal = sample.get("proposal", {})
            tier: str = str(proposal.get("tier", "")).lower()
            # Only consider proposal types we are interested in
            if tier not in proposal_types:
                continue
            # Extract template and iteration from sample.puzzle.id
            puzzle = sample.get("puzzle", {})
            puzzle_id: str = str(puzzle.get("id", ""))
            if ":" not in puzzle_id:
                continue
            template_str, iter_str = puzzle_id.split(":")
            template: int = int(template_str)
            iteration: int = int(iter_str)

            # Append the record
            data[tier].append(
                {
                    "model": model,
                    "template": template,
                    "iteration": iteration,
                    "confidence": confidence,
                }
            )
        except Exception as e:
            # Skip any record with extraction issues
            continue

    # Define iteration offset mapping (assuming 3 iterations: 0,1,2)
    offsets = {0: -0.2, 1: 0.0, 2: 0.2}

    import matplotlib.cm as cm
    import matplotlib.pyplot as plt

    # For each proposal type, create a plot
    for ptype in proposal_types:
        records = data[ptype]
        if not records:
            print(f"No confidence evaluation records for proposal type: {ptype}")
            continue

        # Group records by model then by template
        # Structure: { model: { template: list of (iteration, confidence) } }
        model_group: dict[str, dict[int, list[tuple[int, int]]]] = {}
        for rec in records:
            model = rec["model"]  # type: ignore
            template = rec["template"]  # type: ignore
            iteration = rec["iteration"]  # type: ignore
            confidence = rec["confidence"]  # type: ignore
            if model not in model_group:
                model_group[model] = {}
            if template not in model_group[model]:
                model_group[model][template] = []
            model_group[model][template].append((iteration, confidence))

        # Determine global sorted templates present in any model for this proposal type
        global_templates: set[int] = set()
        for model_data in model_group.values():
            global_templates.update(model_data.keys())
        sorted_templates = sorted(global_templates)

        # Create a mapping from template id to discrete x position based on sorted order
        template_to_x = {temp: idx for idx, temp in enumerate(sorted_templates)}

        # Get distinct models for color assignment, filtering out models that contain 'meta-llama'
        models = [m for m in list(model_group.keys()) if "meta-llama" not in m.lower()]
        colors = cm.get_cmap("tab10", len(models))

        plt.figure(figsize=(12, 6))

        # Plot for each model with mean confidence per template
        for i, model in enumerate(models):
            x_vals = []
            y_vals = []
            # For each template that exists globally
            for temp in sorted_templates:
                if temp in model_group[model]:
                    recs = model_group[model][temp]
                    # Calculate the mean confidence for the template
                    mean_conf = sum(conf for (_, conf) in recs) / len(recs)
                    x_vals.append(template_to_x[temp])
                    y_vals.append(mean_conf)
            if x_vals:
                plt.scatter(x_vals, y_vals, color=colors(i), label=model)

        # Set x-axis ticks to be at discrete positions for each template
        xticks = list(template_to_x.values())
        xtick_labels = [str(temp) for temp in sorted_templates]
        plt.xticks(ticks=xticks, labels=xtick_labels, rotation=45)
        plt.xlabel("Template ID")
        plt.ylabel("Confidence (%)")
        plt.title(
            f'Confidence Evaluations for Proposal Type: {ptype.replace("_", " ").title()}'
        )
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        # Save plot to plots directory
        from pathlib import Path

        plots_dir = Path("plots")
        plots_dir.mkdir(parents=True, exist_ok=True)
        plot_path = plots_dir / f"confidence_{ptype}.png"
        plt.savefig(plot_path)
        plt.close()
        print(f"Confidence plot for '{ptype}' proposals saved to: {plot_path}")


def plot_confidence_violin_by_proposal_type(db_manager: MongoDBManager) -> None:
    """
    Generate and save a plot with 4 subplots (2 rows x 2 columns), one for each proposal type, showing violin plots of the confidence distributions for each model (excluding meta-llama models).
    Each subplot corresponds to one proposal type: 'correct', 'incorrect_easy', 'incorrect_medium', 'incorrect_hard'.
    The violin plots display the distribution of individual confidence values for each model with distinct colors, and a global legend is added.
    """
    import re

    import matplotlib.cm as cm
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Define the proposal types
    proposal_types = ["correct", "incorrect_easy", "incorrect_medium", "incorrect_hard"]

    # Query evaluation_results with evaluation_type 'confidence'
    query = {"evaluation_type": "confidence"}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")

    # Data structure: { proposal_type: list of records }
    # Each record: { 'model': str, 'confidence': int }
    data: dict[str, list[dict[str, object]]] = {ptype: [] for ptype in proposal_types}

    for doc in cursor:
        try:
            model: str = doc.get("model_name", "Unknown")
            # Exclude models containing 'meta-llama'
            if "meta-llama" in model.lower():
                continue
            response: str = str(doc.get("response", ""))
            match = re.search(r"\b(\d{1,3})\b", response)
            if not match:
                continue
            confidence: int = int(match.group(1))

            sample = doc.get("sample", {})
            proposal = sample.get("proposal", {})
            tier: str = str(proposal.get("tier", "")).lower()

            if tier not in proposal_types:
                continue

            data[tier].append({"model": model, "confidence": confidence})
        except Exception as e:
            continue

    # Create a global mapping of models to colors across all proposal types, ensuring they're strings
    global_models = set()
    for records in data.values():
        for rec in records:
            global_models.add(str(rec["model"]))
    sorted_global_models = sorted(global_models, key=str)
    cmap = cm.get_cmap("tab10", len(sorted_global_models))
    model_to_color = {model: cmap(i) for i, model in enumerate(sorted_global_models)}

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
            model = str(rec["model"])
            conf = int(str(rec["confidence"]))
            model_groups.setdefault(model, []).append(conf)

        # Determine models for this subplot sorted by global order
        models = sorted(
            model_groups.keys(), key=lambda m: sorted_global_models.index(m)
        )
        violin_data = [model_groups[m] for m in models]
        positions = list(range(1, len(models) + 1))

        parts = ax.violinplot(
            violin_data, positions=positions, showmeans=True, showmedians=False
        )
        # Set individual colors for each violin body
        for i, body in enumerate(parts["bodies"]):
            model = models[i]
            body.set_facecolor(model_to_color.get(model, (0.5, 0.5, 0.5, 1)))
            body.set_edgecolor("black")
            body.set_alpha(0.7)

        # Remove x-axis tick labels and x-axis label
        ax.set_xticks([])
        ax.set_title(ptype.replace("_", " ").title())
        # Optionally remove the x-axis label 'Model' if set
        # ax.set_xlabel("Model") removed as per request
        if idx % 2 == 0:
            ax.set_ylabel("Confidence (%)")
        ax.grid(True)

    # Remove any unused subplot axes if there are fewer than 4
    for j in range(len(proposal_types), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle("Confidence Violin Plots by Proposal Type", fontsize=16)

    # Create a global legend for models
    legend_handles = [
        Patch(facecolor=model_to_color[m], edgecolor="black", label=m)
        for m in sorted_global_models
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper right",
        bbox_to_anchor=(0.95, 0.88),
        ncol=1,
    )

    plt.tight_layout(rect=(0, 0, 1, 0.95))
    from pathlib import Path

    plots_dir = Path("plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plots_dir / "confidence_violin.png"
    plt.savefig(plot_path)
    plt.close()
    print(f"Confidence violin plot saved to: {plot_path}")


def plot_confidence_by_model(db_manager: MongoDBManager) -> None:
    """
    Generate and save a plot for each model, where the x-axis represents the template IDs and there are four lines (one per proposal tier).
    Each line shows the mean confidence values for that tier across templates. Colors are as follows:
      - correct: green
      - incorrect_hard: yellow
      - incorrect_medium: orange
      - incorrect_easy: red

    The filename will use only the model name without provider information.
    """
    import re
    from pathlib import Path
    from statistics import mean

    import matplotlib.pyplot as plt

    # Query evaluation_results with evaluation_type 'confidence'
    query = {"evaluation_type": "confidence"}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")

    # Group responses by model, then by proposal tier and template
    # Structure: { model: { tier: { template_id: [confidences] } } }
    model_data: dict[str, dict[str, dict[int, list[int]]]] = {}
    valid_tiers = {"correct", "incorrect_hard", "incorrect_medium", "incorrect_easy"}
    for doc in cursor:
        model = doc.get("model_name", "Unknown")
        response = str(doc.get("response", ""))
        m = re.search(r"\b(\d{1,3})\b", response)
        if not m:
            continue
        try:
            conf_value = int(m.group(1))
        except ValueError:
            continue
        sample = doc.get("sample", {})
        tier = str(sample.get("proposal", {}).get("tier", "")).lower()
        if tier not in valid_tiers:
            continue
        # Extract template id from sample.puzzle.id; assume format 'template:iteration'
        puzzle = sample.get("puzzle", {})
        puzzle_id = str(puzzle.get("id", ""))
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

    # Define colors for tiers
    color_map = {
        "correct": "green",
        "incorrect_hard": "yellow",
        "incorrect_medium": "orange",
        "incorrect_easy": "red",
    }

    # For each model, create a plot where x-axis is the index of the template
    for model, tier_dict in model_data.items():
        plt.figure(figsize=(10, 6))
        # Compute the union of template IDs across all tiers for this model
        all_templates = set()
        for tier in ["correct", "incorrect_hard", "incorrect_medium", "incorrect_easy"]:
            all_templates.update(tier_dict[tier].keys())
        if not all_templates:
            print(f"No valid templates for model: {model}")
            continue
        sorted_all_templates = sorted(all_templates)
        x_positions = list(range(len(sorted_all_templates)))

        plotted = False
        # For each tier, plot the mean confidence values at the corresponding index positions
        for tier in ["correct", "incorrect_hard", "incorrect_medium", "incorrect_easy"]:
            x_vals = []
            y_vals = []
            for i, temp in enumerate(sorted_all_templates):
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
        plt.title(f"Confidence Averages for Model: {model}")
        plt.xticks(x_positions, [str(t) for t in sorted_all_templates], rotation=45)
        plt.legend()
        plt.grid(True)

        plots_dir = Path("plots")
        plots_dir.mkdir(parents=True, exist_ok=True)
        # Use only the model name without provider info; assume provider info is separated by ':'
        simple_model = model.split(":")[-1].strip()
        sanitized_model = "".join(
            [c if c.isalnum() or c in ("_", "-") else "_" for c in simple_model]
        )
        plot_path = plots_dir / f"confidence_{sanitized_model}.png"
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        print(f"Confidence plot for model '{model}' saved to: {plot_path}")


def print_ranking_statistics(db_manager: MongoDBManager) -> None:
    """Print ranking evaluation statistics. For each model, count how many responses are a valid list of indexes and how many are not.

    A valid response is defined as a string that matches the pattern of a list of indexes, e.g. "[1, 2, 3]".
    The regex pattern used is ^\s*\[?\s*(\d+(?:\s*,\s*\d+)*)\s*\]?\s*.*$ which ensures the response is a properly formatted list.
    """
    import re

    # Query evaluation_results for ranking evaluations
    query = {"evaluation_type": "ranking", "few_shot_count": 0}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")

    # Dictionary to hold counts for each model
    stats: dict[str, dict[str, int]] = {}

    # Define updated regex pattern with optional square brackets and trailing characters, using DOTALL flag
    pattern = re.compile(r"^\s*\[?\s*(\d+(?:\s*,\s*\d+)*)\s*\]?\s*.*$", re.DOTALL)

    for doc in cursor:
        model: str = doc.get("model_name", "Unknown")
        response: str = str(doc.get("response", ""))
        if model not in stats:
            stats[model] = {"valid": 0, "invalid": 0}
        # Use the updated regex to extract the numbers
        match = pattern.search(response)
        if match:
            numbers_str = match.group(1)
            try:
                numbers = [
                    int(x.strip()) for x in numbers_str.split(",") if x.strip() != ""
                ]
                if numbers:
                    stats[model]["valid"] += 1
                else:
                    stats[model]["invalid"] += 1
            except ValueError:
                stats[model]["invalid"] += 1
        else:
            stats[model]["invalid"] += 1

    print("Ranking Evaluation Response Validity:")
    for model, counts in stats.items():
        total = counts["valid"] + counts["invalid"]
        print(
            f"Model: {model} - Valid Responses: {counts['valid']} / Total Responses: {total}"
        )


def verify_binary_responses(db_manager: MongoDBManager) -> None:
    """Print binary evaluation response validity: For each model, count and display valid responses ('yes' or 'no') versus total responses."""
    query = {"evaluation_type": "binary"}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")
    stats: dict[str, dict[str, int]] = {}

    for doc in cursor:
        model: str = doc.get("model_name", "Unknown")
        response: str = str(doc.get("response", "")).strip()
        if model not in stats:
            stats[model] = {"valid": 0, "invalid": 0}
        if response.lower() in ["yes", "no"]:
            stats[model]["valid"] += 1
        else:
            stats[model]["invalid"] += 1

    print("Binary Evaluation Response Validity:")
    for model, counts in stats.items():
        total = counts["valid"] + counts["invalid"]
        print(
            f"Model: {model} - Valid Responses: {counts['valid']} / Total Responses: {total}"
        )


def plot_binary_accuracy_by_proposal_type(db_manager: MongoDBManager) -> None:
    """Generates and saves a plot of binary response accuracy for valid samples,
    grouped by proposal type and model, for 0-shot and 2-shot.

    The plot has the y-axis as accuracy (%) and columns organized into 4 groups corresponding to proposal types
    (CORRECT, INCORRECT_HARD, INCORRECT_MEDIUM, INCORRECT_EASY). Each group contains bars for each model (colored by model)
    for the given few-shot setting (0-shot on the left, 2-shot on the right), separated by a central dashed line.

    Only valid binary responses are considered, and models containing 'meta-llama' are excluded.
    The expected binary answer is 'yes' if the proposal type is CORRECT, else 'no'.
    """
    from typing import Tuple

    import matplotlib.cm as cm
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    # Data structure: {few_shot_count: {proposal_type: {model: (correct_count, total_count)}}}
    accuracy_data: dict[int, dict[str, dict[str, Tuple[int, int]]]] = {0: {}, 2: {}}

    # Query binary evaluation results for few_shot_count 0 and 2
    query = {"evaluation_type": "binary", "few_shot_count": {"$in": [0, 2]}}
    cursor = db_manager.db["evaluation_results"].find(query).sort("model_name")
    for doc in cursor:
        few_shot = doc.get("few_shot_count", 0)
        if few_shot not in [0, 2]:
            continue
        model: str = doc.get("model_name", "Unknown")
        if "meta-llama" in model.lower():
            continue
        response: str = str(doc.get("response", "")).strip().lower()
        if response not in ["yes", "no"]:
            continue
        # Get proposal tier and standardize to uppercase
        tier: str = str(
            doc.get("sample", {}).get("proposal", {}).get("tier", "")
        ).upper()
        if tier not in {
            "CORRECT",
            "INCORRECT_HARD",
            "INCORRECT_MEDIUM",
            "INCORRECT_EASY",
        }:
            continue
        expected = "yes" if tier == "CORRECT" else "no"
        is_correct = 1 if response == expected else 0
        if tier not in accuracy_data[few_shot]:
            accuracy_data[few_shot][tier] = {}
        if model not in accuracy_data[few_shot][tier]:
            accuracy_data[few_shot][tier][model] = (0, 0)
        prev_correct, prev_total = accuracy_data[few_shot][tier][model]
        accuracy_data[few_shot][tier][model] = (
            prev_correct + is_correct,
            prev_total + 1,
        )

    # Determine union of models across few_shot types for consistent coloring
    union_models = set()
    for shot in [0, 2]:
        for tier_data in accuracy_data[shot].values():
            union_models.update(tier_data.keys())
    union_models = sorted(union_models)

    # Setup colormap for models
    cmap = cm.get_cmap("tab10", len(union_models))
    model_to_color = {model: cmap(i) for i, model in enumerate(union_models)}

    proposal_types = ["CORRECT", "INCORRECT_HARD", "INCORRECT_MEDIUM", "INCORRECT_EASY"]

    # Create a figure with two subplots: one for 0-shot and one for 2-shot
    fig, axes = plt.subplots(ncols=2, figsize=(16, 6), sharey=True)
    shot_labels = {0: "0-shot", 2: "2-shot"}

    # Use union_models for consistent ordering in both subplots
    n_models = len(union_models)
    bar_width = 0.8 / n_models if n_models > 0 else 0.8
    x_groups = np.arange(len(proposal_types))  # one per proposal type

    for ax, shot in zip(axes, [0, 2]):
        for i, tier in enumerate(proposal_types):
            for j, model in enumerate(union_models):
                correct, total = accuracy_data[shot].get(tier, {}).get(model, (0, 0))
                acc = (correct / total * 100) if total > 0 else 0
                # Calculate bar position within the group
                x = x_groups[i] + (j - (n_models - 1) / 2) * bar_width
                ax.bar(x, acc, width=bar_width, color=model_to_color[model])
        ax.set_xticks(x_groups)
        ax.set_xticklabels(proposal_types)
        ax.set_xlabel("Proposal Type")
        ax.set_title(shot_labels[shot])
        ax.grid(axis="y")
        ax.set_ylim(0, 100)
        ax.set_ylabel("Accuracy (%)")

    # Add a central dashed vertical line between the two subplots
    fig.canvas.draw()
    left_pos = axes[0].get_position()
    right_pos = axes[1].get_position()
    x_line = left_pos.x1 + (right_pos.x0 - left_pos.x1) / 2
    fig.add_artist(
        Line2D(
            [x_line, x_line],
            [0, 1],
            transform=fig.transFigure,
            color="black",
            linestyle="--",
        )
    )

    # Create a global legend for models
    legend_handles = [
        Rectangle((0, 0), 1, 1, color=model_to_color[m]) for m in union_models
    ]
    fig.legend(legend_handles, union_models, loc="upper right", title="Models")

    from pathlib import Path

    plots_dir = Path("plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    plot_path = plots_dir / "binary_accuracy_by_proposal_type.png"
    plt.tight_layout()
    plt.savefig(plot_path)
    plt.close()
    print(f"Binary accuracy plot saved to: {plot_path}")


def main() -> None:
    parser = ArgparseManager("Plot statistics from MongoDB.")
    parser.add_common_db_args()
    # parser.add_stats_args()
    args = parser.parse_args()

    db_manager = MongoDBManager(db_name=args.db_name)

    # Uncomment the plot function you want to run
    # plot_mean_attempts_per_template(db_manager)
    # plot_evaluation_results(db_manager, few_shot_count=0)
    extract_confidence_responses(db_manager)
    # plot_confidence_by_proposal_type(db_manager)
    # plot_confidence_violin_by_proposal_type(db_manager)
    # plot_confidence_by_model(db_manager)
    # print_ranking_statistics(db_manager)
    # verify_binary_responses(db_manager)
    # plot_binary_accuracy_by_proposal_type(db_manager)
    db_manager.close_connection()


if __name__ == "__main__":
    main()
