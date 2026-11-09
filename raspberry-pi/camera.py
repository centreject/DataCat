#!/usr/bin/env python3
"""JPEG 촬영. 사진은 메모리(bytes)로 반환하고 파일로 남기지 않는다.

카메라 두 종류를 지원한다. DATACAT_CAMERA 환경변수로 고른다.
  csi   Camera Module 3 (CSI 리본). rpicam-still을 호출한다. (imx708 드라이버·libcamera·rpicam-apps 필요)
  usb   USB 웹캠. OpenCV로 /dev/videoN을 연다.
  auto  (기본) rpicam-still이 있으면 csi, 없으면 usb.
"""

import argparse
import os
import shutil
import subprocess

DEFAULT_DEVICE = 0     # USB 웹캠 /dev/video0 (CSI 카메라를 달면 0번은 unicam이 차지하므로 --device로 바꾼다)
WARMUP_FRAMES = 10     # USB: 장치를 연 직후 프레임은 노출이 맞지 않아 버린다.
JPEG_QUALITY = 85

CAMERA = os.environ.get("DATACAT_CAMERA", "auto")
# CSI: 2304x1296은 센서 2x2 binning 모드라 전체 화각을 유지하면서 빠르다(4608x2592의 1/4 크기).
CSI_WIDTH = int(os.environ.get("DATACAT_CAMERA_WIDTH", "2304"))
CSI_HEIGHT = int(os.environ.get("DATACAT_CAMERA_HEIGHT", "1296"))
CSI_ROTATION = int(os.environ.get("DATACAT_CAMERA_ROTATION", "0"))   # 0 또는 180만 가능
CSI_SETTLE_MS = 500    # 노출·화이트밸런스·초점이 맞을 때까지 기다리는 시간. 실측 촬영 전체 약 1.2초
CSI_TIMEOUT_S = 15


def resolve_backend(name=CAMERA):
    if name == "auto":
        return "csi" if shutil.which("rpicam-still") else "usb"
    if name in ("csi", "usb"):
        return name
    raise ValueError(f"DATACAT_CAMERA는 auto, csi, usb 중 하나여야 합니다: {name!r}")


def capture_jpeg(device=DEFAULT_DEVICE, quality=JPEG_QUALITY, backend=None):
    """JPEG bytes를 반환한다. 실패하면 OSError."""
    if resolve_backend(backend or CAMERA) == "csi":
        return _capture_csi(quality)
    return _capture_usb(device, quality)


def _capture_csi(quality):
    cmd = ["rpicam-still", "-n", "-v", "0", "-t", str(CSI_SETTLE_MS),
           "--width", str(CSI_WIDTH), "--height", str(CSI_HEIGHT),
           "--rotation", str(CSI_ROTATION), "-q", str(quality), "-o", "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=CSI_TIMEOUT_S)
    except FileNotFoundError as exc:
        raise OSError("rpicam-still이 없습니다 (rpicam-apps 설치 확인)") from exc
    except subprocess.TimeoutExpired as exc:
        raise OSError(f"rpicam-still이 {CSI_TIMEOUT_S}초 안에 끝나지 않았습니다") from exc
    jpeg = result.stdout
    if result.returncode != 0 or not jpeg.startswith(b"\xff\xd8"):
        lines = result.stderr.decode(errors="replace").strip().splitlines()
        detail = lines[-1] if lines else f"종료 코드 {result.returncode}"
        raise OSError(f"CSI 카메라 촬영 실패: {detail}")
    return jpeg


def _capture_usb(device, quality):
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
    parser = argparse.ArgumentParser(description="카메라 촬영 시험")
    parser.add_argument("output", nargs="?", default="cam_test.jpg")
    parser.add_argument("--camera", choices=["auto", "csi", "usb"], default=CAMERA)
    parser.add_argument("--device", type=int, default=DEFAULT_DEVICE, help="USB 웹캠 번호")
    args = parser.parse_args()
    backend = resolve_backend(args.camera)
    try:
        jpeg = capture_jpeg(args.device, backend=backend)
    except OSError as exc:
        print(f"촬영 실패({backend}): {exc}")
        return 1
    with open(args.output, "wb") as f:
        f.write(jpeg)
    print(f"저장({backend}): {args.output} ({len(jpeg)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
