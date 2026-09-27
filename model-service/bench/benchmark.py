"""VRAM and latency benchmark for one profile on this machine.

Usage (from model-service/):  python -m bench.benchmark --profile lite --runs 20
Prints a markdown table and writes bench/results/<GPU>_<profile>.json.
Inputs: first image in data/images/person/ and data/audio/tts/delivery_01.wav when present
(run eval/prepare_images.py and eval.make_tts_audio first), otherwise synthetic ones.
"""

import argparse
import json
import math
import re
import subprocess
import time
from pathlib import Path

from app.config import DATA_DIR, Settings

RESULTS = Path(__file__).resolve().parent / "results"
# Plan "Global Constraints": p95 limits in ms per profile.
TARGETS_MS = {"lite": {"audio_process": 4000}, "full": {"audio_process": 2000, "vision": 300}}


def percentile(samples: list[float], pct: float) -> float:
    """Nearest-rank percentile."""
    ordered = sorted(samples)
    return ordered[max(math.ceil(pct / 100 * len(ordered)) - 1, 0)]


def judge(profile: str, stats: dict[str, dict[str, float]]) -> dict[str, bool]:
    return {name: stats[name]["p95"] <= limit for name, limit in TARGETS_MS[profile].items()}


def gpu_used_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    )
    return int(out.stdout.split()[0])


def timed(fn, inputs: list, runs: int) -> dict[str, float]:
    """Time fn over `runs` calls cycling through `inputs`. The first (cold) call is reported
    separately as "first": it is what the first visitor after a restart waits for."""
    start = time.perf_counter()
    fn(inputs[0])
    first = (time.perf_counter() - start) * 1000
    samples = []
    for i in range(runs):
        start = time.perf_counter()
        fn(inputs[i % len(inputs)])
        samples.append((time.perf_counter() - start) * 1000)
    return {
        "first": round(first, 1),
        "p50": round(percentile(samples, 50), 1),
        "p95": round(percentile(samples, 95), 1),
    }


def inputs() -> tuple[list[bytes], list[bytes]]:
    """All person images and all clean TTS utterances (varied lengths), or synthetic fallbacks."""
    from tests.fixtures.make_fixtures import noisy_jpeg, tone_wav

    images = [p.read_bytes() for p in sorted((DATA_DIR / "images" / "person").glob("*.jpg"))]
    wavs = [p.read_bytes() for p in sorted((DATA_DIR / "audio" / "tts").glob("*.wav"))]
    return images or [noisy_jpeg(1280, 720)], wavs or [tone_wav(5)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["lite", "full"], default="lite")
    parser.add_argument("--runs", type=int, default=20)
    args = parser.parse_args()

    import torch

    from app.language.qwen import QwenLanguage
    from app.media import decode_jpeg, decode_wav
    from app.pipeline import process_audio
    from app.registry import ModelRegistry
    from app.speech.whisper import WhisperSpeech
    from app.vision.yolo import YoloVision

    settings = Settings(model_profile=args.profile)
    gpu = torch.cuda.get_device_name(0)
    total_mib = torch.cuda.get_device_properties(0).total_memory // 2**20
    baseline_mib = gpu_used_mib()

    loads = {}
    models = {}
    for name, cls in (("vision", YoloVision), ("stt", WhisperSpeech), ("language", QwenLanguage)):
        before = gpu_used_mib()
        start = time.perf_counter()
        models[name] = cls(settings)
        loads[name] = {
            "load_s": round(time.perf_counter() - start, 1),
            "nvidia_smi_delta_mib": gpu_used_mib() - before,
        }
    registry = ModelRegistry(ready=True, **models)
    jpegs, wavs = inputs()
    # Real transcripts for the language step: the eval sentences, in the same order as the audio.
    cases = Path(__file__).resolve().parent.parent / "eval" / "purpose_cases.jsonl"
    transcripts = [json.loads(line)["transcript"] for line in cases.read_text().splitlines() if line.strip()]

    stats = {
        "vision": timed(lambda jpeg: registry.vision.detect(decode_jpeg(jpeg)), jpegs, args.runs),
        "stt": timed(lambda wav: registry.stt.transcribe(decode_wav(wav)), wavs, args.runs),
        "language": timed(registry.language.analyze, transcripts, args.runs),
        "audio_process": timed(lambda wav: process_audio(registry, wav), wavs, args.runs),
    }
    verdicts = judge(args.profile, stats)
    result = {
        "gpu": gpu,
        "total_mib": total_mib,
        "profile": args.profile,
        "runs": args.runs,
        "models": {"stt": settings.stt_model, "stt_compute": settings.stt_compute_type,
                   "llm": settings.llm_model, "llm_4bit": settings.llm_quantize_4bit},
        "desktop_baseline_mib": baseline_mib,
        "all_loaded_mib": gpu_used_mib(),
        "torch_max_allocated_mib": torch.cuda.max_memory_allocated() // 2**20,
        "loads": loads,
        "latency_ms": stats,
        "pass": verdicts,
    }

    print(f"## {gpu} ({total_mib} MiB) · profile {args.profile} · {args.runs} runs\n")
    print("| 모델 | 로딩(초) | VRAM 증가(MiB) |\n|---|---:|---:|")
    for name, load in loads.items():
        print(f"| {name} | {load['load_s']} | {load['nvidia_smi_delta_mib']} |")
    print(f"\n전체 사용 {result['all_loaded_mib']} MiB (시작 전 {baseline_mib} MiB 포함) / {total_mib} MiB\n")
    print(f"입력: 이미지 {len(jpegs)}장, 음성 {len(wavs)}개, 문장 {len(transcripts)}개를 돌아가며 사용\n")
    print("| 단계 | 첫 요청 (ms) | p50 (ms) | p95 (ms) | 목표 (p95) |\n|---|---:|---:|---:|---|")
    for name, s in stats.items():
        limit = TARGETS_MS[args.profile].get(name)
        target = f"≤ {limit} {'PASS' if verdicts[name] else 'FAIL'}" if limit else "—"
        print(f"| {name} | {s['first']} | {s['p50']} | {s['p95']} | {target} |")

    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{re.sub(r'[^A-Za-z0-9]+', '-', gpu).strip('-')}_{args.profile}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n→ {out.relative_to(RESULTS.parent.parent)}")


if __name__ == "__main__":
    main()
