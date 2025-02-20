"""
MongoDB Manager to handle puzzle insertion.
"""

from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from pymongo import MongoClient

from ..utils.db_schemas import PuzzleSchema
from .base_manager import BaseManager


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
    def db(self):
        return self._db

    def insert_puzzle(self, puzzle_data: PuzzleSchema) -> None:
        """
        Insert a puzzle document into the puzzles collection.
        """
        doc = puzzle_data.model_dump()
        self._db["puzzles"].insert_one(doc)

    def close_connection(self) -> None:
        """
        Closes the database connection.
        """
        if self._client:
            self._client.close()
            logger.info("Closed MongoDB connection.")
