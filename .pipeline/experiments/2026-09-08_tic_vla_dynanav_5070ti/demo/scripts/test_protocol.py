import unittest

from protocol import CommandLatch, INSTRUCTION, body_to_world, parse_command, project_points, read_instruction_request


class ProtocolTests(unittest.TestCase):
    def test_explicit_vocabulary_and_rejection(self):
        self.assertEqual(parse_command("走到自动售货机前。 ")["instruction"], "走到自动售货机前。")
        self.assertEqual(parse_command(INSTRUCTION)["instruction"], INSTRUCTION)
        self.assertEqual(parse_command("去售货机")["instruction"], "去售货机")
        self.assertEqual(parse_command("直走，并在自动售货机前停下")["instruction"], "直走，并在自动售货机前停下")
        self.assertEqual(parse_command("STOP!")["action"], "stop")
        for text in ["不要停下", "继续还是停下", "走到病房", "", None, "x" * 241]:
            with self.assertRaises(ValueError):
                parse_command(text)

    def test_utf8_request_roundtrip_and_no_english_fallback(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            with self.assertRaises(FileNotFoundError):
                read_instruction_request(path)
            payload = {"instruction": "走到自动售货机前", "instruction_mode": "verbatim"}
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(read_instruction_request(path), payload)
            payload["inference_seed"] = 36
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(read_instruction_request(path)["inference_seed"], 36)
            for seed in [-1, True, 1.5, "36", 2**32]:
                path.write_text(json.dumps(dict(payload, inference_seed=seed)), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_instruction_request(path)
            for invalid in [{}, {"instruction": "走到自动售货机前", "instruction_mode": "translated"},
                            {"instruction": "停下", "instruction_mode": "verbatim"}]:
                path.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
                with self.assertRaises(ValueError):
                    read_instruction_request(path)

    def test_stop_received_during_reset_cannot_be_overwritten(self):
        latch = CommandLatch()
        self.assertTrue(latch.is_held())
        with self.assertRaises(ValueError):
            latch.submit({"id": "a", "text": "继续"})
        goal = latch.submit({"id": "g", "text": "走到自动售货机前"})
        self.assertEqual(latch.take(), goal)
        stop = latch.submit({"id": "s", "text": "停下"})
        latch.acknowledge(goal)
        self.assertTrue(latch.is_held())
        latch.acknowledge(latch.take())
        self.assertEqual(latch.snapshot()["ack"], stop)
        # Old retransmissions neither release hold nor create a pending command.
        self.assertEqual(latch.submit({"id": "g", "text": "走到自动售货机前"})["id"], "g")
        self.assertIsNone(latch.take())
        self.assertTrue(latch.is_held())
        latch.submit({"id": "r", "text": "继续"})
        latch.acknowledge(latch.take())
        self.assertFalse(latch.is_held())

    def test_body_pose_and_camera_axes(self):
        from math import sqrt
        point = body_to_world([[2, 0]], [10, 5, 0], [sqrt(.5), 0, 0, sqrt(.5)])[0]
        self.assertAlmostEqual(point[0], 10)
        self.assertAlmostEqual(point[1], 7)
        # Camera looking down -Z: right is +X; image up is +Y.
        matrix = [[1,0,0,0],[0,1,0,0],[0,0,-1,-1],[0,0,0,0]]
        self.assertEqual(project_points([[0,0,-2],[1,1,-2],[0,0,1]], matrix, 100, 80),
                         [[50,40],[75,20],None])


if __name__ == "__main__":
    unittest.main()
