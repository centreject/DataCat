"""ToF 거리 측정(I2C). distance_sensor의 ProximityDetector와 gate에 cm 값을 넘긴다.

센서는 DATACAT_TOF로 고른다.
- l5cx (기본): VL53L5CX. 8x8 구역 중 유효한 구역의 가장 가까운 거리를 쓴다.
  시작할 때 펌웨어(약 86KB)를 I2C로 올리므로 초기화가 I2C 100kHz에서 약 24초 걸린다.
- l0x: 이전 VL53L0X (adafruit_vl53l0x)
"""

import os
import time

TOF_MAX_MM = 1200   # 이보다 먼 값과 "대상 없음"은 이 값으로 본다.
TOF_MIN_MM = 30     # 이보다 가까운 값은 신뢰하지 않는다.
IO_TIMEOUT_S = 0.5  # VL53L0X 라이브러리 기본값 0은 무한 대기라 응답이 끊기면 프로그램이 멈춘다.

# 8x8. qwiic_vl53l5cx 2.0.0은 4x4(16)로 바꾸면 데이터가 오지 않는다(11/22 확인).
# I2C 100kHz에서는 15Hz로 설정해도 실제로 초당 약 2.7회 읽힌다. 새 값이 없으면 이전 값을 준다.
L5CX_RESOLUTION = 64
L5CX_FREQUENCY_HZ = 15
L5CX_VALID_STATUS = (5, 9)  # 라이브러리 설명: 5, 9만 측정 정상
L5CX_STALE_S = 2.0        # 새 측정이 이 시간 넘게 없으면 측정 실패(None)


class L5cxDevice:
    """VL53L5CX를 VL53L0X 라이브러리처럼 .range(mm)로 읽게 감싼다.

    유효한 구역이 하나도 없으면 앞이 비어 있는 것으로 보고 8190을 준다(VL53L0X와 같은 의미).
    """

    NO_TARGET_MM = 8190

    def __init__(self):
        import qwiic_vl53l5cx
        data_path = os.path.join(os.path.dirname(qwiic_vl53l5cx.__file__), "vl53l5cx_bin")
        self.sensor = qwiic_vl53l5cx.QwiicVL53L5CX(dataPath=data_path)
        if not self.sensor.is_connected():
            raise ValueError("I2C 0x29에 VL53L5CX가 없습니다.")
        if not self.sensor.begin():
            raise RuntimeError("VL53L5CX 초기화(펌웨어 업로드) 실패")
        self.sensor.set_resolution(L5CX_RESOLUTION)
        self.sensor.set_ranging_frequency_hz(L5CX_FREQUENCY_HZ)
        self.sensor.start_ranging()
        self.last_mm = self.NO_TARGET_MM
        self.last_at = time.monotonic()

    @property
    def range(self):
        if self.sensor.check_data_ready():
            data = self.sensor.get_ranging_data()
            valid = [d for d, s in zip(data.distance_mm[:L5CX_RESOLUTION],
                                       data.target_status[:L5CX_RESOLUTION])
                     if s in L5CX_VALID_STATUS and d >= TOF_MIN_MM]
            self.last_mm = min(valid) if valid else self.NO_TARGET_MM
            self.last_at = time.monotonic()
        elif time.monotonic() - self.last_at > L5CX_STALE_S:
            raise OSError("VL53L5CX 측정이 멈췄습니다.")
        return self.last_mm

    def close(self):
        try:
            self.sensor.stop_ranging()
        except OSError:
            pass


def open_device(kind=None):
    kind = (kind or os.environ.get("DATACAT_TOF", "l5cx")).lower()
    if kind == "l0x":
        import board
        import adafruit_vl53l0x
        return adafruit_vl53l0x.VL53L0X(board.I2C(), io_timeout_s=IO_TIMEOUT_S)
    if kind == "l5cx":
        return L5cxDevice()
    raise ValueError(f"DATACAT_TOF는 l5cx 또는 l0x입니다: {kind}")


class TofSensor:
    """측정 결과를 HC-SR04의 measure_distance와 같은 의미로 바꾼다.

    - 앞이 비어 있으면 센서는 8190mm 근처를 준다. 측정 실패(None)로 두면
      ProximityDetector가 이탈을 확인하지 못하므로 최대 거리(TOF_MAX_MM)로 바꾼다.
    - I2C 오류와 응답 지연만 측정 실패(None)다.
    """

    def __init__(self, device=None, max_mm=TOF_MAX_MM):
        self.device = open_device() if device is None else device
        self.max_mm = max_mm
        self.last_mm = None  # 서버에 보낼 distanceMm용 원본 값

    def read_mm(self):
        try:
            distance = self.device.range
        except (OSError, RuntimeError):
            self.last_mm = None
            return None
        self.last_mm = distance
        if distance > self.max_mm:
            return self.max_mm
        return distance if distance >= TOF_MIN_MM else None

    def read_cm(self):
        distance = self.read_mm()
        return None if distance is None else distance / 10

    def close(self):
        close = getattr(self.device, "close", None)
        if close:
            close()
