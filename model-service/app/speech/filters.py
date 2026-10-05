from collections.abc import Iterable

# Phrases Whisper tends to invent on silence/noise (learned from Korean YouTube/TV subtitles).
HALLUCINATION_PHRASES = (
    "시청해 주셔서 감사합니다",
    "시청해주셔서 감사합니다",
    "구독과 좋아요",
    "MBC 뉴스",
)


def clean_segments(segments: Iterable[tuple[str, float]], max_no_speech_prob: float = 0.6) -> str:
    """Join (text, no_speech_prob) segments, dropping likely non-speech and known hallucinations."""
    kept = [
        # U+FFFD appears when Whisper cuts a multi-byte token in half; never show it to users.
        text.replace("�", "").strip()
        for text, no_speech_prob in segments
        if no_speech_prob <= max_no_speech_prob and not any(p in text for p in HALLUCINATION_PHRASES)
    ]
    return " ".join(t for t in kept if t).strip()
