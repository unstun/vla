"""Readiness regressions: valid geometry needs no semantic detector output."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("geometry_driver", Path(__file__).with_name("geometry_driver.py"))
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


class GeometryReadinessTests(unittest.TestCase):
    def setUp(self):
        self.health = {"run_id": "case", "run_epoch_ns": 7, "wall_monotonic_ns": 1_000_000_000,
                       "stamps_ns": {"clock": 2_000_000_000, "cloud": 1_900_000_000,
                                     "lidar_pose": 1_900_000_000, "pct_tomogram": 1_000_000_000}}

    def ready(self, value):
        with patch.object(driver, "read_json", return_value=value), patch.object(driver.time, "monotonic_ns", return_value=1_000_000_100):
            return driver.health_ready("unused", "case", 7)

    def test_no_semantic_messages_required(self):
        self.assertTrue(self.ready(self.health))
        self.health["tracker"] = {"ready": False, "reason": "partial visibility"}
        self.assertTrue(self.ready(self.health))

    def test_mismatched_epoch_and_run_rejected(self):
        for field, value in (("run_epoch_ns", 8), ("run_id", "another")):
            health = copy.deepcopy(self.health)
            health[field] = value
            self.assertFalse(self.ready(health))

    def test_missing_stale_future_and_unpaired_sensors_rejected(self):
        for field, value in (("cloud", 0), ("pct_tomogram", 0), ("cloud", 1_000_000_000),
                             ("lidar_pose", 1_899_000_000), ("cloud", 2_100_000_000)):
            health = copy.deepcopy(self.health)
            health["stamps_ns"][field] = value
            self.assertFalse(self.ready(health))

    def test_stale_transport_rejected(self):
        self.health["wall_monotonic_ns"] = 0
        self.assertFalse(self.ready(self.health))


if __name__ == "__main__":
    unittest.main()
