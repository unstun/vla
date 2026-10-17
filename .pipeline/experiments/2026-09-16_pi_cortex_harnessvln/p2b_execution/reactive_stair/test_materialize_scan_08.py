import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("materialize_scan_08", HERE / "materialize_scan_08.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MaterializeScan08Test(unittest.TestCase):
    def test_source_and_new_package_hashes(self):
        base = module.gate()
        candidate = module.OUTPUT / "src"
        record = json.loads((module.OUTPUT / "moving_cluster_candidate_manifest.json").read_text())
        self.assertEqual(record["status"], "source_candidate_unbuilt")
        self.assertEqual(record["base"], "scan_07")
        actual = {path.relative_to(candidate).as_posix(): module.sha(path)
                  for path in candidate.rglob("*") if path.is_file()}
        self.assertEqual(len(base), 74)
        self.assertTrue(all(actual[path] == expected for path, expected in base.items()))
        self.assertTrue(all(actual[path] == expected
                            for path, expected in record["added_sha256"].items()))
        self.assertEqual(set(actual), set(base) | set(record["added_sha256"]))
        package = candidate / "scan_reactive_tracker"
        self.assertIn("scan_planner_msgs", (package / "package.xml").read_text())
        self.assertIn("moving_cluster_tracker = scan_reactive_tracker.node:main",
                      (package / "setup.py").read_text())
        self.assertIn("/quad_0/cloud", (package / "scan_reactive_tracker/node.py").read_text())

    def test_refuse_existing_output(self):
        with self.assertRaisesRegex(module.Refused, "already exists"):
            module.materialize()

    def test_tampered_built_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scan_07"
            source.mkdir()
            for name in ("source_sha256.json", "eth_step_score_candidate_manifest.json", "build_result.json"):
                shutil.copy2(module.SOURCE / name, source / name)
            shutil.copytree(module.SOURCE / "src", source / "src",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (source / "src/plan_env/include/plan_env/grid_map.h").write_bytes(b"tampered")
            previous_source, previous_output = module.SOURCE, module.OUTPUT
            try:
                module.SOURCE, module.OUTPUT = source, root / "scan_08"
                with self.assertRaisesRegex(module.Refused, "scan_07 source gate"):
                    module.materialize()
                self.assertFalse(module.OUTPUT.exists())
            finally:
                module.SOURCE, module.OUTPUT = previous_source, previous_output


if __name__ == "__main__":
    unittest.main()
