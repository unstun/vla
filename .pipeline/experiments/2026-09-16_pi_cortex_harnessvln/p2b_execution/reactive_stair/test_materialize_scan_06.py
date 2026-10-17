import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("materialize_scan_06", HERE / "materialize_scan_06.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MaterializeScan06Test(unittest.TestCase):
    def test_real_candidate_hashes_and_shared_hook(self):
        base = module.scan05_gate.source_hashes(module.SOURCE, module.P2B / "baseline_config/planner.yaml")
        candidate = module.OUTPUT / "src"
        manifest = module.OUTPUT / "reactive_stair_candidate_manifest.json"
        self.assertTrue(manifest.is_file())
        import json
        record = json.loads(manifest.read_text())
        self.assertEqual(record["status"], "source_candidate_unbuilt")
        for path, expected in base.items():
            target = candidate / path
            if path in record["changed_sha256"]:
                self.assertEqual(module.sha(target), record["changed_sha256"][path])
            else:
                self.assertEqual(module.sha(target), expected)
        for path, expected in record["changed_sha256"].items():
            self.assertEqual(module.sha(candidate / path), expected)
        grid_h = (candidate / "plan_env/include/plan_env/grid_map.h").read_text()
        self.assertEqual(grid_h.count("reactiveOccupancy(front)"), 1)
        self.assertEqual(grid_h.count("reactiveOccupancy(rear)"), 1)
        self.assertNotIn("queryIsTraversableStep", grid_h)
        grid_cpp = (candidate / "plan_env/src/grid_map.cpp").read_text()
        self.assertIn("reactiveTomogramCallback", grid_cpp)
        self.assertIn("reactiveTracksCallback", grid_cpp)
        self.assertIn("reactive_pending_cloud_ = true", grid_cpp)
        self.assertIn("if (reactive_pending_cloud_) reactive_cloud_ready_ = true", grid_cpp)
        self.assertIn("reactive_nonterrain_history_.clear()", grid_cpp)
        self.assertEqual(grid_cpp.count("reactive_nonterrain_history_.erase(key)"), 2)
        self.assertEqual(module.sha(module.P2B / "baseline_config/planner.yaml"), record["pinned_planner_yaml_sha256"])

    def test_reject_existing_destination(self):
        with self.assertRaisesRegex(module.Refused, "already exists"):
            module.materialize()

    def test_source_tampering_refuses_before_output(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "scan_04"
            source.mkdir()
            for name in ("overlay_manifest.json", "source_sha256.json", "terminal_accel_fix_manifest.json"):
                shutil.copy2(module.SOURCE / name, source / name)
            shutil.copytree(module.SOURCE / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (source / "src/plan_env/include/plan_env/grid_map.h").write_bytes(b"tampered")
            output = root / "scan_06"
            old_source, old_output = module.SOURCE, module.OUTPUT
            try:
                module.SOURCE, module.OUTPUT = source, output
                with self.assertRaisesRegex(module.scan05_gate.Refused, "source gate failed"):
                    module.materialize()
                self.assertFalse(output.exists())
            finally:
                module.SOURCE, module.OUTPUT = old_source, old_output


if __name__ == "__main__":
    unittest.main()
