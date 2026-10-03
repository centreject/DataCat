"""Purpose accuracy, emergency/threat recall, delivery subtype accuracy and summary checks
on eval/purpose_cases.jsonl (labels follow app/language/purposes.json).

Usage (from model-service/):
  python -m eval.eval_language --rules-only     # keyword fallback only, no GPU
  python -m eval.eval_language                  # real LLM (MODEL_PROFILE picks lite/full)
  python -m eval.eval_language --audio tts_snr10   # end to end: data/audio/<folder>/<id>.wav → STT → LLM
"""

import argparse
import json
import time
from pathlib import Path

from app.config import Settings
from app.language.normalize import PURPOSES
from app.language.rules import rule_analyze
from eval.metrics import TARGETS, group_recall, per_class_scores, subtype_accuracy, verdict

CRITICAL = {"PUBLIC_EMERGENCY", "SAFETY_REVIEW"}

CASES = Path(__file__).resolve().parent / "purpose_cases.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-only", action="store_true")
    parser.add_argument("--audio", help="transcribe data/audio/<folder>/<id>.wav first (end-to-end)")
    args = parser.parse_args()

    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    if args.audio:
        from app.config import DATA_DIR
        from app.media import decode_wav
        from app.speech.whisper import WhisperSpeech

        stt = WhisperSpeech(Settings())
        folder = DATA_DIR / "audio" / args.audio
        for c in cases:
            c["transcript"] = stt.transcribe(decode_wav((folder / f"{c['id']}.wav").read_bytes()))
    ungrounded: list[str] = []
    elapsed_ms: list[float] = []
    if args.rules_only:
        name, fallbacks = "rules", 0
        results = [rule_analyze(c["transcript"]) for c in cases]
    else:
        from app.language.qwen import QwenLanguage

        settings = Settings()
        qwen = QwenLanguage(settings)
        name, fallbacks, results = f"{settings.llm_model} ({settings.model_profile})", 0, []
        for c in cases:
            # The production path; flags say whether rules or the transcript stood in.
            start = time.perf_counter()
            result = qwen.analyze(c["transcript"])
            elapsed_ms.append((time.perf_counter() - start) * 1000)
            fallbacks += "RULES_FALLBACK" in result.flags
            if "SUMMARY_FROM_TRANSCRIPT" in result.flags:
                ungrounded.append(f"{c['id']}: \"{c['transcript']}\"")
            results.append(result)

    gold = [c["purpose"] for c in cases]
    pred = [r.purpose for r in results]
    accuracy = sum(g == p for g, p in zip(gold, pred)) / len(cases)
    over_20 = sum(len(r.summary) > 20 for r in results) / len(cases)
    critical = group_recall(gold, pred, CRITICAL)
    subtypes = subtype_accuracy([(c["purpose"], c.get("subtype")) for c in cases], [(r.purpose, r.subtype) for r in results])

    source = f"음성 {args.audio} → STT → " if args.audio else ""
    print(f"## 용건 분류 — {source}{name}, {len(cases)}건\n")
    print("| 용건 | 정밀도 | 재현율 |\n|---|---:|---:|")
    for label, (p, r) in per_class_scores(gold, pred, list(PURPOSES)).items():
        print(f"| {label} | {p:.0%} | {r:.0%} |")
    print("\n오답:")
    for c, r in zip(cases, results):
        if (c["purpose"], c.get("subtype")) != (r.purpose, r.subtype):
            gold_label = c["purpose"] + (f"/{c['subtype']}" if c.get("subtype") else "")
            pred_label = r.purpose + (f"/{r.subtype}" if r.subtype else "")
            print(f"- {c['id']}: 정답 {gold_label}, 예측 {pred_label} — \"{c['transcript']}\" → \"{r.summary}\"")
    print(f"\n정확도 {accuracy:.0%} (목표 ≥ {TARGETS['purpose_accuracy']:.0%}) → {verdict(accuracy >= TARGETS['purpose_accuracy'])}")
    print(f"긴급·위협 재현율 {critical:.0%} (목표 ≥ {TARGETS['critical_recall']:.0%}) → {verdict(critical >= TARGETS['critical_recall'])}")
    print(f"배송 세부 유형 정확도 {subtypes:.0%} (목표 ≥ {TARGETS['subtype_accuracy']:.0%}) → {verdict(subtypes >= TARGETS['subtype_accuracy'])}")
    print(f"요약 20자 초과 {over_20:.0%} (목표 0%) → {verdict(over_20 <= TARGETS['summary_over_20_max'])}")
    print(f"LLM 출력 파싱 실패로 규칙 사용: {fallbacks}건")
    if elapsed_ms:
        elapsed_ms.sort()
        print(f"LLM 처리 시간: 중앙값 {elapsed_ms[len(elapsed_ms) // 2]:.0f}ms, 최대 {elapsed_ms[-1]:.0f}ms")
    print(f"말하지 않은 내용이라 요약을 전사문으로 바꿈: {len(ungrounded)}건")
    for line in ungrounded:
        print(f"- {line}")


if __name__ == "__main__":
    main()
