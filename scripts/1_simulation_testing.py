"""Simulation testing script for PhysIQ.

This script contains utilities for testing physics simulations.
"""

import argparse
from pathlib import Path
from loguru import logger


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run physics simulation tests.")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Path to simulation configuration file",
    )
    parser.add_argument(
        "--visualize", action="store_true", help="Enable visualization of simulations"
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> None:
    """Main function for simulation testing."""
    logger.info(f"Running simulation tests with config: {args.config}")


if __name__ == "__main__":
    args = parse_args()
    main(args)
