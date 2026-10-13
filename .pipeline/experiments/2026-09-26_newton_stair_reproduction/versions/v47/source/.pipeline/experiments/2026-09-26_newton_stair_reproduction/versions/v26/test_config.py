"""Regression for omission versus explicit automatic layer selection."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("CONFIG_SOURCE", str(
    BASE / "runtime_sources/backend_ros/p2b_backend_ros/config.py")))
SPEC = importlib.util.spec_from_file_location("config_under_test", SOURCE)
CONFIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIG)


class ConfigTests(unittest.TestCase):
    def load(self, payload, overrides=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(payload))
            return CONFIG.load_runtime_config(path, overrides)

    def test_ros_omitted_null_and_integer(self):
        for fields, expected in [({}, 1), ({"pct_layer": None}, None),
                                 ({"pct_layer": 0}, 0), ({"pct_layer": 1}, 1)]:
            with self.subTest(fields=fields):
                actual = self.load({"schema": "p2b_backend_ros_config_v1", "map": fields})
                self.assertEqual(actual["map"]["pct_layer"], expected)

    def test_adapter_omitted_null_and_integer(self):
        for fields, expected in [({}, 1), ({"pct_layer": None}, None),
                                 ({"pct_layer": 0}, 0), ({"pct_layer": 1}, 1)]:
            with self.subTest(fields=fields):
                actual = self.load({"schema": "p2b_backend_adapter_config_v2", "pilot_contract": fields})
                self.assertEqual(actual["map"]["pct_layer"], expected)

    def test_overrides_respect_presence(self):
        for initial, override, expected in [(1, {"pct_layer": None}, None),
                                           (None, {"pct_layer": 0}, 0),
                                           (None, {}, None), (1, {}, 1)]:
            with self.subTest(initial=initial, override=override):
                actual = self.load({"schema": "p2b_backend_ros_config_v1",
                                    "map": {"pct_layer": initial}}, {"map": override})
                self.assertEqual(actual["map"]["pct_layer"], expected)

    def test_unrelated_null_values_keep_old_semantics(self):
        config = self.load({"schema": "p2b_backend_ros_config_v1",
                            "run_id": None, "http": {"port": None},
                            "map": {"epoch": None, "pct_layer": None}})
        self.assertEqual(config["run_id"], CONFIG.DEFAULT_CONFIG["run_id"])
        self.assertEqual(config["http"], CONFIG.DEFAULT_CONFIG["http"])
        self.assertEqual(config["map"]["epoch"], CONFIG.DEFAULT_CONFIG["map"]["epoch"])
        base = {"other": {"pct_layer": 7}}
        CONFIG._deep_update(base, {"other": {"pct_layer": None}})
        self.assertEqual(base["other"]["pct_layer"], 7)

    def test_top_level_map_null_keeps_default(self):
        config = self.load({"schema": "p2b_backend_ros_config_v1", "map": None}, {"map": None})
        self.assertEqual(config["map"], CONFIG.DEFAULT_CONFIG["map"])

    def test_default_not_mutated_by_prior_load(self):
        before = copy.deepcopy(CONFIG.DEFAULT_CONFIG)
        self.load({"schema": "p2b_backend_ros_config_v1", "map": {"pct_layer": None}})
        actual = self.load({"schema": "p2b_backend_ros_config_v1"})
        self.assertEqual(CONFIG.DEFAULT_CONFIG, before)
        self.assertEqual(actual["map"]["pct_layer"], 1)

    def test_actual_v25_live_configuration(self):
        path = BASE / "runs/v25_historical_full01/backend_config.json"
        self.assertIsNone(json.loads(path.read_text())["map"]["pct_layer"])
        self.assertIsNone(CONFIG.load_runtime_config(path)["map"]["pct_layer"])


if __name__ == "__main__":
    unittest.main()
