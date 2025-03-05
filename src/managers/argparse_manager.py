import argparse
import sys
from dataclasses import dataclass, field

from loguru import logger

from .base_manager import BaseManager


@dataclass
class ArgparseManager(BaseManager):
    description: str
    parser: argparse.ArgumentParser = field(init=False)

    def __post_init__(self) -> None:
        """Initialize the argument parser with the given description."""
        self.parser = argparse.ArgumentParser(description=self.description)
        self._add_debug_args()

    def _add_debug_args(self) -> None:
        """Add debug-related arguments."""
        self.parser.add_argument(
            "--debug",
            action="store_true",
            default=False,
            help="Enable debug logging level",
        )

    def _set_loguru_level(self, debug: bool) -> None:
        """Set the loguru logging level based on the debug argument."""
        logger.remove()

        default_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level.icon}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        logger.add(
            sys.stderr,
            level="DEBUG" if debug else "INFO",
            colorize=True,
            format=default_format,
        )

    def add_common_db_args(self) -> None:
        """Add common database-related arguments."""
        self.parser.add_argument(
            "--db_name",
            type=str,
            default="physiq_db",
            help="Name of the MongoDB database to connect to",
        )
        self.parser.add_argument(
            "--save_to_db", action="store_true", help="Save to MongoDB"
        )

    def add_common_simulation_args(self) -> None:
        """Add common simulation-related arguments."""
        start_template = 0
        self.parser.add_argument(
            "--start_template",
            type=int,
            default=start_template,
            help=f"Index of the first template to test (default: {start_template})",
        )
        start_iteration = 0
        self.parser.add_argument(
            "--start_iteration",
            type=int,
            default=start_iteration,
            help=f"Index of the first iteration to test (default: {start_iteration})",
        )
        stop_template = 124
        self.parser.add_argument(
            "--stop_template",
            type=int,
            default=stop_template,
            help=f"Index of the last template to test (default: {stop_template})",
        )
        iterations = 100
        self.parser.add_argument(
            "--iterations",
            type=int,
            default=iterations,
            help=f"Number of puzzle iterations to process per template (default: {iterations})",
        )
        self.parser.add_argument(
            "--visualize",
            action="store_true",
            help="Enable PyGame window rendering",
        )
        self.parser.add_argument(
            "--templates_type", type=str, default="PHYRE", choices=["PHYRE", "TEST"]
        )

    def add_evaluation_args(self, default_output_dir: str = "results") -> None:
        """Add evaluation-specific arguments.

        Args:
            default_output_dir: Default directory to save evaluation results
        """
        self.parser.add_argument(
            "--models",
            type=str,
            nargs="+",
            help="Models to evaluate (can specify multiple)",
            default=["google/gemini-2.0-flash-thinking-exp:free", "openai/gpt-4o"],
        )

        self.parser.add_argument(
            "--evaluation_type",
            type=str,
            choices=["binary", "ranking", "sanity_check", "interactive", "confidence"],
            default="sanity_check",
            help="Type of evaluation to run",
        )

        self.parser.add_argument(
            "--few_shot_count",
            type=int,
            default=1,
            help="Number of few-shot examples to include",
            choices=range(0, 5),
        )

        self.parser.add_argument(
            "--few_shot_frames",
            type=int,
            default=1,
            help="Number of frames per few-shot example",
            choices=range(0, 5),
        )

        self.parser.add_argument(
            "--output_dir",
            type=str,
            default=default_output_dir,
            help="Directory to save evaluation results",
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

    def add_seed_args(self) -> None:
        """Add seed argument."""
        self.parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible position/radius generation",
        )

    def add_stats_args(self) -> None:
        """Add statistics-related arguments."""
        self.parser.add_argument(
            "--save-csv", action="store_true", help="Save results as CSV"
        )

    def add_model_args(self, default_model: str = "openai/gpt-4o") -> None:
        """Add VLM model selection argument.

        Args:
            default_model: Default model to use if not specified
        """
        self.parser.add_argument(
            "--vlm",
            type=str,
            default=default_model,
            choices=[
                "openai/gpt-4o",
                "anthropic/claude-3-5-sonnet",
                "deepseek/deepseek-chat",
                "gemini-2.0-flash",
                "xai/grok-2-latest",
            ],
            help=f"VLM model to use (default: {default_model})",
        )

    def parse_args(self) -> argparse.Namespace:
        """Parse command line arguments and configure logging level."""
        args = self.parser.parse_args()
        self._set_loguru_level(args.debug)
        return args
