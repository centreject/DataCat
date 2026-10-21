from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings

# model-service/ — anchors data paths so they don't depend on the working directory.
SERVICE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SERVICE_ROOT / "data"


class Settings(BaseSettings):
    # mock: canned answers without GPU or weights, for teammates' integration tests (app/mock.py).
    model_profile: Literal["full", "lite", "mock"] = "lite"
    mock_delay_ms: int = Field(0, ge=0)
    person_conf: float = Field(0.4, ge=0, le=1)
    # Packages = fine-tuned YOLOE (box, envelope, plastic bag; finetune/) + zero-shot YOLOE on the
    # prompts below for items the fine-tuned model was never shown. 2026-10-17, eval/README F1:
    # box 78→98%, plastic bag 80→100%, empty-hallway false positives 10→3%, +15 ms per image.
    # The zero-shot model alone used to have 14 prompts (box, bag, envelope, flyer, … at conf 0.25).
    package_conf: float = Field(0.25, ge=0, le=1)
    package_prompts: list[str] = [
        "food delivery bag",
        "takeout container",
        "cooler bag",
        "flower bouquet",
        "cake box",
    ]
    package_ft_conf: float = Field(0.4, ge=0, le=1)
    # Used alone when the fine-tuned weights can't be fetched (offline first start, Release gone):
    # packages are still found, as before 2026-10-17 (box 83%, bag 80%, empty-hallway false alarms 10%).
    package_fallback_prompts: list[str] = [
        "box", "cardboard box", "package", "bag", "plastic bag", "shopping bag", "food delivery bag",
        "takeout container", "cooler bag", "flower bouquet", "cake box", "gift box", "envelope", "flyer",
    ]
    weights_dir: str = str(DATA_DIR / "weights")
    stt_model: str = "large-v3-turbo"
    # Hugging Face commits, so a new PC gets the same weights we measured (2026-10-22), not "latest".
    stt_revision: str = "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
    llm_model: str = "Qwen/Qwen3-4B-Instruct-2507"
    llm_revision: str = "cdbee75f17c01a7cc42f958dc650907174af0554"
    llm_max_new_tokens: int = Field(64, ge=1, le=256)
    # Longest wait for a model busy with another request before answering 503 MODEL_BUSY.
    # Below Spring's timeouts (photo 5 s, audio 10 s). A busy LLM falls back to keyword rules.
    vision_wait_s: float = Field(3.0, gt=0)
    stt_wait_s: float = Field(5.0, gt=0)
    llm_wait_s: float = Field(3.0, gt=0)
    stuck_after_s: float = Field(60.0, gt=0)  # /health turns degraded when one inference runs longer
    # Optional shared secret: when set, /internal/v1/* needs header X-Api-Key with this value.
    model_api_key: str = ""

    model_config = {"protected_namespaces": ()}

    @property
    def stt_compute_type(self) -> str:
        return "float16" if self.model_profile == "full" else "int8_float16"

    @property
    def llm_quantize_4bit(self) -> bool:
        return self.model_profile == "lite"
