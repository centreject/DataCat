"""Q1: does a quiet microphone break speech recognition, and does peak normalization before Whisper help?

The 11/10 real-device test lost one visit because the USB mic sat at 50% input and the speaker was far
away: the whole recording came back empty. This reproduces that with the clean TTS test speech:
scale it down (gain), optionally add a fixed microphone noise floor (so a quieter voice also means a
worse signal-to-noise ratio, as on a real mic), round to 16-bit like the Pi upload, then transcribe
as recorded (the service's boost switched off) and with app.media.boost_quiet, as the service now does.

Run (GPU, ~5 min): python -m eval.eval_low_volume [N_FILES]
"""

import sys

import numpy as np

from app.config import DATA_DIR, Settings
from app.media import boost_quiet, decode_wav
from eval.metrics import cer

GAINS = (1.0, 0.25, 0.1, 0.03, 0.01)  # 0 / -12 / -20 / -30 / -40 dB
NOISE_RMS = 10 ** (-60 / 20)  # fixed mic self-noise, -60 dBFS


def to_int16(audio: np.ndarray) -> np.ndarray:
    """What the Pi actually uploads: 16-bit PCM."""
    return np.round(np.clip(audio, -1, 1) * 32767).astype(np.int16).astype(np.float32) / 32768.0


def main() -> None:
    import app.speech.whisper as whisper_module
    from app.speech.whisper import WhisperSpeech

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    wavs = sorted((DATA_DIR / "audio" / "tts").glob("*.wav"))[:n]
    clips = [(decode_wav(w.read_bytes()), w.with_suffix(".txt").read_text(encoding="utf-8").strip()) for w in wavs]
    stt = WhisperSpeech(Settings())
    rng = np.random.default_rng(0)

    print(f"{len(clips)} clips · noise floor {20 * np.log10(NOISE_RMS):.0f} dBFS")
    print("| 조건 | 음량 | 그대로 CER | 빈 결과 | 음량 올림 CER | 빈 결과 |")
    print("|---|---:|---:|---:|---:|---:|")
    for noisy in (False, True):
        for gain in GAINS:
            row = {False: [], True: []}
            for audio, ref in clips:
                x = audio * gain
                if noisy:
                    x = x + rng.normal(0, NOISE_RMS, x.shape).astype(np.float32)
                x = to_int16(x)
                for norm in (False, True):
                    whisper_module.boost_quiet = boost_quiet if norm else (lambda a: a)
                    hyp = stt.transcribe(x)
                    row[norm].append((cer(ref, hyp), hyp == ""))
            cells = []
            for norm in (False, True):
                scores = row[norm]
                cells += [f"{100 * np.mean([c for c, _ in scores]):.1f}%", str(sum(e for _, e in scores))]
            cond = "+ 잡음 바닥" if noisy else "음량만"
            print(f"| {cond} | {20 * np.log10(gain):.0f} dB | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    main()
