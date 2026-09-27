from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_profile: Literal["full", "lite"] = "lite"
    person_conf: float = 0.4
    package_conf: float = 0.3
    package_prompts: list[str] = []
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
