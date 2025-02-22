"""
MongoDB Manager to handle puzzle insertion.
"""

from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from pymongo import MongoClient

from ..utils.db_schemas import PuzzleSchema
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

    def get_grouped_templates(
        self, start_template: int, iterations: int
    ) -> dict[int, list[dict]]:
        """
        Return all puzzles from the DB, grouped by their template (integer part of id).
        Also sort each group by iteration, then slice up to `iterations`.
        """
        all_puzzles = list(self._db["puzzles"].find({}))
        # Sort by puzzle_id => parse_template_id
        all_puzzles.sort(key=lambda p: parse_puzzle_id(p["id"]))

        grouped = {}
        for p in all_puzzles:
            t_id, i_id = parse_puzzle_id(p["id"])
            if t_id < start_template:
                continue
            grouped.setdefault(t_id, []).append(p)

        # Keep only up to 'iterations' from each group
        for k in grouped:
            grouped[k] = grouped[k][:iterations]
        return grouped

    def close_connection(self) -> None:
        """
        Closes the database connection.
        """
        if self._client:
            self._client.close()
            logger.info("Closed MongoDB connection.")
