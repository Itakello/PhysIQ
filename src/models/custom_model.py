from abc import ABC, abstractmethod
from enum import Enum

import weave
from pydantic import BaseModel


class ModelBackend(Enum):
    HF = "hf"
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"


class CustomModel(ABC, weave.Model, BaseModel):
    id: str
    backend: ModelBackend

    def __str__(self) -> str:
        return f"{self.backend} model: {self.id}"

    @abstractmethod
    @weave.op
    def predict(self, question: str) -> str:
        pass
