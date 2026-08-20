import io
import json
import struct
from unittest import mock
import unittest

from tic_vla_lite3.live_bridge import decode_record


def record(metadata, jpeg=b"jpeg"):
    data = json.dumps(metadata, separators=(",", ":")).encode()
    return io.BytesIO(struct.pack("!I", len(data)) + data + struct.pack("!I", len(jpeg)) + jpeg)


class LiveBridgeTest(unittest.TestCase):
    def metadata(self):
        return {
            "schema": "tic-vla-lite3.observation.v1", "frame_sequence": 2,
            "frame_callback_monotonic_s": 3.0, "frame_source_age_s": 0.01,
            "state_sequence": 4, "state_callback_monotonic_s": 3.1,
            "state_source_age_s": 0.02, "width": 640, "height": 480,
            "encoding": "jpeg-bgr8", "frame_id": "camera_init",
            "child_frame_id": "aft_mapped", "x_m": 0.1, "y_m": -0.2,
            "z_m": 0.0, "qx": 0.0, "qy": 0.0, "qz": 0.0, "qw": 1.0,
            "vx_mps": 0.0, "vy_mps": 0.0, "wz_radps": 0.0,
        }

    def test_decode_uses_receiver_clock(self):
        sample = decode_record(record(self.metadata()), 10.0)
        self.assertEqual(sample.frame.captured_monotonic_s, 10.0)
        self.assertEqual(sample.state.received_monotonic_s, 10.0)

    def test_decode_stamps_after_complete_record_when_clock_not_supplied(self):
        with mock.patch("tic_vla_lite3.live_bridge.time.monotonic", return_value=12.5):
            sample = decode_record(record(self.metadata()))
        self.assertEqual(sample.received_monotonic_s, 12.5)

    def test_unknown_and_nonfinite_rejected(self):
        value = self.metadata(); value["extra"] = 1
        with self.assertRaises(ValueError): decode_record(record(value), 1.0)
        value = self.metadata(); value["vx_mps"] = float("nan")
        with self.assertRaises(ValueError): decode_record(record(value), 1.0)


if __name__ == "__main__":
    unittest.main()
