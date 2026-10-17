"""Failing tests for the global SCAN step-vs-wall occupancy rule."""
import math
import unittest

from step_traversability import (
    DEFAULT_PARAMS,
    occupancy_hit_is_traversable_step,
)


RES = DEFAULT_PARAMS.resolution_m


def fill_rect(height, x0, x1, y0, y1, z, resolution=RES):
    ix0 = math.floor(x0 / resolution)
    ix1 = math.floor((x1 - 1e-9) / resolution)
    iy0 = math.floor(y0 / resolution)
    iy1 = math.floor((y1 - 1e-9) / resolution)
    for ix in range(ix0, ix1 + 1):
        for iy in range(iy0, iy1 + 1):
            height[(ix, iy)] = z


def floor_map(x0=-1.5, x1=3.5, y0=-1.5, y1=1.5, z=0.0):
    height = {}
    fill_rect(height, x0, x1, y0, y1, z)
    return height


class StepTraversabilityTests(unittest.TestCase):
    def test_unmapped_box_0_8m_is_not_a_step(self):
        height = floor_map()
        fill_rect(height, 0.4, 0.8, -0.2, 0.2, 0.8)
        self.assertFalse(
            occupancy_hit_is_traversable_step(height, 0.40, 0.0, DEFAULT_PARAMS)
        )

    def test_building_stair_nosing_is_a_step(self):
        height = floor_map()
        fill_rect(height, 0.0, 0.74, -1.0, 1.0, 0.136)
        self.assertTrue(
            occupancy_hit_is_traversable_step(height, 0.0, 0.0, DEFAULT_PARAMS)
        )

    def test_standard_stair_nosing_is_a_step(self):
        height = floor_map()
        fill_rect(height, 0.0, 0.30, -1.0, 1.0, 0.16)
        self.assertTrue(
            occupancy_hit_is_traversable_step(height, 0.0, 0.0, DEFAULT_PARAMS)
        )

    def test_thin_wall_same_height_as_a_riser_is_not_a_step(self):
        height = floor_map()
        fill_rect(height, 0.50, 0.55, -0.5, 0.5, 0.15)
        self.assertFalse(
            occupancy_hit_is_traversable_step(height, 0.50, 0.0, DEFAULT_PARAMS)
        )

    def test_flat_window_is_not_a_step(self):
        height = floor_map()
        self.assertFalse(
            occupancy_hit_is_traversable_step(height, 0.0, 0.0, DEFAULT_PARAMS)
        )


if __name__ == "__main__":
    unittest.main()
