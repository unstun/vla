import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moving_cluster_core import (CloudFrame, MovingClusterTracker, PoseObservation,
                                 TerrainSupport, rotate_by_quaternion)

NS = 1_000_000_000


def terrain():
    cells = {(x, y): (0.0,) for x in range(0, 51) for y in range(0, 51)}
    return TerrainSupport("world", NS, "pct_selected_ground_fixture", 0.1, 0.0, 0.0, cells)


def pose(stamp_ns, frame="world", child="lidar"):
    return PoseObservation(stamp_ns, frame, child, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))


def cluster(cx, cy, ground=0.0):
    return tuple(
        (cx + dx, cy + dy, ground + height)
        for dx in (-0.10, 0.0, 0.10)
        for dy in (-0.08, 0.08)
        for height in (0.45, 0.8, 1.2, 1.55)
    )


def cloud(stamp_ns, points, frame="lidar", complete=True):
    return CloudFrame(stamp_ns, frame, tuple(points), complete)


class MovingClusterTest(unittest.TestCase):
    def test_slow_current_motion_accumulates_from_first_observation(self):
        tracker, ground = MovingClusterTracker(), terrain()
        confirmed = []
        for index in range(11):
            stamp = NS + index * 100_000_000
            observed_x = 1.0 + 0.03 * index
            result = tracker.process(cloud(stamp, cluster(observed_x, 1.0)),
                                     pose(stamp), ground, stamp)
            if result.tracks:
                self.assertTrue(result.complete)
                self.assertEqual(len(result.tracks), 1)
                self.assertEqual(result.tracks[0].stamp_ns, stamp)
                self.assertAlmostEqual(result.tracks[0].center[0], observed_x, places=2)
                confirmed.append((index, result.tracks[0].id))
        self.assertEqual(confirmed[0][0], 3)
        self.assertEqual({track_id for _, track_id in confirmed}, {"cluster-1"})
        self.assertEqual(confirmed[-1][0], 10)

    def test_static_cluster_jitter_does_not_accumulate_motion(self):
        tracker, ground = MovingClusterTracker(), terrain()
        jitter = ((0.0, 0.0), (0.02, -0.01), (-0.02, 0.02),
                  (0.025, -0.015), (-0.025, 0.0), (0.01, 0.015))
        for index, (dx, dy) in enumerate(jitter):
            stamp = NS + index * 100_000_000
            result = tracker.process(cloud(stamp, cluster(2.0 + dx, 2.0 + dy)),
                                     pose(stamp), ground, stamp)
            self.assertEqual(result.tracks, ())
            if index >= 2:
                self.assertTrue(result.complete)

    def test_moving_cluster_keeps_identity_and_current_only(self):
        tracker, ground = MovingClusterTracker(), terrain()
        first = tracker.process(cloud(NS, cluster(1.0, 1.0)), pose(NS), ground, NS)
        self.assertFalse(first.complete)  # one scan cannot establish motion
        self.assertEqual(first.tracks, ())
        second_stamp = NS + 100_000_000
        second = tracker.process(cloud(second_stamp, cluster(1.14, 1.0)),
                                 pose(second_stamp), ground, second_stamp)
        self.assertTrue(second.complete)
        self.assertEqual(len(second.tracks), 1)
        track_id = second.tracks[0].id
        self.assertAlmostEqual(second.tracks[0].center[0], 1.14, places=2)
        third_stamp = NS + 200_000_000
        third = tracker.process(cloud(third_stamp, cluster(1.27, 1.0)),
                                pose(third_stamp), ground, third_stamp)
        self.assertTrue(third.complete)
        self.assertEqual(third.tracks[0].id, track_id)
        self.assertAlmostEqual(third.tracks[0].center[0], 1.27, places=2)
        self.assertEqual(third.tracks[0].stamp_ns, third_stamp)
        lost_stamp = NS + 300_000_000
        lost = tracker.process(cloud(lost_stamp, ()), pose(lost_stamp), ground, lost_stamp)
        self.assertFalse(lost.complete)
        self.assertEqual(lost.tracks, ())

    def test_static_box_rejected_after_stationary_observations(self):
        tracker, ground = MovingClusterTracker(), terrain()
        results = []
        for index in range(3):
            stamp = NS + index * 100_000_000
            results.append(tracker.process(cloud(stamp, cluster(2.0, 2.0)),
                                           pose(stamp), ground, stamp))
        self.assertFalse(results[0].complete)
        self.assertFalse(results[1].complete)
        self.assertTrue(results[2].complete)
        self.assertEqual(results[2].tracks, ())

    def test_stair_returns_are_not_person_clusters(self):
        tracker, ground = MovingClusterTracker(), terrain()
        stair = [(1.0 + dx, 1.0 + dy, z)
                 for dx in (-0.1, 0.0, 0.1) for dy in (-0.1, 0.1)
                 for z in (0.04, 0.12, 0.22)]
        result = tracker.process(cloud(NS, stair), pose(NS), ground, NS)
        self.assertTrue(result.complete)
        self.assertEqual(result.tracks, ())

    def test_missing_stale_incomplete_and_mismatched_inputs_fail_closed(self):
        ground = terrain()
        tracker = MovingClusterTracker()
        self.assertFalse(tracker.process(cloud(NS, ()), None, ground, NS).complete)
        self.assertFalse(tracker.process(cloud(NS, ()), pose(NS), None, NS).complete)
        self.assertFalse(tracker.process(cloud(NS, ()), pose(NS), ground,
                                         NS + 300_000_000).complete)
        late = NS + 86_401 * NS
        self.assertFalse(tracker.process(cloud(late, ()), pose(late), ground,
                                         late).complete)
        self.assertFalse(tracker.process(cloud(NS, ()), pose(NS + 1), ground, NS).complete)
        self.assertFalse(tracker.process(cloud(NS, (), frame="other"),
                                         pose(NS), ground, NS).complete)
        self.assertFalse(tracker.process(cloud(NS, (), complete=False),
                                         pose(NS), ground, NS).complete)
        self.assertFalse(tracker.process(cloud(NS, ()), pose(NS, frame="odom"),
                                         ground, NS).complete)
        self.assertFalse(tracker.process(cloud(NS, ()),
                                         PoseObservation(NS, "world", "lidar", (0, 0, 0),
                                                         (0, 0, 0, 0)), ground, NS).complete)
        valid = tracker.process(cloud(NS, ()), pose(NS), ground, NS)
        self.assertTrue(valid.complete)
        self.assertFalse(tracker.process(cloud(NS, ()), pose(NS), ground, NS).complete)

    def test_sensor_to_world_rotation_and_multilevel_ground(self):
        q = (0.0, 0.0, math.sin(math.pi/4), math.cos(math.pi/4))
        rotated = rotate_by_quaternion((1.0, 0.0, 1.0), q)
        self.assertAlmostEqual(rotated[0], 0.0, places=6)
        self.assertAlmostEqual(rotated[1], 1.0, places=6)
        ground = terrain()
        ground.heights[(10, 10)] = (0.0, 1.0)
        self.assertEqual(ground.ground_below(1.05, 1.05, 1.6), 1.0)


if __name__ == "__main__":
    unittest.main()
