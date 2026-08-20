import json
import unittest

from tic_vla_lite3.protocol import BodyCommand, ProtocolError, decode_command, encode_command


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.command = BodyCommand("session-a", 1, 2, 3, "shadow", True, 0.2, 0.0, -0.1)

    def test_round_trip(self):
        self.assertEqual(decode_command(encode_command(self.command), "session-a"), self.command)

    def test_strict_field_set_and_session(self):
        value = json.loads(encode_command(self.command))
        value["extra"] = 1
        with self.assertRaises(ProtocolError):
            decode_command(json.dumps(value).encode())
        with self.assertRaises(ProtocolError):
            decode_command(encode_command(self.command), "other")

    def test_ranges_and_types(self):
        for field, value in (("vx_mps", 0.31), ("vy_mps", 0.01),
                             ("wz_radps", -0.21), ("plan_seq", True)):
            payload = json.loads(encode_command(self.command))
            payload[field] = value
            with self.subTest(field=field), self.assertRaises(ProtocolError):
                decode_command(json.dumps(payload).encode())

    def test_size_and_malformed(self):
        for payload in (b"", b"{", b"x" * 1025):
            with self.subTest(payload=payload[:2]), self.assertRaises(ProtocolError):
                decode_command(payload)


if __name__ == "__main__":
    unittest.main()
