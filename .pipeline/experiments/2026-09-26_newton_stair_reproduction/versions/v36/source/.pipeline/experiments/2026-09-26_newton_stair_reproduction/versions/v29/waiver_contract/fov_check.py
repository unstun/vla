"""Count v29-only waived contract points inside the Mid-360 field beyond its minimum range.

Uses the pinned-URDF mount (0.1824, 0, 0.10854) m in TORSO with 15 deg nose-down
pitch, and the source-backed pattern's -7..+52 deg elevation and 0.1 m minimum
range (runtime_sources/bridge/lite3_sim_bridge/mid360_pattern.py). Ignores
self-occlusion by the robot's body, so it is an upper bound on observable
points. Writes fov_check.json.
"""
from pathlib import Path
import csv
import json
import math

import numpy as np

HERE = Path(__file__).resolve().parent
SENSOR = np.array([0.1824, 0.0, 0.10854])
PITCH = math.radians(15.0)
RY = np.array([[math.cos(PITCH), 0, math.sin(PITCH)], [0, 1, 0], [-math.sin(PITCH), 0, math.cos(PITCH)]])


def in_field(local):
    ray = RY.T @ (np.asarray(local) - SENSOR)
    elevation = math.degrees(math.atan2(ray[2], math.hypot(ray[0], ray[1])))
    return bool(np.linalg.norm(ray) >= 0.1 and -7.0 <= elevation <= 52.0)


result = {}
for state in ("stopped", "z_0p3650", "control"):
    counts = {"v29_only_points": 0, "in_field_beyond_min_range": 0, "v29_only_informative": 0, "informative_in_field": 0}
    for row in csv.DictReader((HERE / "green_v29" / f"{state}_discriminating.csv").open()):
        if row["waived_v29"] != "1" or row["waived_v28"] != "0":
            continue
        visible = in_field((float(row["local_x"]), float(row["local_y"]), float(row["local_z"])))
        counts["v29_only_points"] += 1
        counts["in_field_beyond_min_range"] += visible
        if row["free_verdict"] == "0":
            counts["v29_only_informative"] += 1
            counts["informative_in_field"] += visible
    result[state] = counts
(HERE / "fov_check.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=1))
