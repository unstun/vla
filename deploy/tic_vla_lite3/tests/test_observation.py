import unittest

from tic_vla_lite3.frame_source import DelayedFrameBuffer, FrameSample
from tic_vla_lite3.state_source import (ReasoningReferenceBuffer,
                                        RobotStateSample, model_state)


class ObservationTest(unittest.TestCase):
    def test_delayed_context(self):
        buffer = DelayedFrameBuffer()
        for sequence in range(101):
            buffer.append(FrameSample(sequence, sequence / 10.0, 640, 480, b"jpeg"))
        self.assertEqual([frame.sequence for frame in buffer.context(10.0)], [10, 40, 70, 100])

    def test_repeated_frame_rejected(self):
        buffer = DelayedFrameBuffer()
        buffer.append(FrameSample(1, 1.0, 640, 480, b"jpeg"))
        with self.assertRaises(ValueError):
            buffer.append(FrameSample(1, 1.1, 640, 480, b"jpeg"))
        with self.assertRaises(ValueError):
            buffer.append(FrameSample(2, float("inf"), 640, 480, b"jpeg"))
        with self.assertRaises(ValueError):
            buffer.context(float("nan"))

    def test_state_age_and_delta(self):
        start = RobotStateSample(1, 1.0, 0.1, 0.0, 0.01, 2.0, 3.0)
        current = RobotStateSample(2, 1.1, 0.2, 0.0, -0.01, 2.5, 2.75)
        current.validate(1.2, 0.25)
        self.assertEqual(model_state(current, start, 0.2), (0.2, 0.0, -0.01, 0.5, -0.25, 0.2))
        with self.assertRaises(ValueError):
            current.validate(2.0, 0.25)
        with self.assertRaises(ValueError):
            current.validate(float("nan"), 0.25)

    def test_reasoning_reference_matches_upstream_two_generation_window(self):
        references = ReasoningReferenceBuffer()
        current = RobotStateSample(100, 10.0, 0.0, 0.0, 0.0, 10.0, 20.0)
        self.assertIs(references.reference(current), current)
        references.observe(100, {"position": [1.0, 2.0, 0.0]}, 1.0)
        references.observe(200, {"position": [3.0, 4.0, 0.0]}, 2.0)
        self.assertEqual(references.reference(current).sequence, 100)
        references.observe(300, {"position": [5.0, 6.0, 0.0]}, 3.0)
        self.assertEqual(references.reference(current).sequence, 200)

    def test_reasoning_reference_rejects_invalid_or_rollback_generation(self):
        references = ReasoningReferenceBuffer()
        references.observe(2, {"position": [1.0, 2.0, 0.0]}, 1.0)
        with self.assertRaises(ValueError):
            references.observe(2, {"position": [1.0, 2.0, 0.0]}, 1.1)
        with self.assertRaises(ValueError):
            references.observe(3, {"position": [float("nan"), 2.0, 0.0]}, 1.2)


if __name__ == "__main__":
    unittest.main()
