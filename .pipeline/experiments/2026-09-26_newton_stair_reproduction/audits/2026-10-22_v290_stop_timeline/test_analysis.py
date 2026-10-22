"""Checks for measurement definitions, independent of particular route outcomes."""
import math
import unittest
from analyze import angle, displacement, is_zero, yaw


class MeasurementTests(unittest.TestCase):
    def test_displacement_is_not_difference_of_goal_distances(self):
        a = {'body': {'position': [1., 0., 10.]}}
        b = {'body': {'position': [0., 1., 20.]}}
        self.assertAlmostEqual(displacement(a, b), math.sqrt(2))
        # Both have distance 1 to the goal, but the body did move.
        self.assertNotEqual(displacement(a, b), 0)

    def test_zero_includes_yaw(self):
        self.assertFalse(is_zero([0., 0., .15]))
        self.assertTrue(is_zero([0., 0., 0.]))

    def test_quaternion_convention_and_angle_wrap(self):
        self.assertAlmostEqual(yaw([math.sqrt(.5), 0., 0., math.sqrt(.5)]), math.pi/2)
        self.assertAlmostEqual(angle(-math.pi-.1), math.pi-.1)


if __name__ == '__main__':
    unittest.main()
