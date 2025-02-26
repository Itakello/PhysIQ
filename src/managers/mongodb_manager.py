"""
MongoDB Manager to handle puzzle insertion.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger
from pymongo import MongoClient

from ..utils.db_schemas import ProposalSchema, PuzzleSchema
from .base_manager import BaseManager


def parse_puzzle_id(puzzle_id: str) -> tuple[int, int]:
    # "00012:34" -> (12, 34)
    main_part, iteration_part = puzzle_id.split(":")
    return int(main_part), int(iteration_part)


@dataclass
class MongoDBManager(BaseManager):
    """
    Manager class to handle MongoDB operations for puzzle insertion.
    """

    db_name: str
    uri: str = field(default="mongodb://localhost:27017")
    _client: MongoClient | None = field(init=False, default=None)
    _db: Any = field(init=False, default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        logger.info(f"Connecting to MongoDB at {self.uri} / Database: {self.db_name}")
        self._client = MongoClient(self.uri)
        self._db = self._client[self.db_name]

    @property
    def db(self) -> Any:
        return self._db

    def insert_puzzle(self, puzzle_data: PuzzleSchema) -> None:
        """
        Insert a puzzle document into the puzzles collection.
        """
        doc = puzzle_data.model_dump()
        self._db["puzzles"].insert_one(doc)

    def insert_proposal(self, proposal_data: ProposalSchema) -> None:
        """
        Insert a proposal document into the proposals collection.
        """
        doc = proposal_data.model_dump()
        self._db["proposals"].insert_one(doc)

    def set_puzzle_testability(self, puzzle_id: str, testability: bool) -> None:
        """
        Set a puzzle as untestable by updating its metadata.
        """
        self._db["puzzles"].update_one(
            {"id": puzzle_id},
            {"$set": {"metadata.testable": testability}},
        )

    def set_puzzle_screenshot(self, puzzle_id: str, screenshot_path: Path) -> None:
        """
        Set a puzzle's screenshot path by updating its metadata.
        """
        self._db["puzzles"].update_one(
            {"id": puzzle_id},
            {"$set": {"image_path": screenshot_path.as_posix()}},
        )

    def get_grouped_templates(
        self,
        start_template: int,
        stop_template: int,
        start_iteration: int,
        iterations: int,
        type: str = "PHYRE",
        only_testable: bool = False,
    ) -> dict[int, list[dict]]:
        """
        Return all puzzles from the DB with matching type, grouped by their template (integer part of id).
        Also sort each group by iteration, then slice up to `iterations`.

        Args:
            start_template: The template ID to start from
            iterations: Maximum number of iterations to include per template
            type: The puzzle type to filter by (defaults to "PHYRE")
        """
        filter = {"metadata.type": type}
        if only_testable:
            filter["metadata.testable"] = True  # type: ignore
        all_puzzles = list(self._db["puzzles"].find(filter))
        # Sort by puzzle_id => parse_template_id
        all_puzzles.sort(key=lambda p: parse_puzzle_id(p["id"]))

        grouped = {}
        for p in all_puzzles:
            t_id, i_id = parse_puzzle_id(p["id"])
            if t_id < start_template or t_id > stop_template:
                continue
            grouped.setdefault(t_id, []).append(p)

        # Keep only up to 'iterations' from each group
        for k in grouped:
            grouped[k] = grouped[k][start_iteration : start_iteration + iterations]
        return grouped

    def get_puzzle(
        self, template_id: int, iteration_id: int, type: str = "PHYRE"
    ) -> PuzzleSchema | None:
        """
        Get a specific puzzle by template and iteration ID.

        Args:
            template_id: The template ID
            iteration_id: The iteration ID
            type: The puzzle type to filter by (defaults to "PHYRE")

        Returns:
            The puzzle if found, None otherwise
        """
        puzzle_id = f"{template_id:05d}:{iteration_id:03d}"
        puzzle = self._db["puzzles"].find_one({"id": puzzle_id, "metadata.type": type})
        if puzzle is None:
            return None
        return PuzzleSchema(**puzzle)

    def close_connection(self) -> None:
        """
        Closes the database connection.
        """
        if self._client:
            self._client.close()
            logger.info("Closed MongoDB connection.")

    def get_proposals_stats(self) -> list[dict]:
        """
        Get statistics for each template, including:
        - Number of puzzles with proposals (0-3)
        - Average number of attempts across all puzzles in the template

        Returns:
            List of dictionaries containing template stats, sorted by template ID:
            [
                {
                    "_id": template_id,
                    "avgAttempts": float,
                    "totalPuzzles": int
                },
                ...
            ]
        """
        return list(
            self._db["proposals"].aggregate(
                [
                    {
                        "$group": {
                            "_id": "$id",
                            "attempt": {"$first": "$attempt"},
                            "templateId": {
                                "$first": {
                                    "$toInt": {
                                        "$arrayElemAt": [{"$split": ["$id", ":"]}, 0]
                                    }
                                }
                            },
                        }
                    },
                    {
                        "$group": {
                            "_id": {"puzzleId": "$_id", "templateId": "$templateId"},
                            "attempt": {"$first": "$attempt"},
                        }
                    },
                    {
                        "$group": {
                            "_id": "$_id.templateId",
                            "attempts": {"$push": "$attempt"},
                            "avgAttempts": {"$avg": "$attempt"},
                        }
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "avgAttempts": {"$round": ["$avgAttempts", 2]},
                            "totalPuzzles": {"$size": "$attempts"},
                        }
                    },
                    {"$sort": {"_id": 1}},
                ]
            )
        )

    def get_correct_proposal(self, puzzle_id: str) -> ProposalSchema | None:
        """Get all correct proposals for a given puzzle."""
        data = self._db["proposals"].find_one({"id": puzzle_id, "tier": "CORRECT"})
        if data is None:
            return None
        return ProposalSchema(**data)
