#!/usr/bin/env python3
"""USB 웹캠 JPEG 촬영. 사진은 메모리(bytes)로 반환하고 파일로 남기지 않는다."""

import argparse

DEFAULT_DEVICE = 0     # /dev/video0
WARMUP_FRAMES = 10     # 장치를 연 직후 프레임은 노출이 맞지 않아 버린다.
JPEG_QUALITY = 85


def capture_jpeg(device=DEFAULT_DEVICE, quality=JPEG_QUALITY):
    """JPEG bytes를 반환한다. 실패하면 OSError."""
    import cv2
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    try:
        if not cap.isOpened():
            raise OSError(f"/dev/video{device}를 열 수 없습니다 (video 그룹 권한, 다른 프로그램 사용 여부 확인)")
        for _ in range(WARMUP_FRAMES):
            cap.grab()
        ok, frame = cap.read()
        if not ok:
            raise OSError("웹캠에서 프레임을 읽지 못했습니다.")
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise OSError("JPEG 변환 실패")
        return buf.tobytes()
    finally:
        cap.release()


def main():
    parser = argparse.ArgumentParser(description="웹캠 촬영 시험")
    parser.add_argument("output", nargs="?", default="cam_test.jpg")
    parser.add_argument("--device", type=int, default=DEFAULT_DEVICE)
    args = parser.parse_args()
    try:
        jpeg = capture_jpeg(args.device)
    except OSError as exc:
        print(f"촬영 실패: {exc}")
        return 1
    with open(args.output, "wb") as f:
        f.write(jpeg)
    print(f"저장: {args.output} ({len(jpeg)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
