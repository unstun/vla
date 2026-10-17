import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ISAAC_RUNNER = HERE.parent / "isaac_runner"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "rviz_observer"))
sys.path.insert(0, str(ISAAC_RUNNER))

import aabb_hit_marker  # noqa: E402
import occupancy_audit  # noqa: E402
import qualify_stand_runner as qualify  # noqa: E402
import run_rviz_probe as probe  # noqa: E402
import scan_occupancy  # noqa: E402


class AabbHitMarkerTests(unittest.TestCase):
    def test_count_in_aabb_after_identity_transform(self):
        world = aabb_hit_marker.transform_points(
            [(0.0, 0.0, 0.0), (0.9, -4.4, 1.96), (10.0, 0.0, 0.0)],
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        )
        hits = aabb_hit_marker.count_in_aabb(
            world,
            (0.677, -4.609, 1.551),
            (1.097, -4.189, 2.371),
        )
        self.assertEqual(hits, 1)

    def test_load_setup_reads_frozen_box_aabb(self):
        setup_path = (
            HERE / "runs/stand_20260921T083849Z_livox_lidar/returned_artifacts/"
            "runner_output/unmapped_box_setup.json"
        )
        setup = aabb_hit_marker.load_setup(setup_path)
        self.assertEqual(setup["prim"], "/World/unmapped_box")
        self.assertAlmostEqual(setup["center_xyz_m"][0], 0.8870694587067134)
        self.assertLess(setup["min_xyz_m"][0], setup["max_xyz_m"][0])


class OccupancyHelperTests(unittest.TestCase):
    def test_helper_is_planner_only(self):
        script = scan_occupancy.assert_planner_only(scan_occupancy.helper_inner_script())
        self.assertIn("scan_planner_node", script)
        self.assertIn("cloud:=/quad_0/cloud", script)
        self.assertIn("robot_state_publisher", script)
        self.assertIn("rviz_replay_node", script)
        self.assertNotIn("closed_loop_controller", script)
        self.assertNotIn("clusterer", script.lower())
        self.assertNotIn("euclidean", script.lower())

    def test_rewrite_urdf_meshes_matches_native_review(self):
        urdf = (
            HERE.parent / "isaac_runner/assets/lite3_sensor_rig/urdf/"
            "lite3_pro_sensor_rig_real_with_interface.urdf"
        )
        rewritten = scan_occupancy.rewrite_urdf_meshes(urdf.read_text(), urdf)
        self.assertIn('filename="file://%s/meshes/torso.STL"' % urdf.parent, rewritten)
        self.assertNotIn('filename="./meshes/', rewritten)

    def test_occupancy_aabb_count_reuses_frozen_box(self):
        setup_path = (
            HERE / "runs/stand_20260921T083849Z_livox_lidar/returned_artifacts/"
            "runner_output/unmapped_box_setup.json"
        )
        setup = aabb_hit_marker.load_setup(setup_path)
        message = type("Cloud", (), {})()
        message.header = type("Header", (), {})()
        message.header.stamp = type("Stamp", (), {"sec": 1, "nanosec": 0})()
        message.header.frame_id = "world"
        message.point_step = 16
        message.width = 2
        message.height = 1
        import struct
        inside = struct.pack("<fff", 0.9, -4.4, 1.96) + b"\x00\x00\x00\x00"
        outside = struct.pack("<fff", 10.0, 0.0, 0.0) + b"\x00\x00\x00\x00"
        message.data = inside + outside
        record = occupancy_audit.occupancy_record(message, 1, setup)
        self.assertEqual(record["points"], 2)
        self.assertEqual(record["aabb_hits"], 1)
        self.assertEqual(record["aabb_xy_hits"], 1)
        self.assertEqual(record["aabb_z_hits"], 1)
        self.assertEqual(record["miss_class"], "overlap")
        self.assertAlmostEqual(record["xyz_min"][0], 0.9)
        self.assertAlmostEqual(record["xyz_max"][0], 10.0)
        self.assertAlmostEqual(record["xyz_median"][2], 1.96)
        self.assertTrue(record["detected"])
        empty = type("Cloud", (), {})()
        empty.header = message.header
        empty.point_step = 16
        empty.width = 0
        empty.height = 0
        empty.data = b""
        empty_record = occupancy_audit.occupancy_record(empty, 2, setup)
        self.assertEqual(empty_record["points"], 0)
        self.assertEqual(empty_record["miss_class"], "empty")
        self.assertNotIn("xyz_min", empty_record)
        self.assertNotIn("xyz_max", empty_record)
        self.assertNotIn("xyz_median", empty_record)
        self.assertIsNone(occupancy_audit.load_setup_if_ready(HERE / "missing.json"))

    def test_occupancy_miss_class_splits_xy_and_z(self):
        setup = {
            "min_xyz_m": (0.677, -4.609, 1.551),
            "max_xyz_m": (1.097, -4.189, 2.371),
        }
        z_miss = occupancy_audit.miss_class(0, 12, 0, 100)
        xy_miss = occupancy_audit.miss_class(0, 0, 80, 100)
        both = occupancy_audit.miss_class(0, 0, 0, 100)
        self.assertEqual(z_miss, "z-band")
        self.assertEqual(xy_miss, "xy-range")
        self.assertEqual(both, "both")
        self.assertEqual(
            occupancy_audit.count_in_aabb_xy(
                [(0.9, -4.4, 0.3), (10.0, 0.0, 1.96)],
                setup["min_xyz_m"],
                setup["max_xyz_m"],
            ),
            1,
        )
        self.assertEqual(
            occupancy_audit.count_in_aabb_z(
                [(0.9, -4.4, 0.3), (10.0, 0.0, 1.96)],
                setup["min_xyz_m"],
                setup["max_xyz_m"],
            ),
            1,
        )


class RvizProbeHookTests(unittest.TestCase):
    def test_qualify_worker_anchors_are_unique(self):
        worker = qualify.remote_worker_source()
        updated = probe.add_observer_hooks(worker)
        self.assertIn("from observer.session import DisplayProbe", updated)
        self.assertIn("from observer.scan_occupancy import ScanOccupancy", updated)
        self.assertIn("probe.start()", updated)
        self.assertIn("scan_occ.start()", updated)
        self.assertIn('"--ipc=host"', updated)
        self.assertIn('probe.record_process("isaac", runner_proc.pid)', updated)
        self.assertIn('result["observer"] = probe.stop()', updated)
        self.assertIn('result["scan_occupancy"] = scan_occ.stop()', updated)
        self.assertEqual(updated.count("probe.start()"), 1)
        self.assertEqual(updated.count("scan_occ.start()"), 1)
        self.assertNotIn("closed_loop_controller", updated)

    def test_prepare_copies_observer_and_rsync_whitelist(self):
        run_id = "stand_unit_livox_rviz"
        with tempfile.TemporaryDirectory() as tmp:
            original_runs = probe.HERE
            try:
                # prepare() writes under HERE/runs; point it at the temp dir.
                probe.HERE = Path(tmp)
                (Path(tmp) / "rviz_observer").mkdir()
                for name in probe.OBSERVER_EXTRA:
                    source = HERE / "rviz_observer" / name
                    target = Path(tmp) / "rviz_observer" / name
                    target.write_bytes(source.read_bytes())
                (local_run, commands), args = probe.prepare("rviz-gpu", run_id, qualify)
            finally:
                probe.HERE = original_runs
            self.assertTrue((local_run / "observer/session.py").exists())
            self.assertTrue((local_run / "observer/aabb_hit_marker.py").exists())
            self.assertTrue((local_run / "observer/occupancy_audit.py").exists())
            self.assertTrue((local_run / "observer/scan_occupancy.py").exists())
            self.assertTrue((local_run / "config/planner.yaml").exists())
            self.assertTrue((local_run / "inputs/scan_04_identity.json").exists())
            self.assertTrue((local_run / "inputs/sensor_rig/meshes/torso.STL").exists())
            self.assertTrue((local_run / ("observer/pointcloud_%s.rviz" % run_id)).exists())
            self.assertIn("--include=/observer/***", commands["sync"])
            worker = (local_run / "remote_worker.py").read_text()
            self.assertIn("probe.start()", worker)
            self.assertIn("scan_occ.start()", worker)
            self.assertIn('"--ipc=host"', worker)
            self.assertNotIn("closed_loop_controller", worker)
            session = (local_run / "observer/session.py").read_text()
            self.assertIn("occupancy_audit.py", session)
            self.assertIn("/run-artifacts:ro", session)
            self.assertIn("/robot:ro", session)
            rviz = (local_run / ("observer/pointcloud_%s.rviz" % run_id)).read_text()
            self.assertIn("rviz_default_plugins/RobotModel", rviz)
            self.assertIn("/robot_description", rviz)
            self.assertIn("/grid_map/occupancy", rviz)
            self.assertIn("Raw SCAN Occupancy", rviz)
            self.assertNotIn("SCAN Planned Path", rviz)
            config = json.loads((local_run / "observer/config.json").read_text())
            self.assertEqual(config["mode"], "rviz-gpu")
            self.assertEqual(config["capture_encoder"], "h264_nvenc")
            self.assertEqual(config["pointcloud_topic"], "/quad_0/cloud_raw")
            self.assertEqual(config["occupancy_topic"], "/grid_map/occupancy")
            self.assertEqual(
                config["scan_workspace"],
                "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04",
            )
            planner = (local_run / "config/planner.yaml").read_text()
            self.assertIn("ground_height: 0.0", planner)
            self.assertIn("cloud_is_world: false", planner)
            request = json.loads((local_run / "run_request.json").read_text())
            self.assertEqual(request["lidar_pattern_mode"], "livox_mid360")
            self.assertEqual(request["unmapped_box"], "lidar")
            self.assertEqual(request["duration_seconds"], 20.0)
            self.assertIn("Occupancy visualization", request["claim_boundary"])
            self.assertIn("does not amend 09-20 AC1", request["claim_boundary"])
            prepared = qualify.check_prepared_request(args, local_run)
            self.assertEqual(prepared["lidar_pattern_mode"], "livox_mid360")


if __name__ == "__main__":
    unittest.main()
