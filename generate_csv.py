import csv
import json
import os
from typing import Any

# Base path for the templates folder
BASE_PATH = "data/templates"

# Output CSV file path
OUTPUT_CSV = "simulation_results.csv"


def process_folder(base_path) -> list[Any]:
    rows = []

    for category in os.listdir(base_path):  # e.g., "1_ball", "2_ball"
        category_path = os.path.join(base_path, category)

        if not os.path.isdir(category_path):
            continue

        for level in sorted(os.listdir(category_path)):  # e.g., "00000", "00001"
            level_path = os.path.join(category_path, level)

            if not os.path.isdir(level_path):
                continue

            for iteration in sorted(os.listdir(level_path)):  # e.g., "00", "01"
                iteration_path = os.path.join(level_path, iteration)

                if not os.path.isdir(iteration_path):
                    continue

                for config in os.listdir(
                    iteration_path
                ):  # e.g., "default", "higher_density"
                    config_path = os.path.join(iteration_path, config)

                    if not os.path.isdir(config_path):
                        continue

                    row = {
                        "Category": category,
                        "Level": level,
                        "Iteration": iteration,
                        "Configuration": config,
                        "Good Proposals": 0,
                        "Bad Proposals": 0,
                        "Max Attempts": 0,
                    }

                    # Count good and bad proposals
                    for file in os.listdir(config_path):
                        if file.endswith(".json"):
                            file_path = os.path.join(config_path, file)
                            with open(file_path, "r") as f:
                                data = json.load(f)
                                if "good" in file:
                                    row["Good Proposals"] += 1
                                elif "bad" in file:
                                    row["Bad Proposals"] += 1
                                row["Max Attempts"] = max(
                                    data["attempt"], row["Max Attempts"]
                                )

                    rows.append(row)

    return rows


def write_to_csv(rows, output_csv) -> None:
    with open(output_csv, mode="w", newline="") as csvfile:
        fieldnames = [
            "Category",
            "Level",
            "Iteration",
            "Configuration",
            "Good Proposals",
            "Bad Proposals",
            "Max Attempts",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = process_folder(BASE_PATH)
    write_to_csv(rows, OUTPUT_CSV)
    print(f"CSV file created at: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
