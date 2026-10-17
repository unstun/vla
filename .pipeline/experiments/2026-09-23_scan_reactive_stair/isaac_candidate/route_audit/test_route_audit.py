import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

import audit_stair_routes as audit


class RouteAuditTest(unittest.TestCase):
    def test_building_source_gate_and_real_pct_step(self):
        vertices, faces = audit.parse_building_mesh(audit.BUILDING)
        self.assertEqual(len(faces), 16448)
        self.assertGreater(len(vertices), 10000)
        selected = audit.SelectedGround()
        self.assertEqual(len(selected.points), 86775)
        a = selected.nearest(-5.3, 1.5, 0.74)
        b = selected.nearest(-5.3, 1.3, 0.85)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertAlmostEqual(a["world_xyz_m"][2], 0.740234375, places=6)
        self.assertGreater(b["world_xyz_m"][2] - a["world_xyz_m"][2], 0.10)
        for result in (a, b):
            px, py, _ = result["world_xyz_m"]
            expected_cell = [int(round((point - selected.center[i]) / selected.resolution))
                             + int(selected.grid_offset[i])
                             for i, point in enumerate((px, py))]
            self.assertEqual(result["cell_xy"], expected_cell)
        with tempfile.TemporaryDirectory() as temp:
            changed = Path(temp) / "building.usda"
            changed.write_bytes(audit.BUILDING.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                audit.parse_building_mesh(changed)

    def test_no_overhead_hit_is_unknown_not_obstacle(self):
        vertices = np.asarray([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0],
                               [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0]])
        faces = np.asarray([[0, 1, 2], [0, 2, 3]])
        mesh = audit.MeshHeights(vertices, faces)
        class FlatGround:
            def nearest(self, x, y, expected_z, max_delta=0.26):
                return {"cell_xy": [0, 0], "world_xyz_m": [x, y, 0.0],
                        "cost": 0.0, "xy_query_distance_m": 0.0}
        result = audit.support_and_overhead(FlatGround(), mesh, 0.0, 0.0, 0.0)
        self.assertTrue(result["supported"])
        self.assertIsNone(result["headroom_m"])
        self.assertEqual(result["headroom_status"],
                         "no_mesh_overhead_intersection_unknown_or_open")

    def test_real_reviewable_segment_and_transverse_limit(self):
        audit.main()
        report = json.loads((audit.HERE / "route_audit.json").read_text())
        proposal = json.loads((audit.HERE / "proposed_stair_encounter.json").read_text())
        self.assertTrue(report["any_joint_route_pass"])
        self.assertEqual(report["best_x_m"], -5.3)
        self.assertFalse(report["any_0p4m_transverse_crossing"])
        self.assertFalse(proposal["geometry_reviewed"])
        self.assertFalse(proposal["initial_placement_pass"])
        self.assertAlmostEqual(proposal["initial_hull_gap_m"], -0.13, places=6)
        self.assertGreater(len({tuple(cell) for cell in proposal["official_human"]["source_pct_cells"]}), 1)
        self.assertEqual(proposal["status"], "geometry_screen_only_not_approved_or_scheduled")
        person_z = [point[2] for point in proposal["official_human"]["waypoints_ground_xyz_m"]]
        robot_z = [point[2] for point in proposal["robot"]["waypoints_ground_xyz_m"]]
        self.assertEqual(len(set(person_z)), 1)  # no linear crossing of a riser
        self.assertGreater(robot_z[-1] - robot_z[0], 0.10)
        self.assertLessEqual(max(proposal["official_human"]["pct_xy_residual_m"]), 0.06)


if __name__ == "__main__":
    unittest.main()
