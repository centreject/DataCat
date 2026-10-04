"""Write docs/openapi.json and docs/examples/*.json from the code, so they can't drift from it.

Usage (from model-service/):  python docs/make_api_docs.py
Examples are real responses of the mock service (app/mock.py) — same shape as the real one.
tests/test_mock.py fails when these files are out of date.
"""

import io
import json
import math
import os
import struct
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import create_app  # noqa: E402
from app.registry import ModelRegistry  # noqa: E402

DOCS = ROOT / "docs"


def sample_jpeg(textured: bool = True) -> bytes:
    image = Image.new("L", (64, 48), 40)
    if textured:  # a pattern, so LOW_VISIBILITY stays off
        image.putdata([(x * 7 + y * 13) % 256 for y in range(48) for x in range(64)])
    buf = io.BytesIO()
    image.convert("RGB").save(buf, "JPEG")
    return buf.getvalue()


def sample_wav(rate: int = 16000, channels: int = 1) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i / 5))) for i in range(rate * channels)))
    return buf.getvalue()


def openapi() -> dict:
    app = create_app(lambda s: ModelRegistry(vision=None, stt=None, language=None, ready=True))
    return app.openapi()


def examples() -> dict[str, object]:
    """name → response body, from the mock service."""
    os.environ["MODEL_PROFILE"] = "mock"
    try:
        app = create_app()
    finally:
        del os.environ["MODEL_PROFILE"]
    out: dict[str, object] = {}
    with TestClient(app) as client:
        app.state.loader.join(timeout=5)
        out["health"] = {"status": "ok", "profile": "lite"}

        def detect(name: str, jpeg: bytes) -> dict:
            return client.post("/internal/v1/vision/detect", files={"image": (name, jpeg, "image/jpeg")}).json()

        out["vision_detect_person_package"] = detect("person_package.jpg", sample_jpeg())
        out["vision_detect_package_only"] = detect("package.jpg", sample_jpeg())
        out["vision_detect_covered_lens"] = detect("empty.jpg", sample_jpeg(textured=False))
        for scenario in ("delivery", "food", "emergency", "silent"):
            r = client.post("/internal/v1/audio/process", files={"audio": (f"{scenario}.wav", sample_wav(), "audio/wav")})
            out[f"audio_process_{scenario}"] = r.json()
        r = client.post("/internal/v1/audio/process", files={"audio": ("v.wav", sample_wav(44100, 2), "audio/wav")})
        out["error_invalid_audio"] = r.json()
    out["error_model_not_ready"] = {"code": "MODEL_NOT_READY", "message": "stt 모델이 아직 준비되지 않았습니다."}
    return out


def render() -> dict[Path, str]:
    files = {DOCS / "openapi.json": openapi()}
    files.update({DOCS / "examples" / f"{name}.json": body for name, body in examples().items()})
    return {path: json.dumps(body, ensure_ascii=False, indent=2) + "\n" for path, body in files.items()}


def main() -> None:
    for path, text in render().items():
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
