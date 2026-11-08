"""Isolated mock stack only: normal flow, device cancellation and server expiry.

This takes about 2-3 minutes with the default 120 second expiry.
Never treat the result as speaker, physical Pi or actual inference evidence.
"""
import io
import json
import sys
import time
import urllib.error
import urllib.request
import wave
from datetime import datetime, timezone

from PIL import Image
import smoke_server as smoke


def run():
    normal = smoke.run()
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (145, 170, 195)).save(buf, format="JPEG")
    jpeg = buf.getvalue()
    cancelled_id = smoke.create_visit(jpeg)
    path = f"/api/v1/device/events/{cancelled_id}/end"
    body = json.dumps({"reason": "DEVICE_CANCELLED", "endedAt": datetime.now(timezone.utc).isoformat()}).encode()
    cancelled = smoke.request(path, "POST", body, "application/json")
    smoke.check(cancelled.get("action") == "END_SESSION", "Device cancellation was rejected")
    detail = smoke.request(f"/api/v1/events/{cancelled_id}")
    smoke.check(detail.get("needsReview") is True and detail.get("processingStatus") == "단말 확인 필요",
                "Device cancellation is not reviewable")
    smoke.request(path, "POST", body, "application/json")
    smoke.check(smoke.request(f"/api/v1/events/{cancelled_id}").get("endedAt") == detail.get("endedAt"),
                "Repeated cancellation changed end time")

    expired_id = smoke.create_visit(jpeg)
    print(f"Waiting for server expiry, eventId={expired_id} (up to 180s)...", file=sys.stderr, flush=True)
    started = time.monotonic()
    while True:
        expired = smoke.request(f"/api/v1/events/{expired_id}")
        if expired.get("status") == "COMPLETED":
            break
        smoke.check(time.monotonic() - started < 180, "Server expiry did not finish within 180s; check timer settings and API logs")
        time.sleep(1)
    smoke.check(expired.get("needsReview") is True
                and expired.get("reason") == "후속 요청 없이 세션 대기 시간 초과",
                "Abandoned visit did not expire with the expected reason")

    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 1600)
    body, mime = smoke.multipart([("audio", "delivery.wav", "audio/wav", wav_buf.getvalue())])
    req = urllib.request.Request(smoke.BASE + f"/api/v1/device/events/{expired_id}/audio",
                                 data=body, method="POST", headers={"Content-Type": mime})
    try:
        with urllib.request.urlopen(req, timeout=30):
            raise RuntimeError("Expired visit unexpectedly accepted late audio")
    except urllib.error.HTTPError as error:
        payload = json.load(error)
        smoke.check(error.code == 409 and payload.get("code") == "EVENT_STATE_CONFLICT",
                    "Late audio was not rejected as a state conflict")
    smoke.verify_delivery(normal["deliveryEventId"], normal["snapshotSha256"])
    return {"result": "PASS", "modelProfile": "mock", "deliveryEventId": normal["deliveryEventId"],
            "deviceCancelledEventId": cancelled_id, "expiredEventId": expired_id,
            "observedExpiryWaitSeconds": round(time.monotonic() - started, 1),
            "pushChecked": False, "hardwareChecked": False, "actualModelChecked": False}


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=True))
    except Exception as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
