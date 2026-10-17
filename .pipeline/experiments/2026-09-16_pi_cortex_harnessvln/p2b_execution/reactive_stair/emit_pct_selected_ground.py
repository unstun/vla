#!/usr/bin/env python3
"""Emit the pinned Building tomogram cells selected by PCT's publisher.

Standard output is `ix iy elevation_m` for the local C++ diagnostic. This
mirrors planner_node.py:publish_tomogram with endpoint masking disabled, the
default in the pinned P2B inputs. It does not run ROS or publish a topic.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import pickle
import sys

import numpy as np

P2B = Path(__file__).resolve().parent.parent
SOURCE = P2B / "inputs/new_building.pickle"
EXPECTED_SHA = "ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da"


def selected_cells():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("Building tomogram source hash changed")
    with SOURCE.open("rb") as file:
        content = pickle.load(file)
    resolution = float(content["resolution"])
    if resolution != 0.1:
        raise RuntimeError(f"unexpected PCT resolution: {resolution}")
    data = np.asarray(content["data"], dtype=np.float32)
    ground = np.where(np.isfinite(data[3]), data[3], np.nan).copy()
    traversability = data[0].copy()
    for layer in range(ground.shape[0] - 1):
        difference = ground[layer + 1] - ground[layer]
        duplicate = np.isfinite(difference) & (difference < float(content["slice_dh"]))
        ground[layer, duplicate] = np.nan
        traversability[layer + 1, duplicate] = np.minimum(
            traversability[layer, duplicate], traversability[layer + 1, duplicate]
        )
    visible = np.isfinite(ground) & (traversability <= 20.0)
    layers, gx, gy = np.nonzero(visible)
    return gx, gy, ground[layers, gx, gy]


def main():
    gx, gy, z = selected_cells()
    print(len(z))
    for ix, iy, height in zip(gx, gy, z):
        print(int(ix), int(iy), float(height))
    print(f"selected_cells={len(z)} source_sha256={EXPECTED_SHA}", file=sys.stderr)


if __name__ == "__main__":
    main()
