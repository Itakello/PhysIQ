from pathlib import Path

import pandas as pd

from src.managers import ArgparseManager, MongoDBManager


def format_and_save_stats(
    stats: list[dict], save: bool, filename: str = "stats"
) -> None:
    """Format stats as a table and optionally save as CSV.

    Args:
        stats: List of statistics dictionaries
        save: Whether to save as CSV
        filename: Name of CSV file (without extension)
    """
    df = pd.DataFrame(stats)

    # Print formatted table
    print("\nStatistics:")
    print(df.to_string(index=False))

    if save:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        csv_path = results_dir / f"{filename}.csv"
        df.to_csv(csv_path, index=False)
        print(f"\nSaved CSV to: {csv_path}")


def main() -> None:
    parser = ArgparseManager("Plot statistics from MongoDB.")
    parser.add_common_db_args()
    parser.add_stats_args()
    args = parser.parse_args()

    db_manager = MongoDBManager(db_name=args.db_name)
    proposals_stats = db_manager.get_proposals_stats()
    db_manager.close_connection()

    format_and_save_stats(proposals_stats, args.save_csv, "proposals_stats")


if __name__ == "__main__":
    main()
