import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import materialize_official_building_mesh as candidate


class MaterializerTest(unittest.TestCase):
    def test_source_gate_and_official_mesh_wiring(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "candidate"
            manifest = candidate.materialize(output)
            source = (output / "run_pct_scan_building.py").read_text()
            ast.parse(source)
            self.assertEqual(candidate.digest(output / "run_pct_scan_building.py"),
                             manifest["runner_sha256"])
            self.assertEqual(candidate.digest(output / "official_building_human.py"),
                             manifest["helper_sha256"])
            self.assertIn("track_mesh_transforms=True", source)
            self.assertIn("prim_expr=VISUAL_ROOT", source)
            self.assertIn("official_animation_player.update(", source)
            self.assertIn('"official_human_truth.jsonl"', source)
            self.assertIn("if not args.unfiltered_planner_cloud:", source)
            self.assertNotIn("_write_official_human_wrapper_usd", source)
            self.assertNotIn("_official_human_sensor_exprs", source)
            self.assertEqual(manifest["status"],
                             "inactive_source_candidate_requires_isaac_first_hit_smoke")
            with self.assertRaises(FileExistsError):
                candidate.materialize(output)

    def test_changed_source_and_missing_anchor_refused(self):
        path = candidate.PILOT_MATERIALIZER
        with patch.dict(candidate.EXPECTED, {path: "0" * 64}):
            with tempfile.TemporaryDirectory() as temp:
                with self.assertRaisesRegex(ValueError, "pinned source hash changed"):
                    candidate.materialize(Path(temp) / "candidate")
        with self.assertRaisesRegex(ValueError, "anchor count"):
            candidate.overlay("unrelated source")


if __name__ == "__main__":
    unittest.main()
