"""Purpose accuracy and summary length on eval/purpose_cases.jsonl.

Usage (from model-service/):
  python -m eval.eval_language --rules-only     # keyword fallback only, no GPU
  python -m eval.eval_language                  # real LLM (MODEL_PROFILE picks lite/full)
"""

import argparse
import json
from pathlib import Path

from app.config import Settings
from app.language.normalize import PURPOSES, parse_llm_output
from app.language.rules import rule_analyze
from eval.metrics import TARGETS, per_class_scores, verdict

CASES = Path(__file__).resolve().parent / "purpose_cases.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-only", action="store_true")
    args = parser.parse_args()

    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    if args.rules_only:
        name, fallbacks = "rules", 0
        results = [rule_analyze(c["transcript"]) for c in cases]
    else:
        from app.language.qwen import QwenLanguage, build_messages

        settings = Settings()
        qwen = QwenLanguage(settings)
        name, fallbacks, results = f"{settings.llm_model} ({settings.model_profile})", 0, []
        for c in cases:
            parsed = parse_llm_output(qwen.generate(build_messages(c["transcript"])))
            fallbacks += parsed is None
            results.append(parsed or rule_analyze(c["transcript"]))

    gold = [c["purpose"] for c in cases]
    pred = [r.purpose for r in results]
    accuracy = sum(g == p for g, p in zip(gold, pred)) / len(cases)
    over_20 = sum(len(r.summary) > 20 for r in results) / len(cases)

    print(f"## 용건 분류 — {name}, {len(cases)}건\n")
    print("| 용건 | 정밀도 | 재현율 |\n|---|---:|---:|")
    for label, (p, r) in per_class_scores(gold, pred, list(PURPOSES)).items():
        print(f"| {label} | {p:.0%} | {r:.0%} |")
    print("\n오답:")
    for c, r in zip(cases, results):
        if c["purpose"] != r.purpose:
            print(f"- {c['id']}: 정답 {c['purpose']}, 예측 {r.purpose} — \"{c['transcript']}\" → \"{r.summary}\"")
    print(f"\n정확도 {accuracy:.0%} (목표 ≥ {TARGETS['purpose_accuracy']:.0%}) → {verdict(accuracy >= TARGETS['purpose_accuracy'])}")
    print(f"요약 20자 초과 {over_20:.0%} (목표 0%) → {verdict(over_20 <= TARGETS['summary_over_20_max'])}")
    print(f"LLM 출력 파싱 실패로 규칙 사용: {fallbacks}건")


if __name__ == "__main__":
    main()
