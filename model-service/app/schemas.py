from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.language.purposes import CATALOG

# Allowed purpose values come from app/language/purposes.json (덕민님's classification plan).
Purpose = Literal[CATALOG.ids]  # type: ignore[valid-type]

# How an answer was produced, so Spring can mark the event for user review.
#   NO_SPEECH               nothing was said (empty transcript)
#   SUMMARY_FROM_TRANSCRIPT the LLM summary had no word the visitor said; the transcript is used
#   RULES_FALLBACK          the LLM failed or is not loaded; keyword rules decided
Flag = Literal["NO_SPEECH", "SUMMARY_FROM_TRANSCRIPT", "RULES_FALLBACK"]


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
    flags: list[Flag] = Field(default_factory=list)

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
    flags: list[Flag] = Field(default_factory=list)
