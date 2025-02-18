"""
Puzzle Schema definitions using Pydantic.
"""

from typing import Any

from pydantic import BaseModel


class ShapeData(BaseModel):
    type: str | None
    vertices: list[list[float]] | None


class BodyData(BaseModel):
    position: list[float]
    bodyType: int
    angle: float
    color: int
    shapeType: int
    diameter: float | None = None
    radius: float | None = None
    shapes: list[ShapeData] | None = None
    # Add other optional fields as needed


class RelationshipData(BaseModel):
    bodyId1: int
    bodyId2: int
    relationships: list[int]


class MetadataData(BaseModel):
    description: str
    tier: int


class PuzzleSchema(BaseModel):
    puzzle_id: str
    scene_dimensions: list[int]
    bodies: list[BodyData]
    relationship: RelationshipData
    metadata: MetadataData

    # Additional metadata or fields you might want to store
    # e.g., puzzle_type, creation_time, etc.
    puzzle_type: str | None = None
    extra_info: dict[str, Any] | None = None
