"""Chosen takes (민중 listening 2026-10-22) → Pi file names, 16 kHz mono 16-bit."""
import sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/drcloud/tts")
from make_presets import to_wav, resample
CHOSEN = {  # blind2 letter → source take
    "greeting.wav": "qwen_bright/greeting__lively__s2.wav",            # greeting_Y (1st)
    "greeting_alt.wav": "qwen_bright/greeting__lively__s1.wav",        # greeting_X (2nd)
    "completion.wav": "qwen_bright/completion__bright__s3.wav",        # completion_Z
    "fallback.wav": "qwen_bright/fallback__lively__s2.wav",            # fallback_X
}
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
for dst, src in CHOSEN.items():
    with wave.open(f"/home/drcloud/tts/out/{src}") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768; sr = w.getframerate()
    to_wav(out / dst, resample(x, sr, 16000))
    print(dst, "<-", src)
