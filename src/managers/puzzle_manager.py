"""
Manager for creating and manipulating puzzles.
"""

from dataclasses import dataclass
from typing import Sequence

from loguru import logger

from ..utils.db_schemas import BodyData, MetadataData, PuzzleSchema, RelationshipData
from .base_manager import BaseManager


@dataclass
class PuzzleManager(BaseManager):
    """Manager class to handle puzzle creation and manipulation."""

    current_template_id: int = 200

    def create_circle_body(
        self,
        position: list[float],
        radius: float,
        body_type: int = 0,
        color: int = 0,
    ) -> BodyData:
        """Create a circular body for the puzzle."""
        return BodyData(
            position=position,
            body_type=body_type,  # 0=static, 1=dynamic
            color=color,
            shape_type=1,
            radius=radius,
            angle=0.0,
        )

    def create_polygon_body(
        self,
        position: list[float],
        vertices: list[list[float]],
        body_type: int = 0,
        color: int = 0,
        angle: float = 0.0,
    ) -> BodyData:
        """Create a polygon body for the puzzle."""
        return BodyData(
            position=position,
            body_type=body_type,
            color=color,
            shape_type=0,
            vertices=vertices,
            angle=angle,
        )

    def create_relationship(
        self, body1_idx: int, body2_idx: int, relationships: list[int]
    ) -> RelationshipData:
        """Create a relationship between two bodies."""
        return RelationshipData(
            bodyId1=body1_idx,
            bodyId2=body2_idx,
            relationships=relationships,
        )

    def create_metadata(
        self, description: str, tier: str = "easy", type: str = "standard"
    ) -> MetadataData:
        """Create metadata for the puzzle."""
        return MetadataData(description=description, tier=tier, type=type)

    def create_puzzle(
        self,
        bodies: Sequence[BodyData],
        relationship: RelationshipData,
        metadata: MetadataData,
        iteration: int = 0,
    ) -> PuzzleSchema:
        """
        Create a complete puzzle with the given components.

        Args:
            bodies: List of body definitions
            relationship: Relationship between target bodies
            metadata: Puzzle metadata
            iteration: Puzzle iteration number (for variants of same template)
        """
        # Format ID as "00000:00" (template_id:iteration)
        puzzle_id = f"{self.current_template_id:05d}:{iteration:02d}"

        logger.info(f"Creating puzzle {puzzle_id}")

        return PuzzleSchema(
            id=puzzle_id,
            bodies=list(bodies),
            relationship=relationship,
            metadata=metadata,
        )

    def increment_template(self) -> None:
        """Move to next template ID."""
        self.current_template_id += 1
