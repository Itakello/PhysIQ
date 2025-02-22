import argparse
from dataclasses import dataclass, field
from email.policy import default

from .base_manager import BaseManager


@dataclass
class ArgparseManager(BaseManager):
    description: str
    parser: argparse.ArgumentParser = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the argument parser with the given description."""
        self.parser = argparse.ArgumentParser(description=self.description)

    def add_common_db_args(self) -> None:
        """Add common database-related arguments."""
        self.parser.add_argument(
            "--db_name",
            type=str,
            default="physiq_db",
            help="Name of the MongoDB database to connect to",
        )

    def add_common_simulation_args(self) -> None:
        """Add common simulation-related arguments."""
        self.parser.add_argument(
            "--start_template",
            type=int,
            default=0,
            help="Index of the first template to test",
        )
        self.parser.add_argument(
            "--iterations",
            type=int,
            default=100,
            help="Number of puzzle iterations to process per template",
        )
        self.parser.add_argument(
            "--visualize",
            action="store_true",
            help="Enable PyGame window rendering",
        )

    def add_io_args(
        self, input_folder: str | None = None, output_folder: str | None = None
    ) -> None:
        """Add common input/output directory arguments."""
        if input_folder:
            self.parser.add_argument(
                "--input-dir",
                type=str,
                help=f"Directory where JSON files have been saved (default: {input_folder})",
                default=input_folder,
            )
        if output_folder:
            self.parser.add_argument(
                "--output-dir",
                type=str,
                help=f"Directory where JSON files will be saved (default: {output_folder})",
                default=output_folder,
            )

    def add_proposal_args(self) -> None:
        """Add proposal-specific arguments."""
        self.parser.add_argument(
            "--num_proposals",
            type=int,
            default=3,
            help="How many good and bad proposals to gather for each puzzle",
        )
        self.parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible position/radius generation",
        )

    def parse_args(self) -> argparse.Namespace:
        """Parse and return the command line arguments."""
        return self.parser.parse_args()
