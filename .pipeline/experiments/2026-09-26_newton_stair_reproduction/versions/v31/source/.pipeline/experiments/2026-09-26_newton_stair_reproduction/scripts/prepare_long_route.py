"""Generate a registered, empty 30 x 16 m PCT floor in its pinned NumPy runtime."""
import hashlib
import json
from pathlib import Path
import pickle
import sys

import numpy as np


def main():
    if int(np.__version__.split(".")[0]) != 1:
        raise RuntimeError("Generate PCT pickle using the pinned native NumPy 1.x image")
    out = Path(sys.argv[1])
    out.mkdir(exist_ok=False)
    data = np.zeros((5, 2, 301, 161), dtype=np.float32)
    data[4] = 3.
    with (out / "flat_floor.pickle").open("wb") as stream:
        pickle.dump({"data": data, "resolution": .1, "center": [6., 0.],
                     "slice_h0": .5, "slice_dh": .5}, stream, protocol=4)
    scene = {"schema_version": 1, "mode": "walk", "spawn_ground_xyz_m": [0.,0.,0.],
             "spawn_body_height_m": .35, "spawn_yaw_rad": 0., "goal_ground_xyz_m": [12.,0.,0.],
             "locomotion_reference_height_m": .3, "nominal_body_height_m": .35,
             "max_sim_seconds": 150., "max_wall_seconds": 1550.,
             "floor_bounds_m": [-10.,22.,-9.,9.],
             "camera": {"trail_m": 2.2, "height_m": 1.8, "look_ahead_m": 1., "look_down_m": .15},
             "navigation_input": "Synthetic flat PCT support prior and actual geometric LiDAR; no obstacle metadata",
             "obstacles": "none"}
    (out / "scene.json").write_text(json.dumps(scene, indent=2)+"\n")
    (out / "manifest.json").write_text(json.dumps({"files": {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()},
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "numpy": np.__version__, "claim": "Synthetic floor support prior, not a sensed free-space map"}, indent=2)+"\n")


if __name__ == "__main__":
    main()
