import unittest
import numpy as np
from prepare_actor_right import body_clearance, clip_height, projected_distance


class ActorGeometryTests(unittest.TestCase):
    def test_wall_detected_even_when_its_xy_projection_is_degenerate(self):
        wall = np.array([[[0.3, -1, 0], [0.3, 1, 0], [0.3, 1, 3]],
                         [[0.3, -1, 0], [0.3, 1, 3], [0.3, -1, 3]]], dtype=float)
        self.assertAlmostEqual(body_clearance(wall, 0, 0, 0, 0.8), 0.3)

    def test_ground_below_body_does_not_count_as_a_torso_collision(self):
        ground = np.array([[[-1, -1, 0], [1, -1, 0], [0, 1, 0]]], dtype=float)
        self.assertEqual(body_clearance(ground, 0, 0, 0, 0.8), 0.8)
        self.assertEqual(clip_height(list(ground[0]), 0.45, True), [])

    def test_overhead_projection_covers_body_center(self):
        polygon = [np.array([-1, -1, 1.0]), np.array([1, -1, 1.0]), np.array([0, 1, 1.0])]
        self.assertEqual(projected_distance(polygon, np.array([0.0, 0.0])), 0.0)


if __name__ == "__main__":
    unittest.main()
