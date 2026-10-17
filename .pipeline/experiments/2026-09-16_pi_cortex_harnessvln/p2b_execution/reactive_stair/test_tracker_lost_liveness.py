from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from moving_cluster_core import (CloudFrame, MovingClusterTracker, PoseObservation,
                                 TerrainSupport)

NS = 1_000_000_000


def points(center_x):
    return tuple((center_x + dx, 1.0 + dy, z)
                 for dx in (-0.10, 0.0, 0.10) for dy in (-0.08, 0.08)
                 for z in (0.45, 0.8, 1.2, 1.55))


class LostConfirmedTrackLimitTest(unittest.TestCase):
    def test_lost_confirmed_cluster_never_silently_clears(self):
        terrain = TerrainSupport(
            "world", NS, "pinned_pct_fixture", 0.1, 0.0, 0.0,
            {(x, y): (0.0,) for x in range(0, 51) for y in range(0, 51)},
        )
        tracker = MovingClusterTracker()

        def feed(index, values):
            stamp = NS + index * 100_000_000
            pose = PoseObservation(stamp, "world", "lidar", (0, 0, 0), (0, 0, 0, 1))
            return tracker.process(CloudFrame(stamp, "lidar", values), pose, terrain, stamp)

        self.assertFalse(feed(0, points(1.0)).complete)
        confirmed = feed(1, points(1.14))
        self.assertTrue(confirmed.complete)
        self.assertEqual(len(confirmed.tracks), 1)
        for index in range(2, 12):
            result = feed(index, ())
            self.assertFalse(result.complete)
            self.assertEqual(result.tracks, ())
            self.assertEqual(result.reason, "unresolved_or_lost_cluster")
        reappeared_after_gap = feed(12, points(1.20))
        self.assertFalse(reappeared_after_gap.complete)
        self.assertEqual(reappeared_after_gap.tracks, ())


if __name__ == "__main__":
    unittest.main()
