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
