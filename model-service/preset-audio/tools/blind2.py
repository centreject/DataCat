"""Second blind set: per prompt the 3 brightest correct Sohee takes as X/Y/Z (16 kHz, same loudness)."""
import json, random, sys, wave
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/drcloud/tts")
from make_presets import to_wav, resample
picks = json.load(open("/home/drcloud/tts/bright_picks.json"))
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
random.seed(1024); key = {}
for name, files in picks.items():
    files = files[:]; random.shuffle(files)
    for letter, rel in zip("XYZ", files):
        with wave.open(f"/home/drcloud/tts/out/{rel}") as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768; sr = w.getframerate()
        to_wav(out / f"{name}_{letter}.wav", resample(x, sr, 16000))
        key[f"{name}_{letter}"] = rel
json.dump(key, open(out.parent / "blind2_key.json", "w"), ensure_ascii=False, indent=1)
print(len(key))
