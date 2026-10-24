"""Intonation tuning with WORLD (pyworld, MIT): edit the pitch curve of a finished clip, keep timbre.

Variants per input clip:
  resynth  analysis + resynthesis only (isolates WORLD's own quality loss)
  fall     pitch eases down ~1.5 semitones over the last 30% of voiced speech (spoken Korean statements fall at the end)
  range    pitch movement around the speaker's mean widened 20% (less monotone)
  both     fall + range
  slow_end last 25% of the clip 8% slower (people stretch the final syllable)
Usage: qenv/bin/python -I tune_prosody.py OUT_DIR IN.wav...
"""

import sys
import wave
from pathlib import Path

import numpy as np
import pyworld as pw


def read(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768, w.getframerate()


def write(path, x, sr):
    x = x / max(1e-6, np.abs(x).max()) * 0.89
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def fall(f0, semitones=1.5, part=0.3):
    voiced = np.flatnonzero(f0 > 0)
    if len(voiced) < 10:
        return f0
    start = voiced[int(len(voiced) * (1 - part))]
    ramp = np.zeros_like(f0)
    ramp[start:] = np.linspace(0, -semitones, len(f0) - start)
    return np.where(f0 > 0, f0 * 2 ** (ramp / 12), 0)


def widen(f0, k=1.2):
    v = f0 > 0
    if v.sum() < 10:
        return f0
    log = np.log(f0[v])
    out = f0.copy()
    out[v] = np.exp(log.mean() + (log - log.mean()) * k)
    return out


def slow_end(f0, sp, ap, part=0.25, rate=0.92):
    n = len(f0)
    cut = int(n * (1 - part))
    tail = np.arange(cut, n, rate)  # resample frame index at 92% speed → ~8% longer
    idx = np.concatenate([np.arange(cut), tail]).astype(int).clip(0, n - 1)
    return f0[idx], sp[idx], ap[idx]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for src in map(Path, sys.argv[2:]):
        x, sr = read(src)
        f0, t = pw.harvest(x, sr, frame_period=5.0)
        sp, ap = pw.cheaptrick(x, f0, t, sr), pw.d4c(x, f0, t, sr)
        variants = {
            "resynth": (f0, sp, ap),
            "fall": (fall(f0), sp, ap),
            "range": (widen(f0), sp, ap),
            "both": (fall(widen(f0)), sp, ap),
            "slow_end": slow_end(fall(f0), sp, ap),
        }
        for name, (f, s, a) in variants.items():
            y = pw.synthesize(np.ascontiguousarray(f), np.ascontiguousarray(s), np.ascontiguousarray(a), sr, 5.0)
            write(out / f"{src.parent.name}__{src.stem}__{name}.wav", y, sr)
        print(src.name, "done", flush=True)


if __name__ == "__main__":
    main()
