"""Synthesize the purpose cases into 16 kHz mono PCM16 WAVs for STT tests/eval.

Usage (from model-service/):  python -m eval.make_tts_audio
Output (git-ignored):
  data/audio/tts/<id>.wav + <id>.txt          clean speech
  data/audio/tts_snr20/<id>.wav + <id>.txt    + white noise at 20 dB SNR
  data/audio/tts_snr10/<id>.wav + <id>.txt    + white noise at 10 dB SNR
Voices alternate between a male and a female Korean voice.
Real INMP441 recordings go in data/audio/real/ with the same <id>.wav + <id>.txt layout.
"""

import asyncio
import io
import json
import wave
from pathlib import Path

import edge_tts
import numpy as np
from faster_whisper.audio import decode_audio

from app.config import DATA_DIR

CASES = Path(__file__).resolve().parent / "purpose_cases.jsonl"
VOICES = ("ko-KR-InJoonNeural", "ko-KR-SunHiNeural")
NOISE_SNR_DB = (20, 10)


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm.tobytes())


def add_noise(samples: np.ndarray, snr_db: float, seed: int) -> np.ndarray:
    signal_power = float(np.mean(samples**2)) or 1e-9
    noise = np.random.default_rng(seed).normal(0.0, 1.0, samples.shape)
    noise *= np.sqrt(signal_power / (10 ** (snr_db / 10)))
    return samples + noise.astype(np.float32)


async def synthesize(text: str, voice: str) -> np.ndarray:
    chunks = [c["data"] async for c in edge_tts.Communicate(text, voice).stream() if c["type"] == "audio"]
    return decode_audio(io.BytesIO(b"".join(chunks)), sampling_rate=16000)


async def main() -> None:
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    for i, case in enumerate(cases):
        speech = await synthesize(case["transcript"], VOICES[i % len(VOICES)])
        variants = {"tts": speech} | {f"tts_snr{snr}": add_noise(speech, snr, seed=i) for snr in NOISE_SNR_DB}
        for folder, samples in variants.items():
            out = DATA_DIR / "audio" / folder
            write_wav(out / f"{case['id']}.wav", samples)
            (out / f"{case['id']}.txt").write_text(case["transcript"])
    print(f"{len(cases)} cases × {1 + len(NOISE_SNR_DB)} variants → {DATA_DIR / 'audio'}")


if __name__ == "__main__":
    asyncio.run(main())
