import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("materialize_scan_07", HERE / "materialize_scan_07.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MaterializeScan07Test(unittest.TestCase):
    def test_source_and_overlay_hashes(self):
        base = module.gate()
        self.assertEqual(len(base), 72)
        record = json.loads((module.OUTPUT / "eth_step_score_candidate_manifest.json").read_text())
        self.assertEqual(record["status"], "source_candidate_unbuilt")
        self.assertEqual(record["eth_stepfilter_cpp_sha256"], module.EXPECTED_ETH_SHA)
        self.assertEqual(record["local_parameters"]["critical_height_m"], 0.26)
        self.assertEqual(record["local_parameters"]["resolution_m"], 0.10)
        root = module.OUTPUT / "src"
        actual = {path.relative_to(root).as_posix(): module.sha(path)
                  for path in root.rglob("*") if path.is_file()}
        for name, expected in base.items():
            if name not in record["changed_sha256"]:
                self.assertEqual(actual[name], expected)
        for name, expected in record["changed_sha256"].items():
            self.assertEqual(actual[name], expected)
        self.assertEqual(set(actual), set(base) | set(record["changed_sha256"]))
        methods = (root / "plan_env/include/plan_env/scan_reactive_grid_methods.inc").read_text()
        self.assertLess(methods.index("precomputeEthStyleStepScores(terrain)"),
                        methods.index("reactive_decision_.acceptTerrain(scored.support)"))
        self.assertIn("reactive_decision_.decide(query, obstacle)", methods)

    def test_existing_destination_refused(self):
        with self.assertRaisesRegex(module.Refused, "already exists"):
            module.materialize()

    def test_tampered_built_source_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scan_06"
            source.mkdir()
            for name in ("source_sha256.json", "reactive_stair_candidate_manifest.json", "build_result.json"):
                shutil.copy2(module.SOURCE / name, source / name)
            shutil.copytree(module.SOURCE / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (source / "src/plan_env/include/plan_env/grid_map.h").write_bytes(b"tampered")
            old_source, old_output = module.SOURCE, module.OUTPUT
            try:
                module.SOURCE, module.OUTPUT = source, root / "scan_07"
                with self.assertRaisesRegex(module.Refused, "scan_06 source gate"):
                    module.materialize()
                self.assertFalse(module.OUTPUT.exists())
            finally:
                module.SOURCE, module.OUTPUT = old_source, old_output


if __name__ == "__main__":
    unittest.main()
