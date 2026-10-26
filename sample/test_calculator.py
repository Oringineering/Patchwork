import unittest
from calculator import average


class AverageTests(unittest.TestCase):
    def test_whole_number(self):
        self.assertEqual(average([2, 4, 6]), 4)

    def test_fractional_result(self):
        self.assertEqual(average([1, 2]), 1.5)

    def test_negative_numbers(self):
        self.assertEqual(average([-2, -1]), -1.5)

