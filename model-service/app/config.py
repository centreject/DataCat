from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

# model-service/ — anchors data paths so they don't depend on the working directory.
SERVICE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SERVICE_ROOT / "data"


class Settings(BaseSettings):
    # mock: canned answers without GPU or weights, for teammates' integration tests (app/mock.py).
    model_profile: Literal["full", "lite", "mock"] = "lite"
    mock_delay_ms: int = 0
    person_conf: float = 0.4
    # Packages = fine-tuned YOLOE (box, envelope, plastic bag; finetune/) + zero-shot YOLOE on the
    # prompts below for items the fine-tuned model was never shown. 2026-10-17, eval/README F1:
    # box 78→98%, plastic bag 80→100%, empty-hallway false positives 10→3%, +15 ms per image.
    # The zero-shot model alone used to have 14 prompts (box, bag, envelope, flyer, … at conf 0.25).
    package_conf: float = 0.25
    package_prompts: list[str] = [
        "food delivery bag",
        "takeout container",
        "cooler bag",
        "flower bouquet",
        "cake box",
    ]
    package_ft_conf: float = 0.4
    weights_dir: str = str(DATA_DIR / "weights")
    stt_model: str = "large-v3-turbo"
    llm_model: str = "Qwen/Qwen3-4B-Instruct-2507"
    llm_max_new_tokens: int = 64

    model_config = {"protected_namespaces": ()}

    @property
    def stt_compute_type(self) -> str:
        return "float16" if self.model_profile == "full" else "int8_float16"

    @property
    def llm_quantize_4bit(self) -> bool:
        return self.model_profile == "lite"
