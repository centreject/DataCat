"""UTMOS22 strong (MIT) naturalness score for every WAV under the given folders -> JSON on stdout."""
import json
import sys
import wave
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, "/home/drcloud/tts/speechmos/SpeechMOS-1.2.0")
from speechmos.utmos22.strong.model import UTMOS22Strong  # noqa: E402

model = UTMOS22Strong()
model.load_state_dict(torch.load("/home/drcloud/tts/speechmos/utmos22_strong_step7459_v1.pt", map_location="cpu", weights_only=True))
model.eval().cuda()


def read(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
        return x, w.getframerate()


scores = {}
with torch.inference_mode():
    for folder in sys.argv[1:]:
        for f in sorted(Path(folder).rglob("*.wav")):
            x, sr = read(f)
            scores[str(f)] = round(float(model(torch.from_numpy(x)[None].cuda(), sr)), 3)
print(json.dumps(scores, ensure_ascii=False))
