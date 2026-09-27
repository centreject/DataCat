"""Smoke-test a running model service (e.g. the Docker container) over HTTP.

Usage (from model-service/):  python docker/smoke.py [--url http://localhost:8000] [--wait 900]
Waits for /health to report "ok", then calls every endpoint once with sample data and checks
the response shape against API v1.3. Exit code 0 = all good. Standard library only, so it runs
with any Python 3.11 (teammates don't need the model venv).
"""

import argparse
import io
import json
import math
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def request(url: str, body: bytes | None = None, content_type: str | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=body, headers={"Content-Type": content_type} if content_type else {})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def multipart(field: str, filename: str, data: bytes, mime: str) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def sample_wav() -> bytes:
    tts = DATA / "audio" / "tts" / "delivery_01.wav"
    if tts.exists():
        return tts.read_bytes()
    buf = io.BytesIO()  # 1 s tone: STT should return "" (no speech)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 5))) for i in range(16000)))
    return buf.getvalue()


def sample_jpeg() -> bytes:
    images = sorted((DATA / "images" / "person").glob("*.jpg"))
    if not images:
        sys.exit("no sample JPEG: run `python eval/prepare_images.py` first")
    return images[0].read_bytes()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--wait", type=int, default=900, help="seconds to wait for /health ok")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    deadline = time.time() + args.wait
    status = None
    while time.time() < deadline:
        try:
            status = request(f"{base}/health")[1].get("status")
        except (urllib.error.URLError, ConnectionError):
            status = "unreachable"
        if status in ("ok", "error"):
            break
        time.sleep(5)
    print(f"/health: {status}")
    if status != "ok":
        sys.exit(1)

    failures = []

    def check(name: str, code: int, body: dict, keys: set[str]) -> None:
        ok = code == 200 and set(body) == keys
        print(f"{'PASS' if ok else 'FAIL'} {name}: {code} {json.dumps(body, ensure_ascii=False)}")
        if not ok:
            failures.append(name)

    body, ctype = multipart("image", "door.jpg", sample_jpeg(), "image/jpeg")
    check("vision/detect", *request(f"{base}/internal/v1/vision/detect", body, ctype), {"detections"})
    wav = sample_wav()
    body, ctype = multipart("audio", "voice.wav", wav, "audio/wav")
    check("speech/transcribe", *request(f"{base}/internal/v1/speech/transcribe", body, ctype), {"transcript"})
    text = json.dumps({"transcript": "택배 왔습니다. 문 앞에 놓고 갈게요."}).encode()
    check("language/analyze", *request(f"{base}/internal/v1/language/analyze", text, "application/json"),
          {"summary", "purpose"})
    body, ctype = multipart("audio", "voice.wav", wav, "audio/wav")
    check("audio/process", *request(f"{base}/internal/v1/audio/process", body, ctype),
          {"transcript", "purpose", "summary"})
    code, err = request(f"{base}/internal/v1/language/analyze", b"{}", "application/json")
    check_error = code == 400 and err.get("code") == "INVALID_REQUEST"
    print(f"{'PASS' if check_error else 'FAIL'} error format: {code} {err}")
    if not check_error:
        failures.append("error format")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
