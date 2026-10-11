import unittest
from unittest.mock import Mock, patch

from distance_sensor import ProximityDetector, measure_distance


class ProximityTests(unittest.TestCase):
    def setUp(self):
        # 테스트용 입력값이며 실제 설치 환경의 감지 기준과 무관하다.
        self.detector = ProximityDetector(30, 40)

    def feed(self, values):
        return [self.detector.update(value) for value in values]

    def test_one_event_per_approach_and_rearm_after_leaving(self):
        self.assertEqual(self.feed([30, 29, 28, 20, 25]),
                         [None, None, "APPROACH", None, None])
        self.assertEqual(self.feed([40, 45, 50]), [None, None, "CLEAR"])
        self.assertEqual(self.feed([30, 30, 30]), [None, None, "APPROACH"])

    def test_single_spike_and_middle_range_do_not_change_state(self):
        self.assertEqual(self.feed([20, 50, 20, 35, 20, 35]), [None] * 6)
        self.feed([20, 20, 20])
        self.assertEqual(self.feed([39, 40, 39, 40, 39]), [None] * 5)
        self.assertTrue(self.detector.active)

    def test_invalid_reading_breaks_sequence_without_clearing_presence(self):
        self.assertEqual(self.feed([20, 20, None, 20]), [None] * 4)
        self.feed([20, 20])
        self.assertTrue(self.detector.active)
        self.assertEqual(self.feed([40, 40, None, float("nan"), 0, 401, 40]),
                         [None] * 7)
        self.assertTrue(self.detector.active)

    def test_invalid_thresholds_are_rejected(self):
        for near, far in [(40, 30), (30, 30), (1, 20), (30, 401), (float("nan"), 40)]:
            with self.subTest(near=near, far=far), self.assertRaises(ValueError):
                ProximityDetector(near, far)


class MeasurementTests(unittest.TestCase):
    @patch("distance_sensor.time.sleep")
    @patch("distance_sensor.time.monotonic")
    def test_pulse_is_converted_to_centimeters(self, clock, sleep):
        gpio = Mock()
        gpio.input.side_effect = [0, 1, 1, 0]
        clock.side_effect = [0, 0.001, 0.0015, 0.002]
        self.assertAlmostEqual(measure_distance(gpio), 17.15)

    @patch("distance_sensor.time.sleep")
    @patch("distance_sensor.time.monotonic")
    def test_missing_echo_times_out(self, clock, sleep):
        gpio = Mock()
        gpio.input.return_value = 0
        clock.side_effect = [0, 0.031]
        self.assertIsNone(measure_distance(gpio))

    @patch("distance_sensor.time.sleep")
    @patch("distance_sensor.time.monotonic")
    def test_echo_stuck_high_after_trigger_times_out(self, clock, sleep):
        gpio = Mock()
        gpio.input.side_effect = [0, 1, 1]
        clock.side_effect = [0, 0.001, 0.032]
        self.assertIsNone(measure_distance(gpio))

    def test_already_high_echo_skips_trigger(self):
        gpio = Mock()
        gpio.input.return_value = 1
        self.assertIsNone(measure_distance(gpio))
        gpio.output.assert_not_called()


if __name__ == "__main__":
    unittest.main()
