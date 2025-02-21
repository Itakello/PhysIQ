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
    body_type: int
    color: int
    shape_type: int
    angle: float | None = None
    vertices: list[list[float]] | None = None
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
    tier: str
    type: str


class PuzzleSchema(BaseModel):
    id: str
    bodies: list[BodyData]
    relationship: RelationshipData
    metadata: MetadataData


class ProposalSchema(BaseModel):
    id: str
    is_good: bool
    attempt: int
    radius: float
    position: list[float]
    image_path: str
