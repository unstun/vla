import unittest
import numpy as np
from timeline import frame_indices


class TimelineTests(unittest.TestCase):
    def test_retains_start_and_cannot_show_future(self):
        source = np.array([0., .08, .16, .24, .26, .28, .30])
        grid, indices = frame_indices(source)
        self.assertEqual(indices[0], 0)
        self.assertTrue(np.all(source[indices] <= grid))
        self.assertEqual(len(grid), 10)
        self.assertEqual(indices[-1], len(source) - 1)

    def test_rejects_nonzero_start_and_clock_reversal(self):
        for values in ([.1, .2], [0., .1, .1], [0., .2, .1], [0., float('nan')]):
            with self.assertRaises(ValueError):
                frame_indices(values)


if __name__ == "__main__":
    unittest.main()
