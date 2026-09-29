import copy
import json
import threading
from pathlib import Path

from app.config import Settings
from app.hub_cache import load_cached_first
from app.language.normalize import is_grounded, parse_llm_output, truncate_summary
from app.language.purposes import CATALOG
from app.language.rules import rule_analyze
from app.schemas import Analysis

def _system_prompt() -> str:
    purposes = "\n".join(f"- {p['id']}: {p['name']}. {p['description']}" for p in CATALOG.purposes)
    subtypes = "\n".join(f"- {s['id']}: {s['name']}" for s in CATALOG.get("DELIVERY").get("subtypes", []))
    rules = "\n".join(f"- {r}" for r in CATALOG.rules)
    return f"""너는 무인 현관 초인종의 접수 도우미다. 방문객이 말한 내용을 보고 JSON 한 줄만 출력한다.
형식: {{"summary": "...", "purpose": "...", "subtype": "..." 또는 null}}

purpose는 아래 중 하나 (위에 있을수록 우선):
{purposes}

DELIVERY의 subtype은 아래 중 하나:
{subtypes}

판단 규칙:
{rules}

summary 규칙:
- 공백 포함 20자 이내
- 명사형으로 끝낸다 (예: "택배 문 앞 보관", "가스 검침 방문")
- 방문객이 말하지 않은 내용은 만들지 않는다

JSON 외의 설명은 쓰지 않는다."""


# Built from purposes.json, so the classification plan can change without touching this code.
SYSTEM_PROMPT = _system_prompt()
FEW_SHOTS = tuple(
    (s["transcript"], {"summary": s["summary"], "purpose": s["purpose"], "subtype": s["subtype"]})
    for s in CATALOG.few_shots
)


# The first part of an utterance carries the purpose; longer input only slows the LLM down and
# made it lose track (a 1018-char delivery transcript came back as "약국 위치 문의").
MAX_TRANSCRIPT_CHARS = 300


def build_messages(transcript: str) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for utterance, answer in FEW_SHOTS:
        messages.append({"role": "user", "content": utterance})
        messages.append({"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)})
    messages.append({"role": "user", "content": transcript[:MAX_TRANSCRIPT_CHARS]})
    return messages


class QwenLanguage:
    def __init__(self, settings: Settings):
        # Heavy imports stay here so unit tests and the app start without them.
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        cache = str(Path(settings.weights_dir) / "hf")
        kwargs = {"device_map": "cuda", "cache_dir": cache}
        if settings.llm_quantize_4bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16
            )
        else:
            kwargs["dtype"] = torch.bfloat16
        self.torch = torch
        self.tokenizer = load_cached_first(
            lambda local_files_only: AutoTokenizer.from_pretrained(
                settings.llm_model, cache_dir=cache, local_files_only=local_files_only
            )
        )
        self.model = load_cached_first(
            lambda local_files_only: AutoModelForCausalLM.from_pretrained(
                settings.llm_model, local_files_only=local_files_only, **kwargs
            )
        )
        self.max_new_tokens = settings.llm_max_new_tokens
        self.lock = threading.Lock()
        self._build_prefix_cache()
        self.analyze("택배 왔습니다")  # warm-up

    def _render(self, messages: list[dict]) -> str:
        return self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )

    def _build_prefix_cache(self) -> None:
        """Run the fixed part of the prompt (instructions + examples, ~1.5k tokens) once.

        Every request shares it, so each call then only processes the visitor's words. Without this
        the 9-purpose prompt took ~4.4 s per answer on the 3060 Ti (2026-09-29).
        """
        self._prefix_messages = build_messages("")[:-1]
        probe = self._render(self._prefix_messages + [{"role": "user", "content": "x"}])
        prefix_text = probe[: probe.rindex("<|im_start|>user")]
        self._prefix_ids = self.tokenizer(prefix_text, return_tensors="pt").input_ids.to(self.model.device)
        with self.torch.inference_mode():
            self._prefix_cache = self.model(input_ids=self._prefix_ids, use_cache=True).past_key_values

    def generate(self, messages: list[dict], use_prefix_cache: bool = True) -> str:
        inputs = self.tokenizer(self._render(messages), return_tensors="pt").to(self.model.device)
        ids = inputs["input_ids"]
        n = self._prefix_ids.shape[1]
        cached = (
            use_prefix_cache
            and messages[:-1] == self._prefix_messages
            and ids.shape[1] > n
            and self.torch.equal(ids[:, :n], self._prefix_ids)
        )
        with self.lock, self.torch.inference_mode():
            output = self.model.generate(
                **inputs,
                past_key_values=copy.deepcopy(self._prefix_cache) if cached else None,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )
        return self.tokenizer.decode(output[0][ids.shape[1] :], skip_special_tokens=True)

    def analyze(self, transcript: str) -> Analysis:
        parsed = parse_llm_output(self.generate(build_messages(transcript)))
        if parsed is None:
            return rule_analyze(transcript)
        if not is_grounded(parsed.summary, transcript):
            # Keep the LLM's purpose (98% vs 88% for rules) but never show an invented summary.
            return Analysis(summary=truncate_summary(transcript), purpose=parsed.purpose, subtype=parsed.subtype)
        return parsed
