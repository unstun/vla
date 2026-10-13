import math
import numpy as np


def frame_indices(times, fps=30):
    times = np.asarray(times)
    if len(times) == 0 or times[0] != 0. or not np.isfinite(times).all() or np.any(np.diff(times) <= 0.):
        raise ValueError("Expected strictly advancing recorded time from zero")
    grid = np.arange(math.floor(times[-1] * fps) + 1) / fps
    indices = np.searchsorted(times, grid, side="right") - 1
    if np.any(times[indices] > grid):
        raise ValueError("Future state chosen")
    return grid, indices
