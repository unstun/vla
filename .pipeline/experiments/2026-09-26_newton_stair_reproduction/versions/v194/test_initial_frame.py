"""Check zero-state capture and reject a mislabeled already-stepped state."""
from pathlib import Path
import json
import tempfile
import unittest
from types import SimpleNamespace
from initial_frame_v142 import capture_zero, state_digest


class Array:
    def __init__(self, data): self.data = data
    def numpy(self): return self
    def tolist(self): return self.data


class InitialFrameTests(unittest.TestCase):
    def robot(self, steps=0, clock=0.0):
        return SimpleNamespace(steps=steps, physics_time=lambda: clock,
            state=SimpleNamespace(body_q=Array([[1, 2, 3, 0, 0, 0, 1]]),
                                  joint_q=Array([1, 2, 3, 4])))

    def test_capture_keeps_actual_arrays_and_clock(self):
        robot = self.robot()
        with tempfile.TemporaryDirectory() as tmp:
            frame = capture_zero(robot, Path(tmp))
            proof = json.loads((Path(tmp) / 'initial_state.json').read_text())
        self.assertEqual(frame['body_q'], robot.state.body_q.tolist())
        self.assertEqual(frame['joint_q'], robot.state.joint_q.tolist())
        self.assertEqual((robot.steps, robot.physics_time()), (0, 0.0))
        self.assertEqual(state_digest(frame), proof['state_sha256_before'])
        self.assertEqual(proof['state_sha256_before'], proof['state_sha256_after'])
        self.assertTrue(frame['recorded_before_first_physics_step'])

    def test_already_stepped_states_cannot_be_relabelled_zero(self):
        for steps, clock in [(1, 0.0), (0, 0.08), (80, 0.08)]:
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):
                    capture_zero(self.robot(steps, clock), Path(tmp))
                self.assertFalse((Path(tmp) / 'initial_state.json').exists())


if __name__ == '__main__': unittest.main()
