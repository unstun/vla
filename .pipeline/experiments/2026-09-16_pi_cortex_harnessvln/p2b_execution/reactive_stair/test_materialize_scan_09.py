import ast
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import types
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True
from moving_cluster_io import decode_float32_cloud, terrain_from_pct_records
from pct_sim_clock_core import cloud_payload

spec = importlib.util.spec_from_file_location("materialize_scan_09", HERE / "materialize_scan_09.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def terrain_callback(source: Path):
    tree = ast.parse(source.read_text())
    cls = next(item for item in tree.body if isinstance(item, ast.ClassDef)
               and item.name == "MovingClusterNode")
    method = next(item for item in cls.body if isinstance(item, ast.FunctionDef)
                  and item.name == "_on_terrain")
    namespace = {
        "PointCloud2": object, "decode_float32_cloud": decode_float32_cloud,
        "terrain_from_pct_records": terrain_from_pct_records,
        "stamp_ns": lambda stamp: stamp.sec * 1_000_000_000 + stamp.nanosec,
        "math": math,
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_on_terrain"]


class Scan09DensityTest(unittest.TestCase):
    def test_built_source_gate_and_single_overlay(self):
        base = module.gate()
        record = json.loads((module.OUTPUT / "pct_density_candidate_manifest.json").read_text())
        self.assertEqual(record["base"], "scan_08")
        root = module.OUTPUT / "src"
        actual = {path.relative_to(root).as_posix(): module.sha(path)
                  for path in root.rglob("*") if path.is_file()}
        self.assertEqual(len(base), 82)
        self.assertEqual(set(actual), set(base))
        self.assertEqual(set(record["changed_sha256"]), {module.NODE_REL.as_posix()})
        for name, expected in base.items():
            if name not in record["changed_sha256"]:
                self.assertEqual(actual[name], expected)
        self.assertEqual(actual[module.NODE_REL.as_posix()],
                         record["changed_sha256"][module.NODE_REL.as_posix()])

    def test_humble_false_density_with_finite_points_is_accepted(self):
        old_callback = terrain_callback(module.SOURCE / "src" / module.NODE_REL)
        new_callback = terrain_callback(module.OUTPUT / "src" / module.NODE_REL)
        packet = cloud_payload(np.array([[1.0, 2.0, 0.23, 15.0]], dtype=np.float32),
                               1_000_000_000)

        def message(data=packet.data, frame="world"):
            return types.SimpleNamespace(
                is_dense=False, data=data, width=1, height=1, point_step=16,
                row_step=16, is_bigendian=False,
                header=types.SimpleNamespace(frame_id=frame,
                    stamp=types.SimpleNamespace(sec=1, nanosec=0)),
                fields=[types.SimpleNamespace(name=name, offset=offset,
                                              datatype=datatype, count=count)
                        for name, offset, datatype, count in packet.fields],
            )

        def receiver():
            failures = []
            return types.SimpleNamespace(
                _terrain=None,
                _fields=lambda msg: {field.name: (field.offset, field.datatype, field.count)
                                     for field in msg.fields},
                get_logger=lambda: types.SimpleNamespace(error=lambda text: None),
                _publish_incomplete=failures.append,
                failures=failures,
            )

        old = receiver()
        old_callback(old, message())
        self.assertIsNone(old._terrain)
        self.assertEqual(old.failures, ["invalid_pct_support"])

        corrected = receiver()
        new_callback(corrected, message())
        self.assertIsNotNone(corrected._terrain)
        self.assertEqual(corrected.failures, [])
        self.assertAlmostEqual(corrected._terrain.ground_below(1.0, 2.0, 0.5), 0.2, places=6)
        self.assertEqual(corrected._terrain.frame, "world")

        bad = receiver()
        new_callback(bad, message(data=struct.pack("<ffff", 1.0, 2.0, float("nan"), 15.0)))
        self.assertIsNone(bad._terrain)
        self.assertEqual(bad.failures, ["invalid_pct_support"])
        wrong_frame = receiver()
        new_callback(wrong_frame, message(frame="odom"))
        self.assertIsNone(wrong_frame._terrain)

    def test_existing_output_and_tampered_source_refused(self):
        with self.assertRaisesRegex(module.Refused, "already exists"):
            module.materialize()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scan_08"
            source.mkdir()
            for name in ("source_sha256.json", "moving_cluster_candidate_manifest.json", "build_result.json"):
                shutil.copy2(module.SOURCE / name, source / name)
            shutil.copytree(module.SOURCE / "src", source / "src",
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (source / "src" / module.NODE_REL).write_bytes(b"tampered")
            previous_source, previous_output = module.SOURCE, module.OUTPUT
            try:
                module.SOURCE, module.OUTPUT = source, root / "scan_09"
                with self.assertRaisesRegex(module.Refused, "scan_08 source gate"):
                    module.materialize()
                self.assertFalse(module.OUTPUT.exists())
            finally:
                module.SOURCE, module.OUTPUT = previous_source, previous_output


if __name__ == "__main__":
    unittest.main()
