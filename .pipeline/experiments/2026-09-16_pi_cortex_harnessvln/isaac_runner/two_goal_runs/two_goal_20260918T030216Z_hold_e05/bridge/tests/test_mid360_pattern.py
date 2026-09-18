import hashlib
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from lite3_sim_bridge.mid360_pattern import (
    Mid360PatternError,
    load_mid360_pattern,
)
from lite3_sim_bridge.run_isaac_v12_fallback import _set_mid360_scan_window


class Mid360PatternTest(unittest.TestCase):
    def _pattern(self, rows):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "mid360.csv"
        payload = "Time/s,Azimuth/deg,Zenith/deg\n" + "\n".join(rows) + "\n"
        path.write_text(payload, encoding="utf-8")
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return directory, path, digest

    def test_coordinate_conversion_matches_livox_yaw_pitch_convention(self):
        directory, path, digest = self._pattern(
            (
                "1,0,90",
                "2,90,90",
                "3,180,90",
                "4,270,90",
                "5,0,38",
                "6,0,97",
                "7,45,90",
                "8,315,90",
            )
        )
        self.addCleanup(directory.cleanup)
        table = load_mid360_pattern(
            path,
            expected_sha256=digest,
            expected_sample_count=8,
            points_per_second=8,
            scan_hz=2,
        )
        np.testing.assert_allclose(
            table.directions_xyz[:4],
            np.asarray(
                (
                    (1.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0),
                    (-1.0, 0.0, 0.0),
                    (0.0, -1.0, 0.0),
                ),
                dtype=np.float32,
            ),
            rtol=0.0,
            atol=1.0e-6,
        )
        self.assertGreater(table.directions_xyz[4, 2], 0.0)
        self.assertLess(table.directions_xyz[5, 2], 0.0)

    def test_scan_windows_preserve_order_timing_and_cycle(self):
        directory, path, digest = self._pattern(
            tuple(f"{index},{index * 10 % 360},90" for index in range(1, 9))
        )
        self.addCleanup(directory.cleanup)
        table = load_mid360_pattern(
            path,
            expected_sha256=digest,
            expected_sample_count=8,
            points_per_second=8,
            scan_hz=2,
        )
        first, first_meta = table.scan_window(0)
        second, second_meta = table.scan_window(1)
        wrapped, wrapped_meta = table.scan_window(2)
        self.assertEqual(first.shape, (4, 3))
        self.assertEqual(first_meta.first_sample_ordinal, 1)
        self.assertEqual(first_meta.last_sample_ordinal, 4)
        self.assertEqual(first_meta.nominal_last_point_offset_ns, 375_000_000)
        self.assertEqual(second_meta.first_sample_ordinal, 5)
        self.assertEqual(second_meta.last_sample_ordinal, 8)
        self.assertEqual(wrapped_meta.cycle_scan_index, 0)
        np.testing.assert_array_equal(first, wrapped)
        self.assertFalse(np.array_equal(first, second))

    def test_runtime_scan_install_refreshes_pose_after_direction_update(self):
        directory, path, digest = self._pattern(
            tuple(f"{index},{index * 10 % 360},90" for index in range(1, 9))
        )
        self.addCleanup(directory.cleanup)
        table = load_mid360_pattern(
            path,
            expected_sha256=digest,
            expected_sample_count=8,
            points_per_second=8,
            scan_hz=2,
        )

        class FakeLidar:
            device = "cpu"

            def __init__(self):
                self.ray_directions = torch.zeros((1, 4, 3), dtype=torch.float32)
                self.calls = []

            def reset(self):
                self.calls.append("reset")

            def update(self, *, dt, force_recompute):
                self.calls.append(("update", dt, force_recompute))

        lidar = FakeLidar()
        expected, _ = table.scan_window(1)
        metadata = _set_mid360_scan_window(lidar, table, 1, torch)
        np.testing.assert_allclose(
            lidar.ray_directions[0].numpy(), expected, rtol=0.0, atol=0.0
        )
        self.assertEqual(lidar.calls, ["reset", ("update", 0.0, True)])
        self.assertEqual(metadata.first_sample_ordinal, 5)

    def test_loader_fails_closed_on_hash_header_and_sequence(self):
        directory, path, digest = self._pattern(("1,0,90", "3,90,90"))
        self.addCleanup(directory.cleanup)
        with self.assertRaisesRegex(Mid360PatternError, "SHA-256 mismatch"):
            load_mid360_pattern(
                path,
                expected_sha256="0" * 64,
                expected_sample_count=2,
                points_per_second=2,
                scan_hz=1,
            )
        with self.assertRaisesRegex(Mid360PatternError, "consecutive ordinals"):
            load_mid360_pattern(
                path,
                expected_sha256=digest,
                expected_sample_count=2,
                points_per_second=2,
                scan_hz=1,
            )

    def test_official_pattern_contract_when_source_checkout_is_present(self):
        source = (
            Path(__file__).resolve().parents[3]
            / "references"
            / "upstream"
            / "2026-08-19_mid360_simulation"
            / "source"
            / "livox_laser_simulation"
            / "scan_mode"
            / "mid360.csv"
        )
        if not source.is_file():
            self.skipTest("ignored pinned upstream source checkout is not present")
        table = load_mid360_pattern(source)
        self.assertEqual(table.sample_count, 800_000)
        self.assertEqual(table.points_per_scan, 20_000)
        self.assertEqual(table.scans_per_pattern_cycle, 40)
        self.assertLessEqual(table.elevation_range_deg[0], -7.2)
        self.assertGreaterEqual(table.elevation_range_deg[1], 52.1)
        _, metadata = table.scan_window(39)
        self.assertEqual(metadata.first_sample_ordinal, 780_001)
        self.assertEqual(metadata.last_sample_ordinal, 800_000)
        self.assertEqual(metadata.nominal_last_point_offset_ns, 99_995_000)


if __name__ == "__main__":
    unittest.main()
