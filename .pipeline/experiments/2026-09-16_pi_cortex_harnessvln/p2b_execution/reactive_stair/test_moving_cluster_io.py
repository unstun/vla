import struct
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from moving_cluster_io import decode_float32_cloud, terrain_from_pct_records


class PointCloudBoundaryTest(unittest.TestCase):
    def test_physical_ground_keeps_high_cost_floor_with_distinct_provenance(self):
        records = [(1.0, 2.0, 0.77, 50.0), (1.1, 2.0, 0.77, 10.0)]
        payload = b"".join(struct.pack("<ffff", *r) for r in records)
        selected = terrain_from_pct_records(records, payload, "world", 1)
        self.assertIsNone(selected.ground_below(1.0, 2.0, 1.5))
        physical = terrain_from_pct_records(records, payload, "world", 1, cost_limit=None)
        self.assertAlmostEqual(physical.ground_below(1.0, 2.0, 1.5), .74)
        self.assertTrue(physical.source_id.startswith("pct_physical_ground/sha256/"))

    def test_terrain_limit_does_not_relax_raw_cloud_limit(self):
        count = 100_001
        payload = struct.pack("<ffff", 1.0, 2.0, .77, 50.0) * count
        fields = {name: (i * 4, 7, 1) for i, name in enumerate(("x", "y", "z", "intensity"))}
        with self.assertRaises(ValueError):
            decode_float32_cloud(payload, count, 1, 16, 16 * count, False, fields, ("x", "y", "z", "intensity"))
        decoded = decode_float32_cloud(payload, count, 1, 16, 16 * count, False, fields,
                                       ("x", "y", "z", "intensity"), max_points=200_000)
        self.assertEqual(len(decoded), count)

    def test_xyz_little_endian_and_pct_ground_offset(self):
        payload = struct.pack("<ffff", 1.0, 2.0, 0.23, 15.0)
        fields = {name: (offset, 7, 1) for name, offset in
                  (("x", 0), ("y", 4), ("z", 8), ("intensity", 12))}
        decoded = decode_float32_cloud(payload, 1, 1, 16, 16, False, fields,
                                       ("x", "y", "z", "intensity"))
        ground = terrain_from_pct_records(decoded, payload, "world", 1_000_000_000)
        self.assertAlmostEqual(ground.ground_below(1.0, 2.0, 0.5), 0.2, places=6)
        self.assertTrue(ground.source_id.startswith("pct_tomogram/sha256/"))

    def test_bad_layout_or_fields_rejected(self):
        payload = struct.pack("<fff", 1.0, 2.0, 3.0)
        fields = {name: (offset, 7, 1) for name, offset in
                  (("x", 0), ("y", 4), ("z", 8))}
        self.assertEqual(
            decode_float32_cloud(payload, 1, 1, 12, 12, False, fields, ("x", "y", "z")),
            [(1.0, 2.0, 3.0)],
        )
        with self.assertRaisesRegex(ValueError, "layout"):
            decode_float32_cloud(payload, 1, 1, 12, 12, True, fields, ("x", "y", "z"))
        with self.assertRaisesRegex(ValueError, "layout"):
            decode_float32_cloud(payload[:-1], 1, 1, 12, 12, False, fields, ("x", "y", "z"))
        with self.assertRaisesRegex(ValueError, "missing"):
            decode_float32_cloud(payload, 1, 1, 12, 12, False, fields,
                                 ("x", "y", "z", "intensity"))
        with self.assertRaisesRegex(ValueError, "invalid PointCloud2 field"):
            bad = dict(fields, x=(0, 6, 1))
            decode_float32_cloud(payload, 1, 1, 12, 12, False, bad, ("x", "y", "z"))


if __name__ == "__main__":
    unittest.main()
