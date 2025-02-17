"""Dataset conversion script for PhysIQ.

This script handles the conversion of raw data into the required format for training.
"""

import argparse
from pathlib import Path

from loguru import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert raw datasets to training format."
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for converted data",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    logger.info(f"Converting data from {args.input_dir} to {args.output_dir}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
