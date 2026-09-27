import json
import threading
from pathlib import Path

from app.config import Settings
from app.hub_cache import load_cached_first
from app.language.normalize import parse_llm_output
from app.language.rules import rule_analyze
from app.schemas import Analysis

SYSTEM_PROMPT = """너는 무인 현관 초인종의 접수 도우미다. 방문객이 말한 내용을 보고 JSON 한 줄만 출력한다.
형식: {"summary": "...", "purpose": "..."}

purpose는 아래 4개 중 하나:
- DELIVERY: 택배, 음식 배달, 물건 배송. 물건을 문 앞·경비실·관리실에 두거나 맡겼다는 말도 포함
- INSPECTION: 검침, 시설 점검, 관리사무소·관리실 업무, 수리·설치·소독 기사의 방문(예약 방문 포함)
- VISIT: 집에 사는 사람과 개인적으로 아는 사이(가족, 친구, 지인, 이웃)의 방문
- ETC: 위에 해당하지 않거나 용건을 알 수 없음. 모르는 사람의 영업·홍보·보험·종교·설문, 길이나 호수 묻기, 전단지 부착은 모두 ETC

"방문", "왔다"라는 말만으로 VISIT으로 판단하지 않는다. 방문객과 집주인이 아는 사이일 때만 VISIT이다.

summary 규칙:
- 공백 포함 20자 이내
- 명사형으로 끝낸다 (예: "택배 문 앞 보관", "가스 검침 방문")
- 방문객이 말하지 않은 내용은 만들지 않는다

"택배 아니고"처럼 부정한 내용은 용건으로 보지 않는다. JSON 외의 설명은 쓰지 않는다."""

FEW_SHOTS = (
    ("택배 왔습니다. 문 앞에 두고 갈게요.", {"summary": "택배 문 앞 보관", "purpose": "DELIVERY"}),
    ("안녕하세요, 가스 검침하러 왔습니다.", {"summary": "가스 검침 방문", "purpose": "INSPECTION"}),
    ("엄마, 나야. 반찬 가져왔어.", {"summary": "가족 반찬 전달 방문", "purpose": "VISIT"}),
    ("혹시 이 근처에 약국 있나요?", {"summary": "약국 위치 문의", "purpose": "ETC"}),
)


def build_messages(transcript: str) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for utterance, answer in FEW_SHOTS:
        messages.append({"role": "user", "content": utterance})
        messages.append({"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)})
    messages.append({"role": "user", "content": transcript})
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
        self.analyze("택배 왔습니다")  # warm-up

    def generate(self, messages: list[dict]) -> str:
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with self.lock, self.torch.inference_mode():
            output = self.model.generate(
                **inputs, max_new_tokens=self.max_new_tokens, do_sample=False
            )
        return self.tokenizer.decode(output[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)

    def analyze(self, transcript: str) -> Analysis:
        return parse_llm_output(self.generate(build_messages(transcript))) or rule_analyze(transcript)
