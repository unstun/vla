"""A delayed shared snapshot is tolerated without accepting foreign or stale state."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent


class SnapshotReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copyfile(HERE / 'long_route_driver.py', self.root / 'long_route_driver.py')
        shutil.copyfile(HERE.parents[1] / 'repairs/2026-09-26_generic_occupancy/geometry_driver.py',
                        self.root / 'executed_geometry_driver.py')
        spec = importlib.util.spec_from_file_location('test_long_route', self.root / 'long_route_driver.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.snapshot = {'run_id': 'test', 'sim_time_s': 12., 'wall_monotonic_ns': 95_000_000_000,
                         'applied_command': {}, 'measured': {'base_xyz': [0, 0, 0],
                         'base_quat_wxyz': [1, 0, 0, 0], 'horizontal_speed_mps': 0,
                         'yaw_rate_radps': 0, 'command_obs_error': 0}}

    def test_five_second_cached_snapshot_accepts(self):
        path = self.root / 'current_command.json'
        path.write_text(json.dumps(self.snapshot))
        with patch.object(self.module.driver.time, 'monotonic_ns', return_value=100_000_000_000):
            self.assertEqual(self.module.driver.wait_snapshot(path, 'test', timeout_s=15.), self.snapshot)

    def test_old_future_and_foreign_reject(self):
        with patch.object(self.module.driver.time, 'monotonic_ns', return_value=100_000_000_000):
            for changes in ({'wall_monotonic_ns': 89_000_000_000},
                            {'wall_monotonic_ns': 101_000_000_000}, {'run_id': 'foreign'}):
                with self.subTest(changes=changes):
                    self.assertFalse(self.module.driver.snapshot_ok(dict(self.snapshot, **changes), 'test'))


if __name__ == '__main__':
    unittest.main()
