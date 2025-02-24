"""
Manager for creating and manipulating puzzles.
"""

from dataclasses import dataclass, field
from typing import Sequence

from loguru import logger

from ..utils.db_schemas import (
    BodyData,
    MetadataData,
    PuzzleSchema,
    RelationshipData,
    ShapeData,
)
from .base_manager import BaseManager


@dataclass
class PuzzleManager(BaseManager):
    """Manager class to handle puzzle creation and manipulation."""

    template_id: int = 200
    iteration: int = 0
    borders: list[BodyData] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Create default borders after initialization."""
        self.borders = self._create_default_borders()

    def _create_default_borders(self) -> list[BodyData]:
        """Create the four default border walls."""
        return [
            self.create_polygon_body(  # Bottom border
                position=[128.0, -2.5],
                vertices=[[128.0, 2.5], [-128.0, 2.5], [-128.0, -2.5], [128.0, -2.5]],
                body_type=0,
                color=6,
            ),
            self.create_polygon_body(  # Left border
                position=[-2.5, 128.0],
                vertices=[[2.5, 128.0], [-2.5, 128.0], [-2.5, -128.0], [2.5, -128.0]],
                body_type=0,
                color=6,
            ),
            self.create_polygon_body(  # Top border
                position=[128.0, 258.5],
                vertices=[[128.0, 2.5], [-128.0, 2.5], [-128.0, -2.5], [128.0, -2.5]],
                body_type=0,
                color=6,
            ),
            self.create_polygon_body(  # Right border
                position=[258.5, 128.0],
                vertices=[[2.5, 128.0], [-2.5, 128.0], [-2.5, -128.0], [2.5, -128.0]],
                body_type=0,
                color=6,
            ),
        ]

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

    def create_compound_body(
        self,
        position: list[float],
        shapes: list[ShapeData],
        body_type: int = 0,
        color: int = 0,
        angle: float = 0.0,
    ) -> BodyData:
        """Create a compound body made up of multiple shapes."""
        return BodyData(
            position=position,
            body_type=body_type,
            color=color,
            shape_type=3,  # Compound shape type
            shapes=shapes,
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
        include_borders: bool = True,
    ) -> PuzzleSchema:
        """
        Create a complete puzzle with the given components.

        Args:
            bodies: List of body definitions
            relationship: Relationship between target bodies
            metadata: Puzzle metadata
            include_borders: Whether to include default borders
        """
        # Format ID as "00000:00" (template_id:iteration)
        puzzle_id = f"{self.template_id:05d}:{self.iteration:02d}"

        logger.info(f"Creating puzzle {puzzle_id}")

        all_bodies = self.borders + list(bodies) if include_borders else list(bodies)
        return PuzzleSchema(
            id=puzzle_id,
            bodies=all_bodies,
            relationship=relationship,
            metadata=metadata,
        )
