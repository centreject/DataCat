"""Purpose accuracy, emergency/threat recall, delivery subtype accuracy and summary checks
on eval/purpose_cases.jsonl (labels follow app/language/purposes.json).

Usage (from model-service/):
  python -m eval.eval_language --rules-only     # keyword fallback only, no GPU
  python -m eval.eval_language                  # real LLM (MODEL_PROFILE picks lite/full)
"""

import argparse
import json
import time
from pathlib import Path

from app.config import Settings
from app.language.normalize import PURPOSES, is_grounded, parse_llm_output, truncate_summary
from app.language.rules import rule_analyze
from eval.metrics import TARGETS, group_recall, per_class_scores, subtype_accuracy, verdict

CRITICAL = {"PUBLIC_EMERGENCY", "SAFETY_REVIEW"}

CASES = Path(__file__).resolve().parent / "purpose_cases.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-only", action="store_true")
    args = parser.parse_args()

    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    ungrounded: list[str] = []
    elapsed_ms: list[float] = []
    if args.rules_only:
        name, fallbacks = "rules", 0
        results = [rule_analyze(c["transcript"]) for c in cases]
    else:
        from app.language.qwen import QwenLanguage, build_messages

        settings = Settings()
        qwen = QwenLanguage(settings)
        name, fallbacks, results = f"{settings.llm_model} ({settings.model_profile})", 0, []
        for c in cases:
            start = time.perf_counter()
            raw = qwen.generate(build_messages(c["transcript"]))
            elapsed_ms.append((time.perf_counter() - start) * 1000)
            parsed = parse_llm_output(raw)
            fallbacks += parsed is None
            if parsed is None:
                result = rule_analyze(c["transcript"])
            elif not is_grounded(parsed.summary, c["transcript"]):
                ungrounded.append(f"{c['id']}: \"{c['transcript']}\" → \"{parsed.summary}\"")
                result = parsed.model_copy(update={"summary": truncate_summary(c["transcript"])})
            else:
                result = parsed
            results.append(result)

    gold = [c["purpose"] for c in cases]
    pred = [r.purpose for r in results]
    accuracy = sum(g == p for g, p in zip(gold, pred)) / len(cases)
    over_20 = sum(len(r.summary) > 20 for r in results) / len(cases)
    critical = group_recall(gold, pred, CRITICAL)
    subtypes = subtype_accuracy([(c["purpose"], c.get("subtype")) for c in cases], [(r.purpose, r.subtype) for r in results])

    print(f"## 용건 분류 — {name}, {len(cases)}건\n")
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
        print(f"LLM 생성 시간: 중앙값 {elapsed_ms[len(elapsed_ms) // 2]:.0f}ms, 최대 {elapsed_ms[-1]:.0f}ms")
    print(f"말하지 않은 내용이라 요약을 전사문으로 바꿈: {len(ungrounded)}건")
    for line in ungrounded:
        print(f"- {line}")


if __name__ == "__main__":
    main()
