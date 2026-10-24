"""Qwen3-TTS CustomVoice (Sohee, Korean) takes for the doorbell prompts, several styles x seeds.

Usage: qenv/bin/python -I gen_qwen.py OUT_DIR
"""

import sys
import wave
from pathlib import Path

import numpy as np
import torch
from qwen_tts import Qwen3TTSModel

# Same words as the server presets; commas only mark where a person would breathe.
TEXTS = {
    "greeting": "마이크에 말씀해 주세요.",
    "greeting_notice": "안녕하세요. 용건을 말씀해 주시면, 집주인에게 전달됩니다.",
    "completion": "접수되었습니다.",
    "completion_thanks": "전달했습니다. 감사합니다.",
    "fallback": "일시적인 오류로, 접수할 수 없습니다. 잠시 후 다시 시도해 주세요.",
}
STYLES_OLD = {
    "plain": None,
    "en": "Speak like a kind receptionist talking to a visitor at the door: warm, calm and natural, "
          "not robotic. Gentle falling intonation at the end of each sentence.",
    "ko": "친절한 안내원이 문 앞 방문객에게 실제로 말하듯이, 따뜻하고 자연스러운 말투로. "
          "기계처럼 딱딱하지 않게, 문장 끝은 부드럽게 내려서.",
}
SEEDS = (1, 2, 3)


def save(path: Path, x: np.ndarray, sr: int) -> None:
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    x = x / max(1e-6, np.abs(x).max()) * 0.89
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    model = Qwen3TTSModel.from_pretrained(
        "/home/drcloud/tts/qwen3-customvoice", device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa"
    )
    print("speakers:", model.get_supported_speakers())
    for name, text in TEXTS.items():
        for style, instruct in STYLES.items():
            for seed in SEEDS:
                if (out / f"{name}__{style}__s{seed}.wav").exists():
                    continue  # resume: keep takes already made
                torch.manual_seed(seed)
                wavs, sr = model.generate_custom_voice(text=text, speaker="Sohee", language="Korean", instruct=instruct)
                save(out / f"{name}__{style}__s{seed}.wav", wavs[0], sr)
                print(f"{name} {style} s{seed} {len(wavs[0]) / sr:.2f}s", flush=True)




# 2026-10-22 listening: Sohee sounded the most human but a little sad/gloomy → brighter instructions.
STYLES_UNUSED = {
    "bright": "Speak in a bright, cheerful and friendly tone with a smile, like a welcoming receptionist. "
              "Natural and upbeat, not sad, not robotic.",
    "ko_bright": "밝고 상냥한 목소리로, 미소 지으며 반갑게 안내하듯이. 우울하거나 처지지 않게, 말끝은 가볍게.",
    "lively": "Lively and warm, slightly higher pitch, light and positive delivery, like greeting a neighbour.",
}
SEEDS = (1, 2, 3, 4)


# 2026-10-22: completion was the weakest prompt; lively style (liked for greeting/fallback), more seeds.
TEXTS = {"completion": "접수되었습니다."}
STYLES = {
    "calm_en": "Bright but calm and gentle, like a kind receptionist. Say it smoothly in one breath, no stress or emphasis on individual syllables, clear pronunciation.",
    "calm_ko": "밝지만 차분하게, 음절마다 힘주지 말고 부드럽게 한 호흡으로 이어서, 또박또박 분명한 발음으로.",
}
SEEDS = tuple(range(1, 9))

if __name__ == "__main__":
    main()
