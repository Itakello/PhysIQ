"""Dataset expansion script for PhysIQ.

This script handles the expansion of existing datasets with new examples.
"""

import argparse
from pathlib import Path
from loguru import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Expand existing datasets with new examples."
    )
    parser.add_argument(
        "-d",
        "--dataset-path",
        type=Path,
        required=True,
        help="Path to existing dataset",
    )
    parser.add_argument(
        "-n",
        "--num-examples",
        type=int,
        required=True,
        help="Number of new examples to generate",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    """Main function for dataset expansion."""
    logger.info(
        f"Expanding dataset at {args.dataset_path} with {args.num_examples} examples"
    )


if __name__ == "__main__":
    args = parse_args()
    main(args)
