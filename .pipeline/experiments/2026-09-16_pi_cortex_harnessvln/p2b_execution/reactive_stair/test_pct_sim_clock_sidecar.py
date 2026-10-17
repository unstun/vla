import ast
import hashlib
from pathlib import Path
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pct_sim_clock_core import SimClockGate, cloud_payload, load_pinned_map, selected_ground_points


def clock_callback_from_source():
    tree = ast.parse((HERE / "pct_sim_clock_publisher.py").read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "PctSimClockPublisher")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                  and node.name == "_on_clock")

    class FakeCloud:
        def __init__(self):
            self.header = types.SimpleNamespace(
                stamp=types.SimpleNamespace(sec=0, nanosec=0), frame_id=""
            )

    class FakeField:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    namespace = {"Clock": object, "PointCloud2": FakeCloud,
                 "PointField": FakeField, "cloud_payload": cloud_payload}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(HERE / "pct_sim_clock_publisher.py"), "exec"),
         namespace)
    return namespace["_on_clock"]


class SidecarCallbackTest(unittest.TestCase):
    def test_no_zero_clock_publish_and_exact_sim_stamp(self):
        points = selected_ground_points(load_pinned_map())
        messages = []
        callback = clock_callback_from_source()
        fake = types.SimpleNamespace(
            _points=points, _point_sha=hashlib.sha256(points.astype("<f4").tobytes()).hexdigest(),
            _frame="world", _topic="/pct_tomogram", _gate=SimClockGate(),
            _publisher=types.SimpleNamespace(publish=messages.append),
            get_logger=lambda: types.SimpleNamespace(info=lambda message: None),
        )

        def clock(ns):
            return types.SimpleNamespace(clock=types.SimpleNamespace(
                sec=ns // 1_000_000_000, nanosec=ns % 1_000_000_000
            ))

        callback(fake, clock(0))
        callback(fake, clock(1_000_000_000))
        self.assertEqual(messages, [])
        callback(fake, clock(1_100_000_000))
        self.assertEqual(len(messages), 1)
        msg = messages[0]
        self.assertEqual((msg.header.stamp.sec, msg.header.stamp.nanosec), (1, 100_000_000))
        self.assertEqual(msg.header.frame_id, "world")
        self.assertEqual(msg.width, 86775)
        self.assertEqual(msg.point_step, 16)
        self.assertEqual(msg.row_step, 16 * 86775)
        self.assertFalse(msg.is_bigendian)
        self.assertFalse(msg.is_dense)  # exact Humble create_cloud metadata
        self.assertEqual(hashlib.sha256(msg.data).hexdigest(),
                         "71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577")
        callback(fake, clock(1_200_000_000))
        self.assertEqual(len(messages), 1)
        callback(fake, clock(0))
        callback(fake, clock(100_000_000))
        self.assertEqual(len(messages), 1)
        callback(fake, clock(200_000_000))
        self.assertEqual(len(messages), 2)
        self.assertEqual((messages[1].header.stamp.sec, messages[1].header.stamp.nanosec),
                         (0, 200_000_000))


if __name__ == "__main__":
    unittest.main()
