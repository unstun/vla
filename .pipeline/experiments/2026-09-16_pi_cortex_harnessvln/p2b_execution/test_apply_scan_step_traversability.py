"""Failing tests for the hash-gated SCAN step-filter patcher."""
import hashlib
import importlib.util
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCAN_04 = HERE / "builds/scan_04"
GRID_H = Path("src/plan_env/include/plan_env/grid_map.h")
GRID_CPP = Path("src/plan_env/src/grid_map.cpp")
PINNED_PLANNER = HERE / "baseline_config/planner.yaml"
PINNED_PLANNER_SHA256 = "42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e"
SCAN_04_GRID_H_SHA256 = "3a562e007f40dc78fd811b31f4326cf778cfb0e475a1d61fd0836eda3aaa28d4"
SCAN_04_GRID_CPP_SHA256 = "2b94d5e09a71f3d9349e9b816f0b1e42b3dbc03551a20b7452579122e88efc87"
FROZEN_KEYS = (
    'load_parameter(node_, "grid_map.ground_height", mp_.ground_height_, 0.0);',
    'load_parameter(node_, "grid_map.vis_height", mp_.vis_height_, 0.3);',
    'load_parameter(node_, "grid_map.cloud_is_world", mp_.cloud_is_world_, true);',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_apply():
    spec = importlib.util.spec_from_file_location(
        "apply_scan_step_traversability",
        str(HERE / "apply_scan_step_traversability.py"),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ApplyStepTraversabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.build = Path(self.tmp.name) / "scan_copy"
        for rel in (GRID_H, GRID_CPP):
            dest = self.build / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SCAN_04 / rel, dest)

    def test_scan_04_and_planner_yaml_hashes_are_the_pinned_baseline(self):
        self.assertEqual(digest(SCAN_04 / GRID_H), SCAN_04_GRID_H_SHA256)
        self.assertEqual(digest(SCAN_04 / GRID_CPP), SCAN_04_GRID_CPP_SHA256)
        self.assertEqual(digest(PINNED_PLANNER), PINNED_PLANNER_SHA256)

    def test_refuses_wrong_grid_map_hash(self):
        apply = load_apply()
        target = self.build / GRID_H
        target.write_bytes(target.read_bytes() + b"\n")
        with self.assertRaises(apply.PatchRefused):
            apply.apply_patch(self.build)

    def test_patches_inflate_query_and_keeps_frozen_occupancy_loads(self):
        apply = load_apply()
        manifest = apply.apply_patch(self.build)
        header = (self.build / GRID_H).read_text(encoding="utf-8", errors="replace")
        cpp = (self.build / GRID_CPP).read_text(encoding="utf-8", errors="replace")
        copied = self.build / "src/plan_env/include/plan_env/step_traversability.h"
        self.assertTrue(copied.is_file())
        self.assertIn("#include <plan_env/step_traversability.h>", header)
        self.assertIn("queryIsTraversableStep", header)
        self.assertIn("occupancyHitIsTraversableStep", copied.read_text(encoding="utf-8"))
        self.assertIn("if (front_occ == 1 && queryIsTraversableStep(front))", header)
        self.assertIn('load_parameter(node_, "grid_map.step_filter_enable"', cpp)
        for line in FROZEN_KEYS:
            self.assertIn(line, cpp)
        self.assertEqual(digest(SCAN_04 / GRID_H), SCAN_04_GRID_H_SHA256)
        self.assertEqual(digest(SCAN_04 / GRID_CPP), SCAN_04_GRID_CPP_SHA256)
        self.assertEqual(digest(PINNED_PLANNER), PINNED_PLANNER_SHA256)
        self.assertEqual(manifest["schema_version"], 1)

    def test_refuses_accepted_scan_04_build_name(self):
        apply = load_apply()
        with self.assertRaises(apply.PatchRefused):
            apply.main(["scan_04"])

    def test_refuses_canonical_scan_04_path(self):
        apply = load_apply()
        with self.assertRaises(apply.PatchRefused):
            apply.apply_patch(SCAN_04)
        self.assertEqual(digest(SCAN_04 / GRID_H), SCAN_04_GRID_H_SHA256)
        self.assertEqual(digest(SCAN_04 / GRID_CPP), SCAN_04_GRID_CPP_SHA256)
        self.assertFalse((SCAN_04 / "step_traversability_patch_manifest.json").exists())
        self.assertFalse(
            (SCAN_04 / "src/plan_env/include/plan_env/step_traversability.h").exists()
        )

    def test_pinned_hashes_match_scan_04_overlay_manifest(self):
        manifest = json.loads((SCAN_04 / "overlay_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["after"]["plan_env/include/plan_env/grid_map.h"],
            SCAN_04_GRID_H_SHA256,
        )
        self.assertEqual(
            manifest["after"]["plan_env/src/grid_map.cpp"],
            SCAN_04_GRID_CPP_SHA256,
        )

    def test_cpp_and_patcher_defaults_match_python_contract(self):
        from step_traversability import DEFAULT_PARAMS

        apply = load_apply()
        header = (HERE / "step_traversability.h").read_text(encoding="utf-8")
        cpp_insert = "\n".join(apply.CPP_INSERT)
        fields = (
            ("critical_height_m", DEFAULT_PARAMS.critical_height_m),
            ("window_radius_m", DEFAULT_PARAMS.window_radius_m),
            ("height_band_m", DEFAULT_PARAMS.height_band_m),
            ("min_tread_depth_m", DEFAULT_PARAMS.min_tread_depth_m),
            ("min_step_height_m", DEFAULT_PARAMS.min_step_height_m),
            ("resolution_m", DEFAULT_PARAMS.resolution_m),
        )
        for field, value in fields:
            token = "%.2f" % value
            self.assertRegex(header, r"%s = %s" % (field, re.escape(token)))
            if field == "resolution_m":
                continue
            self.assertIn(", " + token + ");", cpp_insert)
        self.assertIn("mp_.step_filter_enable_, true", cpp_insert)


if __name__ == "__main__":
    unittest.main()
