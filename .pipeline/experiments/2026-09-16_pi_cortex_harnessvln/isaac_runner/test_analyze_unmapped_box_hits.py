import json
import tempfile
import unittest
from pathlib import Path

import analyze_unmapped_box_hits as analyzer
import unmapped_box as box


def write_run(root, name, rows, identity=None, mode="spawn"):
    out = Path(root) / name / "returned_artifacts/runner_output"
    out.mkdir(parents=True)
    (out / "clouds.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    pose = box.box_pose_from_stand((0.0, 0.0, 1.0), 0.0)
    record = identity or box.unmapped_box_identity(mode, (0.0, 0.0, 1.0), 0.0, 0.35)
    (out / "unmapped_box_setup.json").write_text(json.dumps(record))
    (out / "summary.json").write_text(json.dumps({
        "case": "stand_probe", "status": "EXTERNAL_EPISODE_FINISHED", "unmapped_box": record,
    }))
    return out.parents[1], pose


def scan(sim_time_s, points, scan_id=0, position=(0.0, 0.0, 1.4), quat=(1.0, 0.0, 0.0, 0.0),
         planner=None):
    row = {
        "scan_id": scan_id,
        "sim_time_s": sim_time_s,
        "sensor_position": list(position),
        "sensor_quaternion_wxyz": list(quat),
        "raw_points_sensor_frame": [list(point) for point in points],
    }
    if planner is not None:
        row["planner_points_sensor_frame"] = [list(point) for point in planner]
    return row


class UnmappedBoxAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_thresholds_are_frozen(self):
        loaded = analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS)
        self.assertEqual(loaded["sha256"], analyzer.FROZEN_THRESHOLDS_SHA256)
        self.assertTrue(loaded["frozen"])
        self.assertEqual(loaded["values"]["settle_s"], 1.0)
        self.assertEqual(loaded["values"]["aabb_pad_m"], 0.01)
        other = Path(self.tmp.name) / "other.json"
        other.write_text(json.dumps({"schema_version": 2}))
        with self.assertRaisesRegex(analyzer.AnalysisError, "not the frozen"):
            analyzer.load_thresholds(other)

    def test_ac1_spawn_zero_hits_after_settle(self):
        # A hit before settle must not fail AC1; planner-only points must not count.
        inside = (2.5, 0.0, 0.0)
        outside = (8.0, 0.0, 0.0)
        rows = [
            scan(0.5, [inside], scan_id=0, planner=[inside]),
            scan(1.0, [outside], scan_id=1, planner=[inside]),
            scan(1.2, [outside, outside], scan_id=2),
            scan(1.4, [], scan_id=3),
        ]
        run, _ = write_run(self.root, "spawn", rows, mode="spawn")
        report = analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))
        self.assertTrue(report["ac1"]["passed"])
        self.assertFalse(report["ac2"]["passed"])
        self.assertEqual(report["aabb_counts_after_settle"], [0, 0, 0])
        self.assertEqual(report["box"]["mode"], "spawn")
        self.assertEqual(analyzer.main([str(run), "--require", "ac1"]), 0)
        self.assertEqual(analyzer.main([str(run), "--require", "ac2"]), 1)

    def test_ac2_lidar_hits_and_median(self):
        inside = [(2.5, 0.0, 0.0)] * 10
        rows = [
            scan(0.2, [], scan_id=0),
            scan(1.0, inside, scan_id=1),
            scan(1.1, inside + [(2.48, 0.0, 0.0)], scan_id=2),
            scan(1.2, inside, scan_id=3),
        ]
        run, _ = write_run(self.root, "lidar", rows, mode="lidar")
        report = analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))
        self.assertFalse(report["ac1"]["passed"])
        self.assertTrue(report["ac2"]["passed"])
        self.assertGreaterEqual(report["median_aabb_count_after_settle"], 10)
        self.assertEqual(analyzer.main([str(run), "--require", "ac2"]), 0)
        self.assertEqual(analyzer.main([str(run), "--require", "ac1"]), 1)

    def test_ac2_fails_when_a_scan_is_empty_or_median_is_low(self):
        inside = [(2.5, 0.0, 0.0)] * 12
        rows = [
            scan(1.0, inside, scan_id=0),
            scan(1.1, [], scan_id=1),
            scan(1.2, inside, scan_id=2),
        ]
        run, _ = write_run(self.root, "lidar_gap", rows, mode="lidar")
        report = analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))
        self.assertFalse(report["ac2"]["passed"])
        self.assertFalse(report["ac2"]["every_scan_min"])

        low = [
            scan(1.0, [(2.5, 0.0, 0.0)] * 2, scan_id=0),
            scan(1.1, [(2.5, 0.0, 0.0)] * 2, scan_id=1),
            scan(1.2, [(2.5, 0.0, 0.0)] * 2, scan_id=2),
        ]
        run, _ = write_run(self.root, "lidar_low", low, mode="lidar")
        report = analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))
        self.assertTrue(report["ac2"]["every_scan_min"])
        self.assertFalse(report["ac2"]["median_min"])
        self.assertFalse(report["ac2"]["passed"])

    def test_refuses_planner_field_as_the_hit_source(self):
        inside = (2.5, 0.0, 0.0)
        rows = [scan(1.0, [(8.0, 0.0, 0.0)], scan_id=0, planner=[inside] * 20)]
        run, _ = write_run(self.root, "planner_only", rows, mode="lidar")
        report = analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))
        self.assertEqual(report["aabb_counts_after_settle"], [0])
        self.assertFalse(report["ac2"]["passed"])

    def test_refuses_missing_sim_time_and_identity_contract_drift(self):
        rows = [scan(1.0, [(8.0, 0.0, 0.0)], scan_id=0)]
        missing = [scan(1.0, [], scan_id=0)]
        missing[0].pop("sim_time_s")
        run, _ = write_run(self.root, "no_time", missing, mode="spawn")
        with self.assertRaisesRegex(analyzer.AnalysisError, "sim_time_s"):
            analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))

        identity = box.unmapped_box_identity("spawn", (0.0, 0.0, 1.0), 0.0, 0.35)
        identity["aabb_pad_m"] = 1.0
        run, _ = write_run(self.root, "wide_pad", rows, identity=identity, mode="spawn")
        with self.assertRaisesRegex(analyzer.AnalysisError, "aabb_pad_m"):
            analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))

        identity = box.unmapped_box_identity("spawn", (0.0, 0.0, 1.0), 0.0, 0.35)
        identity["prim"] = "/World/ground/unmapped_box"
        run, _ = write_run(self.root, "child_prim", rows, identity=identity, mode="spawn")
        with self.assertRaisesRegex(analyzer.AnalysisError, "prim"):
            analyzer.analyze_run(run, analyzer.load_thresholds(analyzer.DEFAULT_THRESHOLDS))


if __name__ == "__main__":
    unittest.main()
