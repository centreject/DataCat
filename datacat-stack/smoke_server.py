"""Exercise the real Spring APIs against the isolated mock stack.

Run inside the model container, which already contains Pillow and Python.
Creates two synthetic visits. Never use this as real-model or hardware evidence.
"""
import argparse
import hashlib
import io
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
import wave
from datetime import datetime, timezone

from PIL import Image

BASE = os.environ.get("DATACAT_SMOKE_BASE_URL", "http://api:8080").rstrip("/")
MODEL = os.environ.get("DATACAT_SMOKE_MODEL_URL", "http://localhost:8000").rstrip("/")


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def request(path, method="GET", body=None, content_type=None, expected=200, raw=False):
    headers = {"Content-Type": content_type} if content_type else {}
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = response.read()
            check(response.status == expected, f"{method} {path}: HTTP {response.status}, expected {expected}")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"{method} {path}: HTTP {error.code}") from error
    return payload if raw else json.loads(payload)


def multipart(parts):
    boundary = uuid.uuid4().hex
    output = bytearray()
    for name, filename, mime, data in parts:
        disposition = f'form-data; name="{name}"'
        if filename:
            disposition += f'; filename="{filename}"'
        output.extend(f"--{boundary}\r\nContent-Disposition: {disposition}\r\nContent-Type: {mime}\r\n\r\n".encode())
        output.extend(data)
        output.extend(b"\r\n")
    output.extend(f"--{boundary}--\r\n".encode())
    return bytes(output), f"multipart/form-data; boundary={boundary}"


def create_visit(jpeg):
    metadata = {"deviceId": "week9-docker-" + uuid.uuid4().hex, "triggerType": "BUTTON",
                "distanceMm": 1850, "capturedAt": datetime.now(timezone.utc).isoformat()}
    body, mime = multipart([
        ("metadata", None, "application/json", json.dumps(metadata).encode()),
        ("image", "person.jpg", "image/jpeg", jpeg),
    ])
    visit = request("/api/v1/device/events", "POST", body, mime, expected=201)
    check(visit.get("status") == "WAITING_AUDIO" and visit.get("action") == "START_RECEPTION", "Photo reception did not start")
    check(visit.get("preset", {}).get("presetId") == 1, "Wrong greeting preset")
    return visit["eventId"]


def verify_delivery(event_id, snapshot_sha256):
    detail = request(f"/api/v1/events/{event_id}")
    check(detail.get("eventId") == event_id, "Wrong event ID")
    expected = {"status": "COMPLETED", "purpose": "DELIVERY", "mainCategory": "배송",
                "subCategory": "택배", "summary": "택배 문 앞 보관",
                "transcript": "택배 왔습니다. 문 앞에 놓고 갈게요."}
    for key, value in expected.items():
        check(detail.get(key) == value, f"Unexpected delivery field: {key}")
    snapshot = request(f"/api/v1/events/{event_id}/snapshot", raw=True)
    check(hashlib.sha256(snapshot).hexdigest() == snapshot_sha256, "Snapshot bytes changed or were lost")


def require_mock():
    with urllib.request.urlopen(MODEL + "/health", timeout=10) as response:
        health = json.load(response)
    check(health.get("status") == "ok" and health.get("profile") == "mock", "This test requires the ready mock model")


def run():
    require_mock()
    check(len(request("/api/v1/presets")) == 3, "Expected three presets")
    jpeg_buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (145, 170, 195)).save(jpeg_buffer, format="JPEG")
    jpeg = jpeg_buffer.getvalue()
    snapshot_sha = hashlib.sha256(jpeg).hexdigest()
    event_id = create_visit(jpeg)

    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 1600)
    body, mime = multipart([("audio", "delivery.wav", "audio/wav", wav_buffer.getvalue())])
    result = request(f"/api/v1/device/events/{event_id}/audio", "POST", body, mime)
    check(result.get("eventId") == event_id and result.get("status") == "COMPLETED", "Audio did not complete the same visit")
    check(result.get("action") == "PLAY_PRESET" and result.get("preset", {}).get("presetId") == 2, "Wrong completion preset")
    verify_delivery(event_id, snapshot_sha)
    repeated = request(f"/api/v1/device/events/{event_id}/audio", "POST", body, mime)
    check(repeated == result, "Repeated audio response differs")

    end_id = create_visit(jpeg)
    end_body = json.dumps({"reason": "VISITOR_LEFT", "endedAt": datetime.now(timezone.utc).isoformat()}).encode()
    ended = request(f"/api/v1/device/events/{end_id}/end", "POST", end_body, "application/json")
    check(ended.get("eventId") == end_id and ended.get("status") == "COMPLETED" and ended.get("action") == "END_SESSION", "End request failed")
    check(request(f"/api/v1/events/{end_id}").get("endedAt") is not None, "End timestamp missing")
    return {"result": "PASS", "modelProfile": "mock", "deliveryEventId": event_id,
            "endEventId": end_id, "snapshotSha256": snapshot_sha,
            "createdAt": datetime.now(timezone.utc).isoformat(), "pushChecked": False,
            "hardwareChecked": False}


def verify():
    report = json.load(sys.stdin)
    check(report.get("result") == "PASS" and report.get("modelProfile") == "mock", "Input must be the previous successful smoke report")
    verify_delivery(report["deliveryEventId"], report["snapshotSha256"])
    ended = request(f"/api/v1/events/{report['endEventId']}")
    check(ended.get("status") == "COMPLETED" and ended.get("endedAt") is not None, "Ended visit was lost")
    return {"result": "PASS", "check": "database-and-snapshot-persistence",
            "deliveryEventId": report["deliveryEventId"], "endEventId": report["endEventId"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "verify"])
    args = parser.parse_args()
    try:
        print(json.dumps(run() if args.action == "run" else verify(), ensure_ascii=True))
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
