"""Verify the delivered dense source and preservation of navigation evidence."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest

B = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(B / "runtime_sources/bridge/lite3_sim_bridge"))
from pct_sim_clock_core import (load_dense_surface_points, load_pinned_map,
                                load_paired_elevations, selected_ground_points)


class DenseInputTests(unittest.TestCase):
    def test_dense_and_navigation_payloads(self):
        source = load_pinned_map(B / "inputs/new_building.pickle")
        before = source["data"].tobytes()
        elevations = load_paired_elevations(
            B / "inputs/new_building_original_precision.npz", source)
        dense = load_dense_surface_points(B / "inputs/new_building_dense_surface.npy")
        navigation = selected_ground_points(source, paired_elevations=elevations)
        self.assertEqual(hashlib.sha256(dense.tobytes()).hexdigest(),
                         "b68527dd9d2ea8a4647c64aaf59b884da16364e41b146943c03f2c6da68cfa56")
        self.assertEqual(hashlib.sha256(navigation.tobytes()).hexdigest(),
                         "97d2dfbdb60c91e8473ab57f348923360f139da1130b4e9b7dd57e8655c15ca2")
        self.assertEqual(source["data"].tobytes(), before)

    def test_altered_source_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "surface.npy"
            raw = bytearray((B / "inputs/new_building_dense_surface.npy").read_bytes())
            raw[-1] ^= 1
            path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_dense_surface_points(path)


if __name__ == "__main__":
    unittest.main()
