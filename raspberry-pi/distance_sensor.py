#!/usr/bin/env python3
"""HC-SR04 거리 측정. 감지 거리는 실행 옵션으로 지정한다."""

import argparse
import math
import time


TRIG_PIN = 24  # BCM 번호, 물리 핀 18
ECHO_PIN = 23  # BCM 번호, 물리 핀 16. 분압 회로를 거쳐 연결한다.
ECHO_TIMEOUT = 0.03


def measure_distance(gpio):
    """거리(cm)를 반환한다. 응답 지연이나 측정 범위 이탈은 None이다."""
    # 이전 펄스가 남아 있다면 이번 측정은 건너뛴다.
    if gpio.input(ECHO_PIN):
        return None

    gpio.output(TRIG_PIN, True)
    time.sleep(0.00001)
    gpio.output(TRIG_PIN, False)

    deadline = time.monotonic() + ECHO_TIMEOUT
    while not gpio.input(ECHO_PIN):
        if time.monotonic() >= deadline:
            return None
    pulse_start = time.monotonic()

    deadline = pulse_start + ECHO_TIMEOUT
    while gpio.input(ECHO_PIN):
        if time.monotonic() >= deadline:
            return None
    pulse_end = time.monotonic()

    distance = (pulse_end - pulse_start) * 34300 / 2
    return distance if 2 <= distance <= 400 else None


class ProximityDetector:
    """연속 측정으로 접근/이탈을 확인하고 같은 접근의 중복 출력을 막는다."""

    def __init__(self, threshold_cm, release_cm, samples=3):
        if not (2 <= threshold_cm < release_cm <= 400):
            raise ValueError("2 <= 감지 거리 < 해제 거리 <= 400 조건이 필요합니다.")
        if samples < 1:
            raise ValueError("연속 측정 횟수는 1 이상이어야 합니다.")
        self.threshold_cm = threshold_cm
        self.release_cm = release_cm
        self.samples = samples
        self.active = False
        self.count = 0

    def update(self, distance):
        if distance is None or not math.isfinite(distance) or not 2 <= distance <= 400:
            self.count = 0
            return None

        crossed = (distance >= self.release_cm if self.active
                   else distance <= self.threshold_cm)
        self.count = self.count + 1 if crossed else 0
        if self.count < self.samples:
            return None

        self.active = not self.active
        self.count = 0
        return "APPROACH" if self.active else "CLEAR"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold-cm", type=float, help="접근 감지 거리(cm)")
    parser.add_argument("--release-cm", type=float, help="감지 해제 거리(cm), 감지 거리보다 크게 지정")
    parser.add_argument("--samples", type=int, default=3, help="상태 변경에 필요한 연속 측정 횟수(기본: 3)")
    args = parser.parse_args()
    if (args.threshold_cm is None) != (args.release_cm is None):
        parser.error("--threshold-cm과 --release-cm을 함께 지정하세요.")
    if args.samples < 1:
        parser.error("--samples는 1 이상이어야 합니다.")
    if args.threshold_cm is not None:
        if not (2 <= args.threshold_cm < args.release_cm <= 400):
            parser.error("2 <= 감지 거리 < 해제 거리 <= 400 조건이 필요합니다.")
    return args


def main():
    args = parse_args()
    try:
        import RPi.GPIO as GPIO
    except (ImportError, RuntimeError) as exc:
        print(f"GPIO를 사용할 수 없습니다: {exc}")
        print("Raspberry Pi에서 python3-rpi.gpio 설치와 실행 환경을 확인하세요.")
        return 1

    detector = (ProximityDetector(args.threshold_cm, args.release_cm, args.samples)
                if args.threshold_cm is not None else None)
    configured_pins = []
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TRIG_PIN, GPIO.OUT, initial=GPIO.LOW)
        configured_pins.append(TRIG_PIN)
        GPIO.setup(ECHO_PIN, GPIO.IN)
        configured_pins.append(ECHO_PIN)
        time.sleep(0.1)
        if detector:
            print(f"접근 <= {args.threshold_cm:g}cm / 해제 >= {args.release_cm:g}cm / 연속 {args.samples}회")
        else:
            print("거리 측정 모드: 감지 기준이 지정되지 않았습니다.")
        print("종료: Ctrl+C", flush=True)

        while True:
            distance = measure_distance(GPIO)
            if distance is None:
                print("측정 실패: 응답 없음 또는 측정 범위 밖", flush=True)
            else:
                print(f"거리: {distance:.1f} cm", flush=True)
            if detector:
                event = detector.update(distance)
                if event:
                    print(f"{event}: {distance:.1f} cm", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n측정 종료")
    except (RuntimeError, OSError) as exc:
        print(f"GPIO 오류: {exc}")
        return 1
    finally:
        if configured_pins:
            GPIO.cleanup(configured_pins)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
