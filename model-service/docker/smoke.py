"""Smoke-test a running model service (e.g. the Docker container) over HTTP.

Usage (from model-service/):
  python docker/smoke.py [--url http://localhost:8000] [--wait 900] [--api-key KEY]
Waits for /health to report "ok" or "degraded", then calls every endpoint once with sample data and checks
the response shape against API v1.6. Exit code 0 = all good. Standard library only, so it runs
with any Python 3.11 (teammates don't need the model venv).
"""

import argparse
import base64
import io
import json
import math
import os
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
# Minimal valid 16x16 textured JPEG (stdlib-only fallback when data/images/person/ has not been downloaded).
_FALLBACK_JPEG_B64 = (
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQ"
    "ERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU"
    "FBQUFBQUFBQUFBQUFBT/wAARCAAQABADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAA"
    "AgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6"
    "Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG"
    "x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREA"
    "AgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5"
    "OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPE"
    "xcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwCnquq3Vtfyxxy7UXGBtB7D2o0rVbq5v4o5"
    "JdyNnI2gdj7UarpV1c38skcW5Gxg7gOw96NK0q6tr+KSSLai5ydwPY+9eD/wo/2j9vk5/wC9a3N91rfKx+n/APCF/YX/AC59"
    "t7H+5zc3J9/Nf538z//Z"
)


def request(
    url: str,
    body: bytes | None = None,
    content_type: str | None = None,
    api_key: str | None = None,
) -> tuple[int, dict]:
    headers = {}
    if content_type:
        headers["Content-Type"] = content_type
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(url, data=body, headers=headers)
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
    for path in (DATA / "audio" / "tts" / "delivery_01.wav", ROOT / "preset-audio" / "final" / "greeting.wav"):
        if path.exists():
            return path.read_bytes()
    buf = io.BytesIO()  # 1 s tone: STT should return "" (no speech)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 5))) for i in range(16000)))
    return buf.getvalue()


def sample_jpeg() -> bytes:
    images = sorted((DATA / "images" / "person").glob("*.jpg"))
    return images[0].read_bytes() if images else base64.b64decode(_FALLBACK_JPEG_B64)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--wait", type=int, default=900, help="seconds to wait for /health ok")
    parser.add_argument("--api-key", default=os.environ.get("MODEL_API_KEY", ""),
                        help="X-Api-Key header when MODEL_API_KEY is set on the server")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    api_key = args.api_key or None

    deadline = time.time() + args.wait
    status, health = None, {}
    while time.time() < deadline:
        try:
            health = request(f"{base}/health")[1]
            status = health.get("status")
        except (urllib.error.URLError, ConnectionError):
            status = "unreachable"
        if status in ("ok", "degraded", "error"):
            break
        time.sleep(5)
    print(f"/health: {status} {json.dumps(health, ensure_ascii=False)}")
    # degraded = still serving (e.g. zero-shot package fallback); only a stuck model fails the smoke test.
    if status not in ("ok", "degraded") or health.get("stuck"):
        sys.exit(1)

    failures = []

    def check(name: str, code: int, body: dict, keys: set[str]) -> None:
        ok = code == 200 and set(body) == keys
        print(f"{'PASS' if ok else 'FAIL'} {name}: {code} {json.dumps(body, ensure_ascii=False)}")
        if not ok:
            failures.append(name)

    body, ctype = multipart("image", "door.jpg", sample_jpeg(), "image/jpeg")
    check("vision/detect", *request(f"{base}/internal/v1/vision/detect", body, ctype, api_key), {"detections", "flags"})
    wav = sample_wav()
    body, ctype = multipart("audio", "voice.wav", wav, "audio/wav")
    check("speech/transcribe", *request(f"{base}/internal/v1/speech/transcribe", body, ctype, api_key), {"transcript"})
    text = json.dumps({"transcript": "택배 왔습니다. 문 앞에 놓고 갈게요."}).encode()
    check("language/analyze", *request(f"{base}/internal/v1/language/analyze", text, "application/json", api_key),
          {"summary", "purpose", "subtype", "flags"})
    body, ctype = multipart("audio", "voice.wav", wav, "audio/wav")
    check("audio/process", *request(f"{base}/internal/v1/audio/process", body, ctype, api_key),
          {"transcript", "purpose", "subtype", "summary", "flags"})
    code, err = request(f"{base}/internal/v1/language/analyze", b"{}", "application/json", api_key)
    check_error = code == 400 and err.get("code") == "INVALID_REQUEST"
    print(f"{'PASS' if check_error else 'FAIL'} error format: {code} {err}")
    if not check_error:
        failures.append("error format")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
