import math
import sys
import unittest
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_ROOT / "scripts"))

from metrics import pairwise_difference, repeat_dispersion, trajectory_metrics  # noqa: E402


class MetricsTests(unittest.TestCase):
    def test_repeat_dispersion_for_identical_trajectories_is_zero(self):
        trajectory = [[float(i), 0.0, 1.0, 0.0] for i in range(8)]
        result = repeat_dispersion([trajectory, trajectory, trajectory])
        self.assertEqual(result["pair_count"], 3)
        self.assertEqual(result["mean_pairwise_mae"], 0.0)
        self.assertEqual(result["max_pairwise_abs"], 0.0)

    def test_pairwise_difference(self):
        left = [[0.0] * 4 for _ in range(8)]
        right = [[1.0] * 4 for _ in range(8)]
        result = pairwise_difference(left, right)
        self.assertEqual(result["mae"], 1.0)
        self.assertEqual(result["rmse"], 1.0)
        self.assertEqual(result["max_abs"], 1.0)

    def test_trajectory_geometry(self):
        trajectory = [[float(i + 1), 0.5 * (i + 1), 1.0, 0.0] for i in range(8)]
        result = trajectory_metrics(trajectory)
        self.assertEqual(result["endpoint_x"], 8.0)
        self.assertEqual(result["endpoint_y"], 4.0)
        self.assertGreater(result["path_length"], 0.0)
        self.assertEqual(result["signed_lateral_displacement"], 4.0)
        self.assertAlmostEqual(result["heading_radians"], 0.0)


if __name__ == "__main__":
    unittest.main()

