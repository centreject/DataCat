"""STT character error rate per audio folder (data/audio/<folder>/<id>.wav + <id>.txt).

Usage (from model-service/):  python -m eval.eval_stt
"""

from app.config import DATA_DIR, Settings
from app.media import decode_wav
from eval.metrics import TARGETS, cer, verdict


def main() -> None:
    from app.speech.whisper import WhisperSpeech

    settings = Settings()
    stt = WhisperSpeech(settings)
    print(f"## STT CER — {settings.stt_model} ({settings.stt_compute_type})\n")
    print("| 폴더 | 파일 수 | 평균 CER | 목표 ≤ 15% |\n|---|---:|---:|---|")
    worst = []
    for folder in sorted(p for p in (DATA_DIR / "audio").iterdir() if p.is_dir()):
        wavs = sorted(folder.glob("*.wav"))
        scores = []
        for wav in wavs:
            ref_path = wav.with_suffix(".txt")
            if not ref_path.exists():
                continue
            hyp = stt.transcribe(decode_wav(wav.read_bytes()))
            score = cer(ref_path.read_text().strip(), hyp)
            scores.append(score)
            worst.append((score, folder.name, wav.stem, hyp))
        if scores:
            mean = sum(scores) / len(scores)
            print(f"| {folder.name} | {len(scores)} | {mean:.1%} | {verdict(mean <= TARGETS['stt_cer_max'])} |")
    print("\n가장 많이 틀린 5개:")
    for score, folder, stem, hyp in sorted(worst, reverse=True)[:5]:
        print(f"- {folder}/{stem}: CER {score:.0%} → \"{hyp}\"")


if __name__ == "__main__":
    main()
