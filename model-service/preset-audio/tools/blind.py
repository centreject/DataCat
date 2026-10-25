"""Blind listening set: per prompt, Supertonic F1 / M2 and the best Qwen3-TTS take, all 16 kHz, shuffled as A/B/C."""
import json
import random
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/drcloud/tts")
from make_presets import to_wav, resample  # same 16 kHz, padding, loudness as the shipped files  # noqa: E402

u = {Path(f).parent.name + "/" + Path(f).name: v for f, v in json.load(open("/home/drcloud/tts/utmos.json")).items()}
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
random.seed(24)
key = {}
for name in ("greeting", "greeting_notice", "completion", "completion_thanks", "fallback"):
    qwen = max((k for k in u if k.startswith(f"qwen/{name}__")), key=u.get)
    cands = {"Supertonic F1": f"supertonic/F1_{name}.wav", "Supertonic M2": f"supertonic/M2_{name}.wav", f"Qwen3 Sohee ({Path(qwen).stem.split('__')[1]})": qwen}
    items = list(cands.items()); random.shuffle(items)
    for letter, (label, rel) in zip("ABC", items):
        with wave.open(f"/home/drcloud/tts/out/{rel}") as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768; sr = w.getframerate()
        x = resample(x, sr, 16000) if sr != 16000 else x
        if label.startswith("Qwen"):
            to_wav(out / f"{name}_{letter}.wav", x)
        else:  # already padded/normalised
            to_wav(out / f"{name}_{letter}.wav", x[int(0.1 * 16000): len(x) - int(0.2 * 16000)])
        key[f"{name}_{letter}"] = {"model": label, "utmos": u[rel]}
json.dump(key, open(out.parent / "blind_key.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(key, ensure_ascii=False, indent=1))
