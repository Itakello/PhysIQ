"""Offline evaluation script for PhysIQ.

This script handles offline evaluation of models using pre-generated datasets.
"""

import argparse
from pathlib import Path
from loguru import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Evaluate models offline on datasets.")
    parser.add_argument(
        "-m", "--model-path", type=Path, required=True, help="Path to the model file"
    )
    parser.add_argument(
        "-d",
        "--dataset-path",
        type=Path,
        required=True,
        help="Path to evaluation dataset",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    """Main function for offline evaluation."""
    logger.info(f"Evaluating model: {args.model_path} on dataset: {args.dataset_path}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
