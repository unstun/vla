import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("materialize_scan_05", HERE / "materialize_scan_05.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MaterializerTest(unittest.TestCase):
    def test_real_source_gate_follows_terminal_fix_chain(self):
        hashes = module.source_hashes(module.SOURCE, module.P2B / "baseline_config" / "planner.yaml")
        self.assertEqual(hashes["plan_manage/src/planner_manager.cpp"], module.EXPECTED_TERMINAL_FIX)

    def test_valid_fixture_and_read_only_baseline(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "scan_04"
            source.mkdir()
            # Verify a disposable sibling fixture; scan_04 remains read-only.
            import shutil
            for name in ("overlay_manifest.json", "source_sha256.json", "terminal_accel_fix_manifest.json"):
                shutil.copy2(module.SOURCE / name, source / name)
            shutil.copytree(module.SOURCE / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            before = module.source_hashes(source, module.P2B / "baseline_config" / "planner.yaml")
            output = root / "scan_05"
            result = module.materialize(source, output)
            self.assertEqual(result["status"], "inactive_no_live_adapter")
            self.assertEqual(module.source_hashes(source, module.P2B / "baseline_config" / "planner.yaml"), before)
            self.assertEqual(module.digest(output / "src" / module.HEADER_REL), module.digest(module.HEADER))
            self.assertEqual(module.digest(output / "src/plan_manage/config/planner.yaml"), before["plan_manage/config/planner.yaml"])
            with self.assertRaisesRegex(module.Refused, "already exists"):
                module.materialize(source, output)

    def test_hash_mismatch_refuses_without_output(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            source = root / "scan_04"
            source.mkdir()
            import shutil
            for name in ("overlay_manifest.json", "source_sha256.json", "terminal_accel_fix_manifest.json"):
                shutil.copy2(module.SOURCE / name, source / name)
            shutil.copytree(module.SOURCE / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (source / "src/plan_env/include/plan_env/grid_map.h").write_bytes(b"tampered")
            output = root / "scan_05"
            with self.assertRaisesRegex(module.Refused, "source gate failed"):
                module.materialize(source, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
