from typing import Literal

from pydantic import BaseModel

Purpose = Literal["DELIVERY", "INSPECTION", "VISIT", "ETC"]


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


class AudioProcessResponse(BaseModel):
    transcript: str
    purpose: str
    summary: str
