import math
import unittest
import uuid

from deploy.omnivla_lite3_receive_only import protocol
from deploy.omnivla_lite3_receive_only.tests.common import minimal_jpeg, trajectory


class ProtocolTests(unittest.TestCase):
    def test_jpeg_dimensions_and_digest(self):
        jpeg = minimal_jpeg(1280, 720)
        width, height, digest = protocol.validate_jpeg(jpeg)
        self.assertEqual((width, height), (1280, 720))
        self.assertEqual(digest, protocol.sha256_bytes(jpeg))

    def test_jpeg_digest_mismatch_is_rejected(self):
        with self.assertRaisesRegex(protocol.ProtocolError, "does not match"):
            protocol.validate_jpeg(minimal_jpeg(), "0" * 64)

    def test_instruction_bounds(self):
        self.assertEqual(protocol.validate_instruction("move forward"), "move forward")
        for value in ("", "  ", "hello\x00world", "界" * 86):
            with self.subTest(value=value):
                with self.assertRaises(protocol.ProtocolError):
                    protocol.validate_instruction(value)

    def test_success_response_round_trip(self):
        request_id = str(uuid.uuid4())
        response = protocol.make_success_response(request_id, trajectory(), 12.5)
        encoded = protocol.canonical_json_bytes(response)
        self.assertTrue(encoded.endswith(b"\n"))
        validated = protocol.validate_success_response(response, request_id)
        self.assertEqual(len(validated["trajectory_normalized"]), 8)
        self.assertFalse(validated["actuation_enabled"])
        self.assertEqual(validated["trajectory_metric_upstream_default"][2][0], 0.2)

    def test_response_rejects_nonfinite_and_wrong_shape(self):
        request_id = str(uuid.uuid4())
        for bad in (
            trajectory()[:7],
            [[0.0, 0.0, 1.0] for _ in range(8)],
            [[math.nan, 0.0, 1.0, 0.0] for _ in range(8)],
            [[math.inf, 0.0, 1.0, 0.0] for _ in range(8)],
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(protocol.ProtocolError):
                    protocol.make_success_response(request_id, bad, 1.0)

    def test_response_rejects_identity_and_actuation_changes(self):
        request_id = str(uuid.uuid4())
        base = protocol.make_success_response(request_id, trajectory(), 1.0)
        changes = {
            "request_id": str(uuid.uuid4()),
            "source_commit": "bad",
            "checkpoint_revision": "bad",
            "modality": "image_only",
            "actuation_enabled": True,
            "metric_scale_status": "calibrated",
        }
        for key, value in changes.items():
            changed = dict(base)
            changed[key] = value
            with self.subTest(key=key):
                with self.assertRaises(protocol.ProtocolError):
                    protocol.validate_success_response(changed, request_id)


if __name__ == "__main__":
    unittest.main()

