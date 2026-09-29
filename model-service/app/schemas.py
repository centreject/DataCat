from typing import Literal

from pydantic import BaseModel, model_validator

from app.language.purposes import CATALOG

# Allowed purpose values come from app/language/purposes.json (덕민님's classification plan).
Purpose = Literal[CATALOG.ids]  # type: ignore[valid-type]


class Detection(BaseModel):
    label: Literal["person", "package"]
    confidence: float


class DetectResponse(BaseModel):
    detections: list[Detection]


class TranscribeResponse(BaseModel):
    transcript: str


class AnalyzeRequest(BaseModel):
    transcript: str


class Analysis(BaseModel):
    summary: str
    purpose: Purpose
    subtype: str | None = None  # only for purposes that have subtypes (DELIVERY)

    @model_validator(mode="after")
    def _subtype_belongs_to_purpose(self):
        allowed = CATALOG.subtypes(self.purpose)
        if self.subtype is not None and self.subtype not in allowed:
            raise ValueError(f"subtype {self.subtype!r} is not valid for {self.purpose}")
        return self


class AudioProcessResponse(BaseModel):
    transcript: str
    purpose: Purpose
    subtype: str | None = None
    summary: str
