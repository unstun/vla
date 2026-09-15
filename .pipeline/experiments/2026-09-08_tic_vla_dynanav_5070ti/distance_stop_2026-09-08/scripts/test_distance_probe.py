"""Tests that distinguish measured metric stopping from endpoint/command artifacts."""
import unittest

from distance_probe import DistanceMeter, INSTRUCTION, sustained_stop_windows
from protocol import parse_command


class DistanceProbeTests(unittest.TestCase):
    def test_instruction_remains_chinese_and_numeric(self):
        self.assertEqual(parse_command(INSTRUCTION)['instruction'], INSTRUCTION)

    def test_rotated_frame_and_path_differ(self):
        from math import sqrt
        meter = DistanceMeter()
        meter.start([10, 20, 0], [sqrt(.5), 0, 0, sqrt(.5)], 4, 120)
        a = meter.sample([9, 21, 0], [1, 0, 0], 0, [1, 0], [1, 0], 5, 150, True)
        self.assertAlmostEqual(a['forward_m'], 1)
        self.assertAlmostEqual(a['lateral_m'], 1)
        b = meter.sample([10, 23, 0], [0, 0, 0], 0, [0, 0], [0, 0], 6, 180, True)
        self.assertAlmostEqual(b['forward_m'], 3)
        self.assertAlmostEqual(b['lateral_m'], 0)
        self.assertGreater(b['sampled_path_length_m'], b['forward_m'])
        self.assertTrue(b['qualifying_stop_sample'])

    def test_no_false_stop_from_collision_hold_or_wrong_position(self):
        meter = DistanceMeter()
        meter.start([0, 0, 0], [1, 0, 0, 0], 0, 0)
        for position, desired, normal in [([3, 0, 0], [1, 0], True),
                                          ([3, 0, 0], [0, 0], False),
                                          ([0, 0, 0], [0, 0], True),
                                          ([3, 1, 0], [0, 0], True)]:
            sample = meter.sample(position, [0, 0, 0], 0, desired, [0, 0], 1, 30, normal)
            self.assertFalse(sample['qualifying_stop_sample'])

    def test_stop_requires_continuous_two_seconds(self):
        samples = [{'timeline_seconds': i / 10, 'qualifying_stop_sample': True} for i in range(22)]
        self.assertEqual(len(sustained_stop_windows(samples)), 1)
        self.assertEqual(sustained_stop_windows(samples[:20]), [])
        samples[10]['qualifying_stop_sample'] = False
        self.assertEqual(sustained_stop_windows(samples), [])
        gap = [{'timeline_seconds': 0, 'qualifying_stop_sample': True},
               {'timeline_seconds': 3, 'qualifying_stop_sample': True}]
        self.assertEqual(sustained_stop_windows(gap), [])


if __name__ == '__main__':
    unittest.main()
