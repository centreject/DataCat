"""VL53L0X ToF 거리 측정(I2C). distance_sensor의 ProximityDetector와 gate에 cm 값을 넘긴다."""

TOF_MAX_MM = 1200   # 기본 측정 모드의 유효 거리. 이보다 먼 값은 "대상 없음"으로 본다.
TOF_MIN_MM = 30     # 이보다 가까운 값은 신뢰하지 않는다.
IO_TIMEOUT_S = 0.5  # 라이브러리 기본값 0은 무한 대기라 응답이 끊기면 프로그램이 멈춘다.


class TofSensor:
    """측정 결과를 HC-SR04의 measure_distance와 같은 의미로 바꾼다.

    - 앞이 비어 있으면 센서는 8190mm 근처를 준다. 측정 실패(None)로 두면
      ProximityDetector가 이탈을 확인하지 못하므로 최대 거리(TOF_MAX_MM)로 바꾼다.
    - I2C 오류와 응답 지연만 측정 실패(None)다.
    """

    def __init__(self, device=None, max_mm=TOF_MAX_MM):
        if device is None:
            import board
            import adafruit_vl53l0x
            device = adafruit_vl53l0x.VL53L0X(board.I2C(), io_timeout_s=IO_TIMEOUT_S)
        self.device = device
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
