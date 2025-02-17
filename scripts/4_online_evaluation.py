"""Online evaluation script for PhysIQ.

This script handles real-time evaluation of models in simulation.
"""

import argparse
from pathlib import Path
from loguru import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate models in real-time simulation."
    )
    parser.add_argument(
        "-m", "--model-path", type=Path, required=True, help="Path to the model file"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Path to simulation configuration",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    """Main function for online evaluation."""
    logger.info(f"Running online evaluation of model: {args.model_path}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
