import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "run_unmapped_box_avoid.py"
PLANNER = HERE.parent / "p2b_execution/baseline_config/planner.yaml"
PINNED_PLANNER_SHA256 = "42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e"


def load_module():
    spec = importlib.util.spec_from_file_location("run_unmapped_box_avoid", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AvoidLauncherTests(unittest.TestCase):
    def setUp(self):
        self.m = load_module()

    def test_runner_argv_uses_livox_and_lidar_box(self):
        argv = self.m.build_avoid_runner_argv(
            self.m.avoid_args(),
            "/remote/avoid_run",
            "avoid_run",
            json.loads((HERE.parent / "p2b_execution/inputs/pilot.json").read_text()),
        )
        self.assertEqual(argv[argv.index("--unmapped-box") + 1], "lidar")
        self.assertEqual(argv[argv.index("--lidar-pattern-mode") + 1], "livox_mid360")
        self.assertIn("/remote/avoid_run/inputs/livox_mid360/mid360.csv", argv)

    def test_driver_posts_goal_b_once_and_does_not_cancel(self):
        source = self.m.driver_source()
        self.assertEqual(source.count('post_json(base, "/goal"'), 1)
        self.assertIn('pilot["goals"][1]', source)
        self.assertNotIn("goal-a", source)
        self.assertNotIn('"/cancel"', source)

    def test_source_planner_yaml_hash_is_the_pinned_file(self):
        digest = hashlib.sha256(PLANNER.read_bytes()).hexdigest()
        self.assertEqual(digest, PINNED_PLANNER_SHA256)
        self.assertEqual(self.m.pinned_planner_sha256(), PINNED_PLANNER_SHA256)

    def test_straight_segment_through_a_rectangle_counts_as_crossing(self):
        box = {"min_xyz_m": (0.0, 0.0, 0.0), "max_xyz_m": (1.0, 1.0, 1.0)}
        self.assertTrue(self.m.route_xy_crosses_box([(-1.0, 0.5, 0.0), (2.0, 0.5, 0.0)], box))
        self.assertFalse(self.m.route_xy_crosses_box([(-1.0, 2.0, 0.0), (2.0, 2.0, 0.0)], box))

    def test_torso_sample_inside_the_box_is_overlap(self):
        box = {"min_xyz_m": (0.0, 0.0, 0.0), "max_xyz_m": (1.0, 1.0, 2.0)}
        self.assertTrue(self.m.torso_intersects_box((0.2, 0.2, 0.35), 0.0, 0.35, box))
        self.assertFalse(self.m.torso_intersects_box((10.0, 10.0, 0.35), 0.0, 0.35, box))

    def test_episode_verdict_requires_cross_clearance_and_arrival(self):
        box = {"min_xyz_m": (0.0, 0.0, 0.0), "max_xyz_m": (1.0, 1.0, 2.0)}
        passed = self.m.episode_verdict(
            waypoints=[(-1.0, 0.5, 0.0), (2.0, 0.5, 0.0)],
            samples=[((10.0, 0.5, 0.35), 0.0), ((3.0, 0.5, 0.35), 0.0)],
            goal_xyz=(3.0, 0.5, 0.0),
            box_aabb=box,
            body_height_m=0.35,
            xy_tolerance_m=0.25,
        )
        self.assertEqual(passed["status"], "pass")
        missed = self.m.episode_verdict(
            waypoints=[(-1.0, 2.0, 0.0), (2.0, 2.0, 0.0)],
            samples=[((0.2, 0.2, 0.35), 0.0)],
            goal_xyz=(3.0, 0.5, 0.0),
            box_aabb=box,
            body_height_m=0.35,
            xy_tolerance_m=0.25,
        )
        self.assertEqual(missed["status"], "fail")
        self.assertFalse(missed["route_crosses_box"])
        self.assertTrue(missed["torso_overlap"])
