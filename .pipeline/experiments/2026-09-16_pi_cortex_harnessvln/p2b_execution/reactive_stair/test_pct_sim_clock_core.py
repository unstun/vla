import ast
import hashlib
from pathlib import Path
import sys
import tempfile
import types
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pct_sim_clock_core import (DEFAULT_MAP, MAP_SHA, PCT_PUBLISHER_SHA,
                                SimClockGate, cloud_payload, load_pinned_map,
                                selected_ground_points)
from physical_ground_contract import verify_physical_ground

PCT_NODE = HERE.parent / "pct_runtime/python/pct_planner/planner_node.py"


def pinned_publisher_points(source, coord_mode):
    """Execute the exact pinned publisher methods with ROS transport stubs."""
    code = PCT_NODE.read_text()
    if hashlib.sha256(code.encode()).hexdigest() != PCT_PUBLISHER_SHA:
        raise AssertionError("pinned PCT publisher source changed")
    tree = ast.parse(code)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "PCTPlanner")
    wanted = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)
              and node.name in ("world_to_planner", "planner_to_world", "publish_tomogram")}
    if len(wanted) != 3:
        raise AssertionError("pinned PCT publisher methods missing")
    captured = []

    class FakeHeader:
        stamp = None
        frame_id = None

    class FakePublisher:
        def publish(self, points):
            captured.append(points)

    namespace = {
        "np": np,
        "Header": FakeHeader,
        "TOMOGRAM_POINT_FIELDS": [],
        "pc2": types.SimpleNamespace(create_cloud=lambda header, fields, points: points),
    }
    for node in wanted.values():
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(PCT_NODE), "exec"), namespace)
    data = np.asarray(source["data"], dtype=np.float32)
    planner = types.SimpleNamespace(
        elev_g_valid=np.isfinite(data[3]),
        elev_g=np.nan_to_num(data[3], nan=-100),
        trav=data[0], n_slice=data.shape[1], slice_dh=float(source["slice_dh"]),
        offset=np.array([int(data.shape[2] / 2), int(data.shape[3] / 2)], dtype=np.int32),
        resolution=float(source["resolution"]), center=np.asarray(source["center"], dtype=np.double),
        astar_cost_threshold=20.0,
    )
    fake = types.SimpleNamespace(
        planner=planner, endpoint_mask=None, coord_mode=coord_mode,
        tomogram_visual_z_offset=0.03, frame_id="world",
        tomogram_topic="/pct_tomogram", tomogram_pub=FakePublisher(),
        get_clock=lambda: types.SimpleNamespace(now=lambda: types.SimpleNamespace(to_msg=lambda: object())),
        get_logger=lambda: types.SimpleNamespace(info=lambda message: None),
    )
    fake.world_to_planner = types.MethodType(namespace["world_to_planner"], fake)
    fake.planner_to_world = types.MethodType(namespace["planner_to_world"], fake)
    namespace["publish_tomogram"](fake)
    return captured[0]


class ClockAndPointParityTest(unittest.TestCase):
    def test_full_physical_ground_is_separate_from_selected_navigation_points(self):
        physical = selected_ground_points(self.source, cost_limit=None)
        self.assertEqual(physical.shape, (149504, 4))
        self.assertTrue(np.isfinite(physical).all())
        self.assertGreater(int(np.sum(physical[:, 3] > 20)), 0)
        packet = cloud_payload(physical, 100, "world")
        self.assertGreater(packet.width, 100_000)
        contract = dict(data=packet.data, frame="world", width=packet.width, height=1,
                        point_step=packet.point_step, row_step=packet.row_step, is_bigendian=False,
                        fields={name: (offset, datatype, count) for name, offset, datatype, count in packet.fields})
        verify_physical_ground(**contract)
        # Identical bytes must not be reinterpreted using a different schema.
        # The z.offset=0 case previously passed and silently discarded the actor.
        bad_fields = dict(contract["fields"], z=(0, 7, 1))
        for changed in ({"frame": "odom"}, {"width": packet.width // 2, "height": 2},
                        {"point_step": 12}, {"row_step": packet.row_step + 16},
                        {"is_bigendian": True}, {"fields": bad_fields},
                        {"fields": dict(contract["fields"], z=(8, 8, 1))},
                        {"fields": dict(contract["fields"], z=(8, 7, 2))},
                        {"data": packet.data[:-1] + bytes([packet.data[-1] ^ 1])}):
            with self.subTest(changed=list(changed)), self.assertRaises(ValueError):
                verify_physical_ground(**dict(contract, **changed))
        selected = selected_ground_points(self.source)
        with self.assertRaises(ValueError):
            verify_physical_ground(**dict(contract, data=selected.astype("<f4").tobytes(),
                                          width=len(selected), row_step=16 * len(selected)))
        # Exact selected-point parity is independently checked against the
        # captured upstream publisher in test_exact_point_parity_with_pinned_publisher.

    @classmethod
    def setUpClass(cls):
        cls.source = load_pinned_map()

    def test_zero_clock_refused_and_reset_rearms(self):
        gate = SimClockGate()
        self.assertIsNone(gate.observe(0))
        self.assertIsNone(gate.observe(100))
        self.assertIsNone(gate.observe(100))
        self.assertEqual(gate.observe(150), 150)
        self.assertIsNone(gate.observe(200))
        self.assertIsNone(gate.observe(0))
        self.assertIsNone(gate.observe(5))
        self.assertEqual(gate.observe(6), 6)
        with self.assertRaisesRegex(ValueError, "nonzero simulation stamp"):
            cloud_payload(np.ones((1, 4), dtype=np.float32), 0)

    def test_exact_pinned_map_hash_and_wrong_source_refused(self):
        self.assertEqual(hashlib.sha256(DEFAULT_MAP.read_bytes()).hexdigest(), MAP_SHA)
        self.assertEqual(hashlib.sha256(PCT_NODE.read_bytes()).hexdigest(), PCT_PUBLISHER_SHA)
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "changed.pickle"
            changed.write_bytes(DEFAULT_MAP.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_pinned_map(changed)

    def test_exact_point_parity_with_pinned_publisher(self):
        expected_hashes = {
            "identity": "71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577",
            "sim_to_pct_180deg": "086443241a8b5cb628285c060624a896ee2ba87b7f2710ddd0a16a9667c94ef5",
        }
        for coord_mode in ("identity", "sim_to_pct_180deg"):
            with self.subTest(coord_mode=coord_mode):
                expected = pinned_publisher_points(self.source, coord_mode)
                actual = selected_ground_points(self.source, coord_mode)
                self.assertEqual(actual.shape, (86775, 4))
                self.assertEqual(actual.dtype, np.float32)
                np.testing.assert_array_equal(actual, expected)
                packet = cloud_payload(actual, 987654321, "world")
                self.assertEqual(packet.stamp_ns, 987654321)
                self.assertEqual(packet.frame, "world")
                self.assertEqual(packet.width, 86775)
                self.assertEqual(packet.point_step, 16)
                self.assertEqual(packet.row_step, 16 * 86775)
                self.assertEqual(packet.fields[0], ("x", 0, 7, 1))
                self.assertEqual(packet.data, actual.astype("<f4").tobytes())
                self.assertEqual(hashlib.sha256(packet.data).hexdigest(), expected_hashes[coord_mode])


if __name__ == "__main__":
    unittest.main()
