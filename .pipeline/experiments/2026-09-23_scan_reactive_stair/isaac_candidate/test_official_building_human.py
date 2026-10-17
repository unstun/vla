import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from official_building_human import (
    actor_state, file_sha256, load_actor_route, verify_official_bundle,
)


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
ASSETS = PROJECT / "references/upstream/2026-09-24_isaac_official_police_human"
CACHE = HERE.parent / "official_human_cache"
BUILDING_SHA = "e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39"


class OfficialBuildingHumanTest(unittest.TestCase):
    def test_smoke_refuses_unpinned_asset_before_isaac_import(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "unused-output"
            result = subprocess.run([
                sys.executable, str(HERE / "smoke_official_mesh_two_poses.py"),
                "--asset-root", temp, "--cache-dir", str(CACHE),
                "--output", str(output),
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("official human asset missing or changed", result.stderr)
            self.assertFalse(output.exists())

    def test_pinned_official_bundle_and_missing_texture(self):
        identity = verify_official_bundle(ASSETS, CACHE)
        self.assertEqual(identity["cache_content_sha256"],
                         "76c19b57ebd03e01820e6b9db79bde8f2f3e436302744ef457278af8d17ef5b3")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "male_adult_police_04.usd").write_bytes(
                (ASSETS / "male_adult_police_04.usd").read_bytes())
            with self.assertRaisesRegex(ValueError, "asset missing or changed"):
                verify_official_bundle(root, CACHE)

    def test_route_is_separate_truth_and_tracks_ground_height(self):
        route_doc = {
            "schema_version": 1, "frame_id": "world", "building_usda_sha256": BUILDING_SHA,
            "geometry_reviewed": True, "speed_mps": 0.5, "start_delay_s": 1.0,
            "waypoints_ground_xyz_m": [[0.0, 0.0, 0.1], [0.0, 0.2, 0.2], [0.0, 0.4, 0.35]],
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "route.json"
            path.write_text(json.dumps(route_doc))
            with self.assertRaisesRegex(ValueError, "no approved SHA-256"):
                load_actor_route(path, BUILDING_SHA)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_actor_route(path, BUILDING_SHA, "0" * 64)
            route = load_actor_route(path, BUILDING_SHA, file_sha256(path))
            self.assertEqual(actor_state(route, 0.0)["phase"], "waiting")
            middle = actor_state(route, 1.2)
            self.assertEqual(middle["phase"], "walking")
            self.assertAlmostEqual(middle["ground_xyz_m"][1], 0.1)
            self.assertAlmostEqual(middle["ground_xyz_m"][2], 0.15)
            self.assertEqual(actor_state(route, 2.0)["phase"], "arrived")
            route_doc["geometry_reviewed"] = False
            path.write_text(json.dumps(route_doc))
            with self.assertRaisesRegex(ValueError, "no geometry review"):
                load_actor_route(path, BUILDING_SHA, file_sha256(path))
            route_doc["geometry_reviewed"] = True
            route_doc["waypoints_ground_xyz_m"][2][2] = 0.5
            path.write_text(json.dumps(route_doc))
            with self.assertRaisesRegex(ValueError, "exceed the V12 step height"):
                load_actor_route(path, BUILDING_SHA, file_sha256(path))


if __name__ == "__main__":
    unittest.main()
