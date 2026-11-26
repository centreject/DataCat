"""R1: real door photos and mic recordings — recording sheet + evaluation.

Everything lives in data/real/ (git-ignored: faces, unit numbers and voices never enter the repository).

  python -m eval.real_data sheet [--distances 20,50,100]   # writes data/real/recording_sheet.md + labels.csv
  python -m eval.real_data eval [--split test|tune|all]    # runs the real models over labels.csv (GPU)
  python -m eval.real_data eval --split tune --errors      # also lists the wrong photo/voice files

labels.csv (one row per file, paths relative to data/real/):
  file          photo/....jpg or voice/....wav (WAV: 16 kHz mono 16-bit, as the Pi uploads)
  kind          photo | voice
  truth         photo: person, package, animal joined by "+" (e.g. "person+package"), or "empty"
                voice: the purpose id (DELIVERY, SAFETY_REVIEW, ...)
  subtype       voice, DELIVERY only (PARCEL, FOOD, ...); else empty
  text          voice: what was meant to be said (for the character error rate)
  distance_cm   mouth-to-mic or person-to-camera distance; empty if not measured
  light         photo: day | night; else empty
  split         tune (may be looked at and tuned on) | test (measured only, never tuned on)

Recording sentences: the 45 held-out 김덕민 sentences are read aloud as the test split (the models never
saw their text during tuning); 3 dev sentences per purpose form the tune split.
"""

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.config import DATA_DIR
from eval.metrics import cer

REAL = DATA_DIR / "real"
EVAL = Path(__file__).resolve().parent
PHOTO_LABELS = {"person", "package", "animal"}
CRITICAL = {"PUBLIC_EMERGENCY", "SAFETY_REVIEW"}
FIELDS = ["file", "kind", "truth", "subtype", "text", "distance_cm", "light", "split"]


@dataclass
class Row:
    file: str
    kind: str
    truth: str
    subtype: str
    text: str
    distance_cm: str
    light: str
    split: str

    def photo_labels(self) -> set[str]:
        return set() if self.truth == "empty" else set(self.truth.split("+"))


def load_labels(path: Path) -> list[Row]:
    """Read labels.csv and refuse rows the evaluation would silently miscount."""
    from app.language.purposes import CATALOG

    rows, problems = [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for n, raw in enumerate(csv.DictReader(f), start=2):
            row = Row(**{k: (raw.get(k) or "").strip() for k in FIELDS})
            if row.kind not in ("photo", "voice"):
                problems.append(f"{n}행: kind는 photo 또는 voice")
            elif row.kind == "photo" and row.truth != "empty" and not row.photo_labels() <= PHOTO_LABELS:
                problems.append(f"{n}행: 사진 truth는 person/package/animal을 +로 잇거나 empty")
            elif row.kind == "voice" and row.truth not in {p["id"] for p in CATALOG.purposes}:
                problems.append(f"{n}행: 음성 truth는 용건 id여야 함({row.truth!r})")
            elif row.kind == "voice" and not row.text:
                problems.append(f"{n}행: 음성 text(읽은 문장)가 비어 있음")
            elif row.subtype and (row.kind != "voice"
                                  or row.subtype not in {e["id"] for e in CATALOG.get(row.truth).get("subtypes", [])}):
                problems.append(f"{n}행: subtype {row.subtype!r}은 이 용건의 세부 유형이 아님")
            if not row.file:
                problems.append(f"{n}행: file이 비어 있음")
            if row.split not in ("tune", "test"):
                problems.append(f"{n}행: split은 tune 또는 test")
            rows.append(row)
    if problems:
        raise ValueError("labels.csv 오류:\n" + "\n".join(problems))
    return rows


def _cases(name: str) -> list[dict]:
    return [json.loads(line) for line in (EVAL / name).read_text("utf-8").splitlines() if line.strip()]


def make_sheet(distances: list[int]) -> tuple[str, list[dict]]:
    """Markdown sheet to read from, and labels.csv rows already filled in for each recording."""
    test = _cases("deokmin_cases.jsonl")
    tune, seen = [], defaultdict(int)
    for c in _cases("purpose_cases.jsonl"):
        if seen[c["purpose"]] < 3:
            seen[c["purpose"]] += 1
            tune.append(c)
    lines = ["# 실제 마이크 녹음 문장표", "",
             f"거리마다(입에서 마이크까지 {', '.join(f'{d}cm' for d in distances)}) 아래 문장을 한 번씩 읽는다. "
             "파일 이름은 표의 이름 그대로(`voice/` 폴더). 틀리면 다시 녹음해 덮어쓴다.", "",
             "| 파일 이름(거리마다 _20cm 등) | 나눔 | 정답 용건 | 문장 |", "|---|---|---|---|"]
    labels = []
    for split, cases in (("test", test), ("tune", tune)):
        for c in cases:
            lines.append(f"| {c['id']}_<거리>cm.wav | {split} | {c['purpose']} | {c['transcript']} |")
            for d in distances:
                labels.append({"file": f"voice/{c['id']}_{d}cm.wav", "kind": "voice", "truth": c["purpose"],
                               "subtype": c.get("subtype") or "", "text": c["transcript"],
                               "distance_cm": str(d), "light": "", "split": split})
    return "\n".join(lines) + "\n", labels


def _rate(hits: int, n: int) -> str:
    return f"{hits}/{n} ({hits / n:.0%})" if n else "—"


def format_photo_results(records: list[tuple[Row, set[str]]], show_errors: bool = False) -> list[str]:
    groups: dict[str, list[tuple[set[str], set[str]]]] = defaultdict(list)
    for r, found in records:
        for key in ("전체", f"빛 {r.light or '?'}", f"거리 {r.distance_cm or '?'}cm"):
            groups[key].append((r.photo_labels(), found))
    out = ["| 묶음 | 사람 찾음 | 물품 찾음 | 동물 찾음 | 사람 없는 사진에서 '사람'(오탐) "
           "| 물품 없는 사진에서 '물품'(오탐) | 빈 사진에서 무엇이든 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for key, pairs in groups.items():
        cells = []
        for label in ("person", "package", "animal"):
            have = [f for t, f in pairs if label in t]
            cells.append(_rate(sum(label in f for f in have), len(have)))
        for label in ("person", "package"):
            without = [f for t, f in pairs if label not in t]
            cells.append(_rate(sum(label in f for f in without), len(without)))
        empty = [f for t, f in pairs if not t]
        cells.append(_rate(sum(bool(f) for f in empty), len(empty)))
        out.append(f"| {key} | " + " | ".join(cells) + " |")
    if show_errors:
        out += ["", "#### 틀린 사진 (tune만)", "", "| 파일 | 정답 | 결과 | 빛 | 거리 |", "|---|---|---|---|---|"]
        for r, found in records:
            truth = r.photo_labels()
            if truth != found:
                want = "+".join(sorted(truth)) if truth else "empty"
                have = "+".join(sorted(found)) if found else "empty"
                out.append(f"| {r.file} | {want} | {have} | {r.light or '?'} | {r.distance_cm or '?'}cm |")
    return out


def eval_photos(rows: list[Row], show_errors: bool = False) -> list[str]:
    from app.config import Settings
    from app.media import decode_jpeg
    from app.vision.yolo import YoloVision

    vision = YoloVision(Settings())
    records = [
        # Same decoding as the service (EXIF rotation), so phone photos are seen upright.
        (r, {d.label for d in vision.detect(decode_jpeg((REAL / r.file).read_bytes()))})
        for r in rows
    ]
    return format_photo_results(records, show_errors=show_errors)


def format_voice_results(records: list[tuple[Row, str, object]], show_errors: bool = False) -> list[str]:
    groups: dict[str, list[tuple[Row, str, object]]] = defaultdict(list)
    for r, transcript, got in records:
        for key in ("전체", f"거리 {r.distance_cm or '?'}cm"):
            groups[key].append((r, transcript, got))
    out = ["| 묶음 | 건수 | 글자 오류율 | 빈 받아쓰기 | 용건 정확도 | 배송 세부 유형 | 긴급·위협 찾음 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    for key, items in groups.items():
        n = len(items)
        mean_cer = sum(cer(r.text, t) for r, t, _ in items) / n
        critical = [g for r, _, g in items if r.truth in CRITICAL]
        # Same denominator as eval.metrics.subtype_accuracy: include every gold-subtyped row so
        # misclassified purpose or NO_SPEECH counts as a miss instead of being dropped.
        typed = [(r, g) for r, _, g in items if r.subtype]
        out.append(f"| {key} | {n} | {mean_cer:.1%} | {sum(not t for _, t, _ in items)} | "
                   f"{_rate(sum(r.truth == g.purpose for r, _, g in items), n)} | "
                   f"{_rate(sum(r.truth == g.purpose and r.subtype == g.subtype for r, g in typed), len(typed))} | "
                   f"{_rate(sum(g.purpose in CRITICAL for g in critical), len(critical))} |")
    if show_errors:
        out += ["", "#### 틀린 것 (tune만)", "", "| 파일 | 정답 | 결과 | 받아쓰기 |", "|---|---|---|---|"]
        for r, t, g in records:
            if r.truth != g.purpose or (r.subtype and r.subtype != g.subtype):
                want = r.truth + (f"/{r.subtype}" if r.subtype else "")
                have = g.purpose + (f"/{g.subtype}" if g.subtype else "")
                out.append(f"| {r.file} | {want} | {have} | {t or '(빈 받아쓰기)'} |")
    return out


def eval_voices(rows: list[Row], show_errors: bool = False) -> list[str]:
    from app.config import Settings
    from app.language.qwen import QwenLanguage
    from app.media import decode_wav
    from app.pipeline import analyze_transcript
    from app.speech.whisper import WhisperSpeech

    settings = Settings()
    stt, llm = WhisperSpeech(settings), QwenLanguage(settings)
    records = []
    for r in rows:
        transcript = stt.transcribe(decode_wav((REAL / r.file).read_bytes()))
        records.append((r, transcript, analyze_transcript(llm, transcript)))
    return format_voice_results(records, show_errors=show_errors)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("--distances", default="20,50,100")
    e = sub.add_parser("eval")
    e.add_argument("--split", choices=("test", "tune", "all"), default="test")
    e.add_argument("--errors", action="store_true", help="틀린 사진·음성 파일 목록 (tune에서만: test는 보고 고치지 않는다)")
    args = parser.parse_args()
    if getattr(args, "errors", False) and args.split != "tune":
        parser.error("--errors는 --split tune에서만 쓴다")

    if args.cmd == "sheet":
        sheet, labels = make_sheet([int(d) for d in args.distances.split(",")])
        (REAL / "voice").mkdir(parents=True, exist_ok=True)
        (REAL / "photo").mkdir(parents=True, exist_ok=True)
        (REAL / "recording_sheet.md").write_text(sheet, encoding="utf-8")
        path = REAL / "labels.csv"
        if path.exists():
            print(f"{path} 이미 있음 — 덮어쓰지 않음(사진 행을 지울 수 있어서). 음성 행은 recording_sheet.md 참고.")
        else:
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, FIELDS)
                w.writeheader()
                w.writerows(labels)
            print(f"{path}: 음성 {len(labels)}행. 사진은 같은 형식으로 행을 더한다.")
        print(f"{REAL / 'recording_sheet.md'}")
        return

    rows = [r for r in load_labels(REAL / "labels.csv") if args.split == "all" or r.split == args.split]
    present = [r for r in rows if (REAL / r.file).exists()]
    print(f"## 실제 데이터 평가 — split {args.split}, 파일 {len(present)}/{len(rows)}개 있음\n")
    if photos := [r for r in present if r.kind == "photo"]:
        print("### 사진\n\n" + "\n".join(eval_photos(photos, args.errors)) + "\n")
    if voices := [r for r in present if r.kind == "voice"]:
        print("### 음성\n\n" + "\n".join(eval_voices(voices, args.errors)))


if __name__ == "__main__":
    main()
