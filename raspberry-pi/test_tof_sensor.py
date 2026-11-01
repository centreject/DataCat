import unittest

from distance_sensor import ProximityDetector
from gate import visitor_present
from tof_sensor import TOF_MAX_MM, TofSensor


class FakeVl53l0x:
    def __init__(self, values):
        self.values = iter(values)

    @property
    def range(self):
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return value


class TofSensorTests(unittest.TestCase):
    def sensor(self, values):
        return TofSensor(device=FakeVl53l0x(values))

    def test_converts_mm_to_cm(self):
        self.assertEqual(self.sensor([523]).read_cm(), 52.3)

    def test_no_target_is_far_not_failure(self):
        sensor = self.sensor([8190])
        self.assertEqual(sensor.read_cm(), TOF_MAX_MM / 10)
        self.assertEqual(sensor.last_mm, 8190)

    def test_io_error_and_timeout_are_failures(self):
        sensor = self.sensor([OSError(121, "Remote I/O error"),
                              RuntimeError("Timeout waiting for VL53L0X!")])
        self.assertIsNone(sensor.read_cm())
        self.assertIsNone(sensor.read_cm())
        self.assertIsNone(sensor.last_mm)

    def test_too_close_is_failure(self):
        self.assertIsNone(self.sensor([10]).read_cm())

    def test_clear_after_visitor_leaves_empty_doorway(self):
        # 감지 30cm / 해제 40cm, 사람이 떠난 뒤 센서가 범위 밖 값을 낼 때 CLEAR가 나와야 한다.
        sensor = self.sensor([250, 240, 260, 8190, 8191, 8190])
        detector = ProximityDetector(30, 40)
        events = [detector.update(sensor.read_cm()) for _ in range(6)]
        self.assertEqual(events, [None, None, "APPROACH", None, None, "CLEAR"])

    def test_gate_sees_empty_doorway_as_left(self):
        sensor = self.sensor([8190] * 5)
        self.assertFalse(visitor_present(sensor.read_cm, 40, sleep=lambda _: None))


if __name__ == "__main__":
    unittest.main()
