"""Current-frame foreground and fail-closed coverage regression cases."""
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moving_cluster_core import CloudFrame, MovingClusterTracker, PoseObservation, TerrainSupport, TrackerParameters
from static_background import StaticBackgroundIndex, load_building_background
from static_foreground_tracker import StaticForegroundTracker

NS = 1_000_000_000


def person(x, y):
    return [(x + dx, y + dy, z) for dx in (-.10, 0, .10)
            for dy in (-.08, .08) for z in (.45, .8, 1.2, 1.55)]


class StaticForegroundTests(unittest.TestCase):
    def setUp(self):
        self.floor = [(x, y, 0.0) for x in np.linspace(.2, 3.8, 24) for y in np.linspace(.2, 2.8, 24)]
        self.background = StaticBackgroundIndex(self.floor, "test_static_floor")
        self.terrain = TerrainSupport("world", NS, "physical_ground_fixture", .1, 0, 0,
                                      {(x, y): (0.0,) for x in range(51) for y in range(51)})

    def frame(self, index, points, offset=(0, 0, 0)):
        stamp = NS + index * 100_000_000
        pose = PoseObservation(stamp, "world", "lidar", offset, (0, 0, 0, 1))
        cloud = CloudFrame(stamp, "lidar", tuple(self.floor + points))
        return cloud, pose, stamp

    def test_measured_foreground_tracks_and_then_stands_without_prediction(self):
        tracker = StaticForegroundTracker(self.background)
        ids = set()
        for i in range(12):
            x = 1.5 + min(i, 5) * .03
            cloud, pose, now = self.frame(i, person(x, 1.5))
            original = copy.deepcopy(cloud)
            result = tracker.process(cloud, pose, self.terrain, now)
            self.assertEqual(cloud, original)  # Navigation may retain this same raw input.
            if i >= 3:
                self.assertTrue(result.complete)
                self.assertEqual(len(result.tracks), 1)
                self.assertAlmostEqual(result.tracks[0].center[0], x, places=6)
                self.assertEqual(result.tracks[0].stamp_ns, now)
                ids.add(result.tracks[0].id)
        self.assertEqual(ids, {"cluster-1"})

    def test_static_scene_and_static_person_do_not_create_moving_tracks(self):
        for extra in ([], person(1.5, 1.5)):
            tracker = StaticForegroundTracker(self.background)
            for i in range(5):
                cloud, pose, now = self.frame(i, extra)
                result = tracker.process(cloud, pose, self.terrain, now)
                self.assertEqual(result.tracks, ())
                if i >= 2:
                    self.assertTrue(result.complete)

    def test_missing_foreground_ground_cannot_become_complete_empty(self):
        terrain = TerrainSupport("world", NS, "incomplete_ground_fixture", .1, 0, 0,
                                 {(x, y): (0.0,) for x in range(51) for y in range(51)
                                  if not (12 <= x <= 18 and 12 <= y <= 18)})
        cloud, pose, now = self.frame(0, person(1.5, 1.5))
        self.assertTrue(MovingClusterTracker().process(cloud, pose, terrain, now).complete)
        result = StaticForegroundTracker(self.background).process(cloud, pose, terrain, now)
        self.assertFalse(result.complete)
        self.assertEqual(result.reason, "foreground_ground_coverage_missing")

    def test_map_missing_or_misaligned_fails_closed(self):
        cloud, pose, now = self.frame(0, person(1.5, 1.5))
        self.assertFalse(StaticForegroundTracker(None).process(cloud, pose, self.terrain, now).complete)
        wrong_pose = PoseObservation(now, "world", "lidar", (20, 0, 0), (0, 0, 0, 1))
        result = StaticForegroundTracker(self.background).process(cloud, wrong_pose, self.terrain, now)
        self.assertFalse(result.complete)
        self.assertEqual(result.reason, "static_background_alignment_missing")

    def test_stale_mismatched_nonfinite_and_oversize_raw_inputs_fail(self):
        cloud, pose, now = self.frame(0, person(1.5, 1.5))
        tracker = StaticForegroundTracker(self.background)
        self.assertFalse(tracker.process(cloud, pose, self.terrain, now + 300_000_000).complete)
        bad_pose = PoseObservation(now + 1, "world", "lidar", (0, 0, 0), (0, 0, 0, 1))
        self.assertFalse(tracker.process(cloud, bad_pose, self.terrain, now).complete)
        bad_cloud = CloudFrame(now, "lidar", ((math.nan, 0, 0),))
        self.assertFalse(tracker.process(bad_cloud, pose, self.terrain, now).complete)
        small = StaticForegroundTracker(self.background, TrackerParameters(max_points=10))
        self.assertFalse(small.process(cloud, pose, self.terrain, now).complete)

    def test_lost_confirmed_foreground_stays_incomplete(self):
        tracker = StaticForegroundTracker(self.background)
        for i in range(4):
            cloud, pose, now = self.frame(i, person(1.5 + i * .04, 1.5))
            result = tracker.process(cloud, pose, self.terrain, now)
        self.assertTrue(result.complete)
        self.assertEqual(len(result.tracks), 1)
        cloud, pose, now = self.frame(4, [])
        result = tracker.process(cloud, pose, self.terrain, now)
        self.assertFalse(result.complete)
        self.assertEqual(result.tracks, ())

    def test_world_transform_used_for_static_match(self):
        q = (0, 0, math.sin(math.pi / 4), math.cos(math.pi / 4))
        pose = PoseObservation(NS, "world", "lidar", (1, 1, 0), q)
        world = np.array(self.floor)
        local = np.column_stack((world[:, 1] - 1, -(world[:, 0] - 1), world[:, 2]))
        selected = self.background.select(CloudFrame(NS, "lidar", local.tolist()), pose, TrackerParameters())
        self.assertEqual(len(selected.cloud.points), 0)
        self.assertEqual(selected.matched_fraction, 1.0)

    def test_pinned_loader_rejects_missing_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "map.pcd"
            with self.assertRaises(OSError):
                load_building_background(path)
            path.write_bytes(b"not the pinned static map")
            with self.assertRaises(ValueError):
                load_building_background(path)


if __name__ == "__main__":
    unittest.main()
