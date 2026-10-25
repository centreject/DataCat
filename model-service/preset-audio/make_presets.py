"""Preset audio for the doorbell (Pi sounds/): Supertonic 2 (OpenRAIL-M), 16 kHz mono 16-bit WAV.

Usage: python -I make_presets.py MODEL_DIR OUT_DIR VOICE... (e.g. F1 M2); helper.py from the official
example (MIT) goes in ./code/ next to this file — see README.md.
Deterministic: fixed noise seed per clip, so the same text + voice gives the same file.
"""

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).with_name("code")))
from helper import load_text_to_speech, load_voice_style  # noqa: E402

TEXTS = {
    "greeting": "마이크에 말씀해 주세요.",
    "greeting_notice": "안녕하세요. 용건을 말씀해 주시면 집주인에게 전달됩니다.",
    "completion": "접수되었습니다.",
    "completion_thanks": "전달했습니다. 감사합니다.",
    "fallback": "일시적인 오류로 접수할 수 없습니다. 잠시 후 다시 시도해 주세요.",
}
RATE = 16000


def resample(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    """FFT resampling (band-limited), fine for short clips."""
    n = int(round(len(x) * dst / src))
    spec = np.fft.rfft(x)
    keep = n // 2 + 1
    spec = spec[:keep] if len(spec) >= keep else np.pad(spec, (0, keep - len(spec)))
    return np.fft.irfft(spec, n) * (n / len(x))


def to_wav(path: Path, x: np.ndarray) -> None:
    x = np.concatenate([np.zeros(int(0.1 * RATE)), x, np.zeros(int(0.2 * RATE))])  # breathing room
    x = x / max(1e-6, np.abs(x).max()) * 0.89  # peak about -1 dBFS
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    model, out, voices = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    out.mkdir(parents=True, exist_ok=True)
    tts = load_text_to_speech(str(model / "onnx"))
    for voice in voices:
        style = load_voice_style([str(model / "voice_styles" / f"{voice}.json")])
        for i, (name, text) in enumerate(TEXTS.items()):
            np.random.seed(1000 + i)
            wav, dur = tts(text, "ko", style, total_step=16, speed=1.0)
            x = wav[0, : int(tts.sample_rate * float(dur[0]))].astype(np.float64)
            to_wav(out / f"{voice}_{name}.wav", resample(x, tts.sample_rate, RATE))
            print(f"{voice}_{name}.wav {len(x) / tts.sample_rate:.2f}s  {text}")


if __name__ == "__main__":
    main()
