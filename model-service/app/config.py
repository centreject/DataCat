from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings

# model-service/ — anchors data paths so they don't depend on the working directory.
SERVICE_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SERVICE_ROOT / "data"


class Settings(BaseSettings):
    model_profile: Literal["full", "lite"] = "lite"
    person_conf: float = 0.4
    # Tuned on the Open Images val/test subset from eval/prepare_images.py (2026-09-27),
    # measured per whole folder (prompts below): person 93%, box 83%, plastic bag 80%,
    # empty-hallway false positives 10%. Zero-shot; box/bag still just below the 85% target.
    package_conf: float = 0.25
    package_prompts: list[str] = [
        "box",
        "cardboard box",
        "package",
        "bag",
        "plastic bag",
        "shopping bag",
        "food delivery bag",
        "takeout container",
        "cooler bag",
        # 2026-10-04: items the classification plan lists for 물품만 있음 (box 53→83%, bag 72→80%,
        # empty-hallway false positives 3→10%).
        "flower bouquet",
        "cake box",
        "gift box",
        "envelope",
        "flyer",
    ]
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
