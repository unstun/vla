import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location("materialize_scan_10", HERE / "materialize_scan_10.py")
materializer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = materializer
spec.loader.exec_module(materializer)


def load_core(name, path):
    core_spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(core_spec)
    sys.modules[name] = module
    core_spec.loader.exec_module(module)
    return module


def cluster(cx):
    return tuple((cx + dx, 1.0 + dy, height)
                 for dx in (-0.10, 0.0, 0.10)
                 for dy in (-0.08, 0.08)
                 for height in (0.45, 0.8, 1.2, 1.55))


def observed_track_count(core):
    ground = core.TerrainSupport(
        "world", 1_000_000_000, "pct_selected_ground_fixture", 0.1, 0.0, 0.0,
        {(x, y): (0.0,) for x in range(0, 51) for y in range(0, 51)})
    tracker = core.MovingClusterTracker()
    results = []
    for index in range(11):
        stamp = 1_000_000_000 + index * 100_000_000
        cloud = core.CloudFrame(stamp, "lidar", cluster(1.0 + 0.03 * index))
        pose = core.PoseObservation(stamp, "world", "lidar", (0.0, 0.0, 0.0),
                                    (0.0, 0.0, 0.0, 1.0))
        results.append(tracker.process(cloud, pose, ground, stamp))
    return results


class Scan10MaterializerTest(unittest.TestCase):
    def test_built_scan09_gate_and_only_core_changed(self):
        base = materializer.gate()
        record = json.loads((materializer.OUTPUT / "slow_motion_candidate_manifest.json").read_text())
        root = materializer.OUTPUT / "src"
        actual = {path.relative_to(root).as_posix(): materializer.sha(path)
                  for path in root.rglob("*") if path.is_file()}
        self.assertEqual(record["base"], "scan_09")
        self.assertEqual(record["status"], "source_candidate_unbuilt")
        self.assertEqual(record["base_sha256"], base)
        self.assertEqual(set(record["changed_sha256"]), {materializer.CORE_REL.as_posix()})
        self.assertEqual(actual, {**base, **record["changed_sha256"]})
        self.assertEqual(record["source_label"], "sensor_lidar_moving_cluster_candidate_v2")
        baseline = HERE.parent.parent.parent / "2026-09-23_scan_reactive_stair/scan09_slow_motion_review.json"
        self.assertEqual(record["baseline_failure_sha256"], hashlib.sha256(baseline.read_bytes()).hexdigest())
        self.assertTrue(json.loads(baseline.read_text())["reproduced_failure"])

    def test_materialized_core_corrects_bounded_slow_motion_failure(self):
        old = load_core("scan09_baseline_core_test", materializer.SOURCE / "src" / materializer.CORE_REL)
        new = load_core("scan10_candidate_core_test", materializer.OUTPUT / "src" / materializer.CORE_REL)
        old_rows, new_rows = observed_track_count(old), observed_track_count(new)
        self.assertEqual(sum(len(row.tracks) for row in old_rows), 0)
        self.assertEqual([i for i, row in enumerate(new_rows) if row.tracks][0], 3)
        self.assertEqual({row.tracks[0].id for row in new_rows if row.tracks}, {"cluster-1"})
        self.assertAlmostEqual(new_rows[-1].tracks[0].center[0], 1.3, places=2)
        self.assertEqual(new_rows[-1].tracks[0].stamp_ns, 2_000_000_000)

    def test_existing_output_and_tampered_source_refused(self):
        with self.assertRaisesRegex(materializer.Refused, "already exists"):
            materializer.materialize()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scan_09"
            source.mkdir()
            for name in ("source_sha256.json", "pct_density_candidate_manifest.json", "build_result.json"):
                shutil.copy2(materializer.SOURCE / name, source / name)
            shutil.copytree(materializer.SOURCE / "src", source / "src",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (source / "src" / materializer.CORE_REL).write_bytes(b"tampered")
            previous_source, previous_output = materializer.SOURCE, materializer.OUTPUT
            try:
                materializer.SOURCE, materializer.OUTPUT = source, root / "scan_10"
                with self.assertRaisesRegex(materializer.Refused, "scan_09 source gate"):
                    materializer.materialize()
                self.assertFalse(materializer.OUTPUT.exists())
            finally:
                materializer.SOURCE, materializer.OUTPUT = previous_source, previous_output


if __name__ == "__main__":
    unittest.main()
