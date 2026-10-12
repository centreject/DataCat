import unittest

from gate import visitor_present


def reader(values):
    values = list(values)
    return lambda: values.pop(0)


class GateTests(unittest.TestCase):
    def check(self, values):
        return visitor_present(reader(values), release_cm=60, sleep=lambda _: None)

    def test_visitor_still_near(self):
        self.assertTrue(self.check([30, 32, 31, 30, 29]))

    def test_visitor_left(self):
        self.assertFalse(self.check([120, 150, 130, 140, 135]))

    def test_majority_of_valid_readings_decides(self):
        self.assertTrue(self.check([30, 90, 30, None, None]))
        self.assertFalse(self.check([30, 90, 90, None, None]))
        self.assertFalse(self.check([30, 90, None, None, None]))  # 동률은 이탈

    def test_all_failures_count_as_left(self):
        self.assertFalse(self.check([None] * 5))

    def test_release_distance_is_not_near(self):
        self.assertFalse(self.check([60] * 5))

    def test_waits_between_readings(self):
        waits = []
        visitor_present(reader([30] * 5), 60, attempts=5, interval=0.06, sleep=waits.append)
        self.assertEqual(waits, [0.06] * 4)


if __name__ == "__main__":
    unittest.main()
