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
    testable: bool = True


class PuzzleSchema(BaseModel):
    id: str
    bodies: list[BodyData]
    relationship: RelationshipData
    metadata: MetadataData
    image_path: str | None = None


class ProposalData(BaseModel):
    radius: float
    position: list[float]


class ProposalSchema(BaseModel):
    id: str
    attempt: int
    proposals: list[ProposalData]
    image_path: str
    tier: str


class FewShotData(BaseModel):
    puzzle: PuzzleSchema
    proposal: ProposalSchema
    images: list[str]
    index: int


class SampleData(BaseModel):
    puzzle: PuzzleSchema
    proposal: ProposalSchema
    images: list[str]
    few_shot: list[FewShotData] | None = None


# New schema classes for ranking samples
class RankingProposalItem(BaseModel):
    """A single proposal in a ranking sample"""

    proposal: ProposalSchema
    images: list[str]
    tier: str  # Used for tracking the original tier (CORRECT, INCORRECT_EASY, etc.)
    original_index: int  # Track the original position before shuffling


class RankingMetadata(BaseModel):
    """Metadata for ranking samples"""

    correct_ranking: list[int]  # The correct order indices after shuffling
    proposal_tiers: list[str]  # The tier of each proposal in order


class RankingSampleData(SampleData):
    """Extended sample data for ranking tasks with multiple proposals"""

    proposals: list[RankingProposalItem]
    metadata: RankingMetadata


# New schema class for ranking few-shot examples
class RankingFewShotData(FewShotData):
    """Extended few-shot data for ranking tasks with multiple proposals"""

    proposals: list[ProposalSchema]
    images_list: list[list[str]]
    metadata: RankingMetadata


class InteractiveEvalResult(BaseModel):
    """Result of an interactive evaluation."""

    status: str
    message: str
    ball_data: dict | list[dict] | None = None
    screenshots: list[str] | None = None  # List of file paths to screenshots


class EvaluationResultSchema(BaseModel):
    """Schema for storing evaluation results in MongoDB."""

    evaluation_type: str
    model_name: str
    sample: SampleData
    few_shot_count: int
    few_shot_frames: int
    correct: bool
    ground_truth: Any
    response: Any
    interactive_results: list[InteractiveEvalResult] | None = None
