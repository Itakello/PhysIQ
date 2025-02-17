"""Dataset creation script for PhysIQ.

This script handles the generation of physics simulation datasets.
"""

import argparse
from pathlib import Path
from loguru import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate physics simulation datasets."
    )
    parser.add_argument(
        "-c", "--config", type=str, required=True, help="Name of the configuration"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for generated datasets",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    """Main function for dataset creation."""
    logger.info(f"Creating dataset using config: {args.config}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
