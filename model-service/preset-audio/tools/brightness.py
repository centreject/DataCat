"""Rough "bright vs gloomy" cues per clip: sad speech is lower, flatter and slower.

Prints JSON {file: {f0_st, range_st, sec}}: mean pitch in semitones above 100 Hz, pitch spread (std, semitones),
duration. Usage: qenv/bin/python -I brightness.py DIR...
"""

import json
import sys
import wave
from pathlib import Path

import numpy as np
import pyworld as pw

out = {}
for folder in sys.argv[1:]:
    for f in sorted(Path(folder).rglob("*.wav")):
        with wave.open(str(f)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768
            sr = w.getframerate()
        f0, _ = pw.harvest(x, sr, frame_period=10.0)
        st = 12 * np.log2(f0[f0 > 0] / 100)
        out[f.parent.name + "/" + f.name] = {
            "f0_st": round(float(st.mean()), 2), "range_st": round(float(st.std()), 2), "sec": round(len(x) / sr, 2)
        }
print(json.dumps(out, ensure_ascii=False))
